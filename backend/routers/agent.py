from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from backend.agents.resolution_agent import run_resolution_agent
from backend.database import db

router = APIRouter(prefix="/agent", tags=["Autonomous Agent"])

@router.post("/resolve/{id}")
async def trigger_resolution_agent(id: str):
    issue = db.get_document("issues", id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    # Just trigger / return OK. The client will connect to /status/{id} to view it happen
    return {"success": True, "message": f"Autonomous agent run initialized for issue {id}"}

@router.get("/status/{id}")
async def get_agent_status_stream(id: str):
    issue = db.get_document("issues", id)
    if not issue:
        # Stream error
        async def err_generator():
            yield "data: {\"error\": \"Issue not found\"}\n\n"
        return StreamingResponse(err_generator(), media_type="text/event-stream")
        
    async def event_generator():
        async for log in run_resolution_agent(id):
            yield f"data: {log}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")
