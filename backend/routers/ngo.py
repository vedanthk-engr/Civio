from fastapi import APIRouter, HTTPException, Body
from typing import List, Optional
from pydantic import BaseModel

from backend.database import db
from backend.services.vertex_service import calculate_decay_score, WARD_BOUNDARIES

router = APIRouter(prefix="/ngo", tags=["NGO Operations"])

class CommitRequest(BaseModel):
    issueId: str
    ngoId: str

@router.get("/opportunities")
async def get_opportunities():
    """
    Returns unresolved issues as project opportunities for NGOs.
    """
    issues = db.list_documents("issues")
    # Filters out resolved/duplicate issues
    opportunities = [
        x for x in issues 
        if x.get("status") not in ["RESOLVED", "DUPLICATE", "CLOSED"]
    ]
    return opportunities

@router.post("/commit")
async def commit_to_opportunity(payload: CommitRequest):
    """
    Commit an NGO to work on resolving a reported civic issue.
    """
    issue = db.get_document("issues", payload.issueId)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
        
    # Update issue document to assign the NGO and set status to ACKNOWLEDGED
    updates = {
        "assignedNgo": payload.ngoId,
        "status": "ACKNOWLEDGED"
    }
    
    # Add a community note about the NGO commitment
    notes = issue.get("communityNotes", [])
    notes.append({
        "author": f"NGO Support ({payload.ngoId})",
        "text": f"NGO has committed to inspect and resolve this issue. Project started.",
        "timestamp": db.datetime.utcnow().isoformat() + "Z" if hasattr(db, 'datetime') else "2026-06-26T12:00:00Z"
    })
    updates["communityNotes"] = notes
    
    db.update_document("issues", payload.issueId, updates)
    return {"success": True, "message": f"NGO {payload.ngoId} committed to issue {payload.issueId}"}

@router.get("/recommendations")
async def get_ngo_recommendations():
    """
    Generates AI-driven ward recommendations for NGOs based on decay forecasting.
    """
    recommendations = []
    issues = db.list_documents("issues")
    
    for ward_name in WARD_BOUNDARIES.keys():
        # Get decay forecast for each ward
        decay_result = calculate_decay_score(ward_name, issues)
        score = decay_result.get("decay_score", 50.0)
        
        # Recommendations focus on high risk wards (score >= 60)
        if score >= 50.0:
            top_risks = decay_result.get("top_risks", [])
            recommended_actions = decay_result.get("recommended_actions", {})
            
            # Find issues in this ward matching the top risks
            matching_issues = [
                x for x in issues 
                if x.get("location", {}).get("ward") == ward_name 
                and x.get("category") in top_risks
                and x.get("status") not in ["RESOLVED", "DUPLICATE", "CLOSED"]
            ]
            
            recommendations.append({
                "ward": ward_name,
                "decayRiskScore": round(score, 1),
                "riskLevel": "HIGH" if score >= 75 else "MEDIUM" if score >= 50 else "LOW",
                "topRisks": top_risks,
                "actions": recommended_actions,
                "matchingIssuesCount": len(matching_issues),
                "issues": matching_issues[:3]  # Return top 3 issues needing immediate help
            })
            
    # Sort recommendations by highest decay score first
    recommendations.sort(key=lambda x: x["decayRiskScore"], reverse=True)
    return recommendations
