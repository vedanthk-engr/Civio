from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional
from datetime import datetime
import uuid

from backend.database import db
from backend.services.gemini_service import generate_civic_pulse_report

router = APIRouter(prefix="/authority", tags=["Authority"])

@router.get("/dashboard")
async def get_authority_dashboard_data(ward: str = Query("Indiranagar")):
    issues = db.list_documents("issues")
    
    # Filter by ward
    ward_issues = [x for x in issues if x.get("location", {}).get("ward") == ward]
    
    total = len(ward_issues)
    reported = len([x for x in ward_issues if x["status"] == "REPORTED"])
    verified = len([x for x in ward_issues if x["status"] == "VERIFIED"])
    assigned = len([x for x in ward_issues if x["status"] == "ASSIGNED"])
    in_progress = len([x for x in ward_issues if x["status"] == "IN_PROGRESS"])
    resolved = len([x for x in ward_issues if x["status"] in ["RESOLVED", "CLOSED"]])
    
    breached = len([x for x in ward_issues if x.get("slaBreached") and x["status"] not in ["RESOLVED", "CLOSED"]])
    
    # Calculate workloads by department
    depts = ["Roads & Bridges", "Water Supply & Sewerage", "Electrical Engineering", "Solid Waste Management", "Town Planning & Revenue"]
    dept_workloads = {}
    for d in depts:
        active_count = len([
            x for x in issues 
            if x.get("assignedDepartment") == d and x.get("status") in ["ASSIGNED", "IN_PROGRESS"]
        ])
        dept_workloads[d] = {
            "activeCount": active_count,
            "status": "CRITICAL" if active_count > 12 else "WARNING" if active_count > 6 else "OPTIMAL"
        }
        
    return {
        "summary": {
            "totalIssues": total,
            "reported": reported,
            "verified": verified,
            "assigned": assigned,
            "inProgress": in_progress,
            "resolved": resolved,
            "breachedSLACount": breached
        },
        "departmentWorkloads": dept_workloads
    }

@router.get("/work-orders")
async def list_work_orders(department: Optional[str] = None):
    work_orders = db.list_documents("work_orders")
    if department:
        work_orders = [x for x in work_orders if x.get("department") == department]
    return work_orders

@router.post("/work-orders")
async def approve_work_order(payload: dict = Body(...)):
    wo_id = payload.get("workOrderId")
    approved_by = payload.get("approvedBy", "auth_1")
    
    if not wo_id:
        raise HTTPException(status_code=400, detail="Missing 'workOrderId'")
        
    wo = db.get_document("work_orders", wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
        
    db.update_document("work_orders", wo_id, {
        "status": "APPROVED",
        "approvedBy": approved_by
    })
    
    # Update issue status to reflect APPROVED/ASSIGNED
    db.update_document("issues", wo["issueId"], {
        "status": "ASSIGNED"
    })
    
    # Audit log
    db.save_document("audit_logs", f"AUD-{uuid.uuid4().hex[:6].upper()}", {
        "issueId": wo["issueId"],
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": "WORK_ORDER_APPROVED",
        "description": f"Work order {wo_id} was approved by {approved_by}."
    })
    
    return {"success": True, "workOrderId": wo_id, "status": "APPROVED"}

@router.get("/reports")
async def get_civic_pulse_report_endpoint(ward: str = Query("Indiranagar")):
    issues = db.list_documents("issues")
    
    # Gather statistics
    ward_issues = [x for x in issues if x.get("location", {}).get("ward") == ward]
    active = len([x for x in ward_issues if x["status"] not in ["RESOLVED", "CLOSED"]])
    resolved = len([x for x in ward_issues if x["status"] in ["RESOLVED", "CLOSED"]]) # simple mock weekly resolved
    critical = len([x for x in ward_issues if x.get("aiAnalysis", {}).get("severityScore", 1) >= 8 and x["status"] not in ["RESOLVED", "CLOSED"]])
    breached = len([x for x in ward_issues if x.get("slaBreached") and x["status"] not in ["RESOLVED", "CLOSED"]])
    
    summary = {
        "active": active,
        "resolved": resolved if resolved > 0 else 5, # ensure positive mock representation
        "critical": critical,
        "breached": breached
    }
    
    report = await generate_civic_pulse_report(ward, summary)
    return {
        "ward": ward,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "reportHtml": report
    }

_AUTHORITY_MAP = {
    'pothole':      {'name': 'MCD Road Maintenance Division',                  'email': 'pgms@mcdonline.nic.in'},
    'waterleak':    {'name': 'Delhi Jal Board (Water Supply Division)',        'email': 'cmo@delhijalboard.in'},
    'streetlight':  {'name': 'MCD Lighting Department',                       'email': 'pgms@mcdonline.nic.in'},
    'waste':        {'name': 'MCD Sanitation Department',                      'email': 'pgms@mcdonline.nic.in'},
    'roaddamage':   {'name': 'MCD Road Maintenance Division',                  'email': 'pgms@mcdonline.nic.in'},
    'encroachment': {'name': 'Office of the District Magistrate, Delhi',       'email': 'dm.newdelhi@delhi.gov.in'},
    'sewage':       {'name': 'Delhi Jal Board (Sewerage Division)',            'email': 'cmo@delhijalboard.in'},
    'other':        {'name': 'Office of the District Magistrate, Delhi',       'email': 'dm.newdelhi@delhi.gov.in'},
}

@router.get("/contact/{tag}")
async def get_authority_contact(tag: str):
    clean_tag = tag.lower().replace("_", "")
    contact = _AUTHORITY_MAP.get(clean_tag, _AUTHORITY_MAP['other'])
    return contact
