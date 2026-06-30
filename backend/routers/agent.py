from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json
from backend.agents.resolution_agent import run_resolution_agent
from backend.database import db

router = APIRouter(prefix="/agent", tags=["Autonomous Agent"])

@router.post("/resolve/{id}")
async def trigger_resolution_agent(id: str):
    issue = db.get_document("issues", id)
    if not issue:
        issue = db.get_document("issues", f"ISS-{id}")
    if not issue:
        # Try numeric ID if Civio passed it
        issues = db.list_documents("issues")
        for x in issues:
            if x.get("id", "").replace("ISS-", "") == id:
                issue = x
                break
                
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    logs = []
    async for raw_log in run_resolution_agent(issue["id"]):
        try:
            log_data = json.loads(raw_log)
            logs.append(f"{log_data.get('thought')}")
        except Exception:
            logs.append(str(raw_log))
            
    db.update_document("issues", issue["id"], {"status": "RESOLVED"})
    
    return {
        "success": True,
        "logs": logs,
        "workOrderId": issue.get("workOrderId", f"WO-{id}")
    }

@router.get("/status/{id}")
async def get_agent_status_stream(id: str):
    issue = db.get_document("issues", id)
    if not issue:
        issue = db.get_document("issues", f"ISS-{id}")
        
    if not issue:
        async def err_generator():
            yield "data: {\"error\": \"Issue not found\"}\n\n"
        return StreamingResponse(err_generator(), media_type="text/event-stream")
        
    async def event_generator():
        async for log in run_resolution_agent(issue["id"]):
            yield f"data: {log}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")
