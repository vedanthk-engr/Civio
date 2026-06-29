from fastapi import APIRouter, HTTPException, status, Body
from typing import List, Optional
from pydantic import BaseModel
import uuid
from datetime import datetime, timedelta

from backend.database import db
from backend.models.issue import Issue, IssueCategory, IssueStatus
from backend.agents.triage_agent import run_triage_agent
from backend.services.gemini_service import detect_duplicate
from backend.services.validation_service import (
    classify_spam,
    compute_image_hash,
    is_duplicate_image,
    check_cross_modal_consistency,
    detect_ai_image
)

router = APIRouter(prefix="/issues", tags=["Issues"])

class TriageRequest(BaseModel):
    imageData: str  # Base64 or URL
    lat: float
    lng: float
    description: Optional[str] = ""

class CreateIssueRequest(BaseModel):
    title: str
    description: str
    category: IssueCategory
    subcategory: str
    location: dict
    aiAnalysis: dict
    reportedBy: str
    mediaUrls: Optional[List[str]] = []
    thumbnailUrl: Optional[str] = ""
    imageHash: Optional[str] = ""

@router.post("/triage")
async def triage_issue_endpoint(payload: TriageRequest):
    # 1. 3-Layer Spam Check
    if payload.description:
        spam_check = classify_spam(payload.description)
        if spam_check['verdict'] in ('spam', 'abuse'):
            spam_id = f"SPM-{uuid.uuid4().hex[:6].upper()}"
            db.save_document("spam_issues", spam_id, {
                "id": spam_id,
                "user_name": "Citizen",
                "description": payload.description,
                "lat": payload.lat,
                "lng": payload.lng,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "spam_verdict": spam_check['verdict'],
                "spam_reason": spam_check['reason'],
                "spam_confidence": spam_check.get('confidence', 80)
            })
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Submission rejected: {spam_check['reason']}"
            )
        if spam_check['verdict'] == 'test':
            spam_id = f"SPM-{uuid.uuid4().hex[:6].upper()}"
            db.save_document("spam_issues", spam_id, {
                "id": spam_id,
                "user_name": "Citizen",
                "description": payload.description,
                "lat": payload.lat,
                "lng": payload.lng,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "spam_verdict": spam_check['verdict'],
                "spam_reason": spam_check['reason'],
                "spam_confidence": spam_check.get('confidence', 80)
            })
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Test submission ignored."
            )

    # 2. AI Image Detection Check
    if payload.imageData:
        ai_img_check = detect_ai_image(payload.imageData)
        if ai_img_check.get("is_ai_generated") and ai_img_check.get("confidence", 0) >= 70:
            spam_id = f"SPM-{uuid.uuid4().hex[:6].upper()}"
            db.save_document("spam_issues", spam_id, {
                "id": spam_id,
                "user_name": "Citizen",
                "description": payload.description or "AI Image detected",
                "lat": payload.lat,
                "lng": payload.lng,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "spam_verdict": "synthetic_image",
                "spam_reason": f"Synthetic/AI-generated image detected. Signals: {', '.join(ai_img_check.get('signals', []))}",
                "spam_confidence": ai_img_check.get("confidence", 75)
            })
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Synthetic/AI-generated image detected. Submission rejected. Signals: {', '.join(ai_img_check.get('signals', []))}"
            )

    try:
        # Run Triage Agent (Gemini Vision Triage)
        triage_data = await run_triage_agent(
            payload.imageData,
            payload.lat,
            payload.lng,
            payload.description
        )
        
        # 2. Image Hash Duplicate Detection
        img_hash = compute_image_hash(payload.imageData)
        triage_data["aiAnalysis"]["imageHash"] = img_hash or ""
        
        dup_id = None
        existing_issues = db.list_documents("issues")
        
        if img_hash:
            stored_hashes = [x.get("imageHash") for x in existing_issues if x.get("imageHash")]
            dup_check = is_duplicate_image(img_hash, stored_hashes)
            if dup_check["is_duplicate"]:
                for x in existing_issues:
                    if x.get("imageHash") == dup_check["matched_hash"]:
                        dup_id = x.get("id")
                        break
        
        # Fallback to standard location-based duplicate check
        if not dup_id:
            dup_id = await detect_duplicate(
                triage_data["location"],
                triage_data["category"],
                payload.description or triage_data["title"],
                existing_issues
            )
            
        if dup_id:
            triage_data["aiAnalysis"]["duplicateOfId"] = dup_id
            
        # 3. Cross-Modal Consistency Check
        if payload.description and triage_data.get("category"):
            cm_check = check_cross_modal_consistency(
                triage_data["category"],
                payload.description,
                payload.imageData
            )
            if not cm_check.get("approved", True):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Description does not match the image. {cm_check.get('reason', '')}"
                )
            
        return triage_data
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Triage agent error: {str(e)}")

@router.post("")
async def create_issue(payload: CreateIssueRequest):
    issue_id = f"ISS-{uuid.uuid4().hex[:6].upper()}"
    reported_at = datetime.utcnow().isoformat() + "Z"
    
    # Calculate default deadline if not present
    sla_deadline = payload.aiAnalysis.get("severityScore", 5)
    sla_hours = 24 if sla_deadline >= 9 else 72 if sla_deadline >= 7 else 168 if sla_deadline >= 4 else 336
    sla_deadline_str = (datetime.utcnow() + timedelta(hours=sla_hours) if not payload.aiAnalysis.get("slaDeadline") else payload.aiAnalysis.get("slaDeadline"))
    
    issue_doc = {
        "id": issue_id,
        "title": payload.title,
        "description": payload.description,
        "category": payload.category.value,
        "subcategory": payload.subcategory,
        "location": payload.location,
        "mediaUrls": payload.mediaUrls,
        "thumbnailUrl": payload.thumbnailUrl or (payload.mediaUrls[0] if payload.mediaUrls else ""),
        "aiAnalysis": payload.aiAnalysis,
        "imageHash": payload.imageHash or payload.aiAnalysis.get("imageHash", ""),
        "reportedBy": payload.reportedBy,
        "verifiedBy": [],
        "upvotes": 0,
        "communityNotes": [],
        "status": IssueStatus.DUPLICATE.value if payload.aiAnalysis.get("duplicateOfId") else IssueStatus.REPORTED.value,
        "reportedAt": reported_at,
        "slaDeadline": payload.aiAnalysis.get("slaDeadline", (datetime.utcnow() + timedelta(hours=sla_hours)).isoformat() + "Z"),
        "slaBreached": False,
        "reporterTrustScore": 50.0,
        "validationScore": 50.0
    }
    
    db.save_document("issues", issue_id, issue_doc)
    
    # Update reporting user stats & XP
    user = db.get_document("users", payload.reportedBy)
    if user:
        user["issuesReported"] = user.get("issuesReported", 0) + 1
        user["xp"] = user.get("xp", 0) + 50  # 50 XP for reporting!
        user["level"] = 1 + (user["xp"] // 500)
        db.save_document("users", payload.reportedBy, user)
        
    return issue_doc

@router.get("", response_model=List[Issue])
async def list_issues(
    ward: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None
):
    issues = db.list_documents("issues")
    filtered = []
    for x in issues:
        # Ward filter
        if ward and x.get("location", {}).get("ward") != ward:
            continue
        # Category filter
        if category and x.get("category") != category:
            continue
        # Status filter
        if status and x.get("status") != status:
            continue
        filtered.append(x)
    return filtered

@router.get("/{id}")
async def get_issue(id: str):
    issue = db.get_document("issues", id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue

@router.patch("/{id}/status")
async def update_status(id: str, status_payload: dict = Body(...)):
    new_status = status_payload.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="Missing 'status' in payload")
        
    issue = db.get_document("issues", id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
        
    updates = {"status": new_status}
    if new_status == "RESOLVED":
        updates["resolvedAt"] = datetime.utcnow().isoformat() + "Z"
        
    db.update_document("issues", id, updates)
    
    # Audit log
    db.save_document("audit_logs", f"AUD-{uuid.uuid4().hex[:6].upper()}", {
        "issueId": id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": f"STATUS_UPDATED_{new_status}",
        "description": f"Status updated manually to {new_status}."
    })

    # Outbound WhatsApp alert
    from backend.routers.whatsapp import wa_notify
    reported_by = issue.get("reportedBy")
    if reported_by and len(reported_by) >= 10:
        msg = f"📢 *Civio Update*\n\nYour reported issue #{id} ({issue.get('category', 'civic issue')}) status has been updated to *{new_status}*.\n\nThank you for helping make our city self-healing! 🇮🇳"
        try:
            wa_notify(reported_by, msg)
        except Exception as e:
            print(f"[outbound_whatsapp] Failed to send notification: {e}")
    
    return {"success": True, "status": new_status}

@router.post("/{id}/verify")
async def verify_issue(id: str, payload: dict = Body(...)):
    userId = payload.get("userId")
    if not userId:
        raise HTTPException(status_code=400, detail="Missing 'userId'")
        
    issue = db.get_document("issues", id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
        
    verified_by = issue.get("verifiedBy", [])
    if userId in verified_by:
        return {"success": True, "message": "Already verified", "verifiedByCount": len(verified_by)}
        
    verified_by.append(userId)
    upvotes = issue.get("upvotes", 0) + 1  # Verify counts as upvote
    val_score = min(100.0, issue.get("validationScore", 50.0) + 5.0)
    
    db.update_document("issues", id, {
        "verifiedBy": verified_by,
        "upvotes": upvotes,
        "validationScore": val_score,
        "status": IssueStatus.VERIFIED.value if issue.get("status") == IssueStatus.REPORTED.value else issue.get("status")
    })
    
    # Update verifier user stats & XP
    user = db.get_document("users", userId)
    if user:
        user["issuesVerified"] = user.get("issuesVerified", 0) + 1
        user["xp"] = user.get("xp", 0) + 20  # 20 XP for verifying!
        user["level"] = 1 + (user["xp"] // 500)
        db.save_document("users", userId, user)
        
    return {"success": True, "verifiedByCount": len(verified_by)}

@router.post("/{id}/upvote")
async def upvote_issue(id: str):
    issue = db.get_document("issues", id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
        
    upvotes = issue.get("upvotes", 0) + 1
    db.update_document("issues", id, {"upvotes": upvotes})
    return {"success": True, "upvotes": upvotes}

@router.get("/debug/dup-check")
async def debug_dup_check(
    lat: float,
    lng: float,
    category: str,
    radius: int = 50
):
    """
    Test duplicate detection candidates without creating an issue.
    """
    try:
        existing_issues = db.list_documents("issues")
        dup_id = await detect_duplicate(
            {"lat": lat, "lng": lng, "ward": "Indiranagar"},
            category,
            "Duplicate check test",
            existing_issues
        )
        
        matched_issue = db.get_document("issues", dup_id) if dup_id else None
        
        return {
            "query": {"lat": lat, "lng": lng, "category": category, "radius_m": radius},
            "matched": dup_id is not None,
            "matched_issue_id": dup_id,
            "matched_title": matched_issue.get("title") if matched_issue else None,
            "matched_description": matched_issue.get("description") if matched_issue else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
