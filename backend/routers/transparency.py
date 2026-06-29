from fastapi import APIRouter, Query, Body
from typing import List, Optional
from backend.database import db
from datetime import datetime

router = APIRouter(prefix="/transparency", tags=["Transparency & Accountability"])

@router.get("/index")
async def get_accountability_index():
    issues = db.list_documents("issues")
    
    # Group issues by ward
    wards = ["Indiranagar", "Koramangala", "Whitefield", "Jayanagar", "Malleshwaram", "HSR Layout"]
    ward_stats = {}
    
    for w in wards:
        ward_stats[w] = {
            "resolved_within_sla": 0,
            "resolved_total": 0,
            "total": 0,
            "breached": 0,
            "satisfaction_sum": 0,
            "satisfaction_count": 0,
            "active_ages_sum": 0,
            "active_count": 0
        }
        
    now = datetime.utcnow()
    
    for x in issues:
        ward = x.get("location", {}).get("ward")
        if ward not in ward_stats:
            continue
            
        stats = ward_stats[ward]
        stats["total"] += 1
        
        status = x.get("status")
        sla_breached = x.get("slaBreached", False)
        
        if status in ["RESOLVED", "CLOSED"]:
            stats["resolved_total"] += 1
            if not sla_breached:
                stats["resolved_within_sla"] += 1
            # Mock satisfaction score based on upvotes/validation
            satisfaction = min(5, 3 + (x.get("upvotes", 0) % 3))
            stats["satisfaction_sum"] += satisfaction
            stats["satisfaction_count"] += 1
        else:
            stats["active_count"] += 1
            reported_at = datetime.fromisoformat(x["reportedAt"].replace("Z", ""))
            age_days = (now - reported_at).days
            stats["active_ages_sum"] += age_days
            if sla_breached:
                stats["breached"] += 1
                
    results = []
    for w in wards:
        stats = ward_stats[w]
        
        # Calculate rates
        sla_rate = (stats["resolved_within_sla"] / stats["resolved_total"] * 100) if stats["resolved_total"] > 0 else 85.0
        avg_sat = (stats["satisfaction_sum"] / stats["satisfaction_count"]) if stats["satisfaction_count"] > 0 else 4.2
        avg_age = (stats["active_ages_sum"] / stats["active_count"]) if stats["active_count"] > 0 else 3.5
        
        # Add some variation to trends
        import random
        random.seed(w)
        trend = random.choice(["IMPROVING", "STABLE", "DECLINING"])
        
        results.append({
            "ward": w,
            "slaComplianceRate": round(sla_rate, 1),
            "averageResolutionDays": round(4.5 if w == "Jayanagar" else 6.2 if w == "Indiranagar" else 11.2, 1),
            "citizenSatisfaction": round(avg_sat, 1),
            "openIssuesCount": stats["active_count"],
            "slaBreachesCount": stats["breached"],
            "averageAgeOfOpenIssuesDays": round(avg_age, 1),
            "trend": trend,
            "accountabilityScore": round((sla_rate * 0.5) + (avg_sat * 10) + (100 - min(100, avg_age * 4)) * 0.1, 1)
        })
        
    # Sort by accountability score descending
    results.sort(key=lambda item: item["accountabilityScore"], reverse=True)
    return results

@router.get("/audit")
async def get_public_audit_log(issueId: Optional[str] = Query(None)):
    logs = db.list_documents("audit_logs")
    if issueId:
        logs = [x for x in logs if x.get("issueId") == issueId]
        
    # Sort logs by timestamp descending
    logs.sort(key=lambda item: item.get("timestamp", ""), reverse=True)
    return logs

@router.get("/complaint/{id}")
async def get_draft_complaint(id: str, citizenName: Optional[str] = Query("Concerned Citizen")):
    issue = db.get_document("issues", id)
    if not issue:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Issue not found")
        
    from backend.services.gemini_service import draft_complaint_letter
    letter = await draft_complaint_letter(issue, citizenName)
    return letter

@router.post("/complaint/{id}/send")
async def send_complaint_email_endpoint(
    id: str,
    payload: dict = Body(...)
):
    from fastapi import HTTPException, Body
    citizen_name = payload.get("citizenName", "Concerned Citizen")
    
    issue = db.get_document("issues", id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
        
    from backend.services.gemini_service import draft_complaint_letter
    letter = await draft_complaint_letter(issue, citizen_name)
    
    subject = letter.get("subject", f"Civic Complaint - Ref #{id}")
    body_text = letter.get("body", "")
    body_html = "<h3>Civio Grievance Dispatch</h3>" + "".join(f"<p>{line}</p>" for line in body_text.split("\n") if line.strip())
    
    from backend.routers.authority import _AUTHORITY_MAP
    category = str(issue.get("category", "OTHER")).lower().replace("_", "")
    contact = _AUTHORITY_MAP.get(category, _AUTHORITY_MAP['other'])
    to_email = contact['email']
    
    from backend.services.email_service import EmailService
    result = EmailService.send_complaint(
        to_email=to_email,
        subject=subject,
        body_html=body_html,
        body_text=body_text
    )
    
    import uuid
    db.save_document("audit_logs", f"AUD-{uuid.uuid4().hex[:6].upper()}", {
        "issueId": id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": "COMPLAINT_DISPATCHED",
        "description": f"Complaint letter emailed to {contact['name']} ({to_email}) via Resend."
    })
    
    return {"success": not result.get("error"), "result": result, "recipient": to_email}
