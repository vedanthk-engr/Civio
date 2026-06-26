import os
import json
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator
import google.generativeai as genai
from backend.database import db
from backend.services.gemini_service import draft_work_order

# Tool Implementations
def get_issue_details(issue_id: str) -> dict:
    return db.get_document("issues", issue_id) or {}

def get_department_workload(department: str) -> dict:
    issues = db.list_documents("issues")
    active = [x for x in issues if x.get("assignedDepartment") == department and x.get("status") in ["ASSIGNED", "IN_PROGRESS"]]
    return {"department": department, "activeIssuesCount": len(active), "status": "HIGH" if len(active) > 10 else "MODERATE" if len(active) > 4 else "LOW"}

def get_historical_resolution_time(category: str, department: str) -> dict:
    # BigQuery/analytics simulation
    averages = {
        "POTHOLE": 2.1,
        "WATER_LEAK": 1.5,
        "STREETLIGHT": 1.1,
        "WASTE": 0.5,
        "ROAD_DAMAGE": 4.5,
        "ENCROACHMENT": 6.2,
        "SEWAGE": 2.5,
        "OTHER": 3.0
    }
    return {"category": category, "department": department, "avgResolutionDays": averages.get(category, 2.5)}

def assign_issue(issue_id: str, department: str, priority: str) -> str:
    db.update_document("issues", issue_id, {
        "assignedDepartment": department,
        "status": "ASSIGNED",
        "validationScore": 85.0
    })
    return f"Issue assigned to {department} department with priority {priority}."

async def create_work_order_tool(issue_id: str, department: str) -> dict:
    issue = db.get_document("issues", issue_id)
    if not issue:
        return {"error": "Issue not found"}
        
    draft = await draft_work_order(issue)
    wo_id = f"WO-{uuid.uuid4().hex[:6].upper()}"
    
    wo_data = {
        "id": wo_id,
        "issueId": issue_id,
        "title": draft.get("title", f"Repair Work Order for {issue.get('title')}"),
        "description": draft.get("description", ""),
        "requiredMaterials": draft.get("requiredMaterials", []),
        "estimatedCost": draft.get("estimatedCost", 5000),
        "estimatedDuration": draft.get("estimatedDuration", "2 hours"),
        "requiredSkills": draft.get("requiredSkills", []),
        "safetyNotes": draft.get("safetyNotes", "Standard PPE required"),
        "department": department,
        "priority": draft.get("priority", "P3"),
        "status": "DRAFT",
        "createdAt": datetime.utcnow().isoformat() + "Z"
    }
    
    db.save_document("work_orders", wo_id, wo_data)
    db.update_document("issues", issue_id, {"workOrderId": wo_id})
    return wo_data

def schedule_work_order(work_order_id: str, date_str: str) -> str:
    db.update_document("work_orders", work_order_id, {
        "scheduledDate": date_str,
        "status": "SCHEDULED"
    })
    # Update issue status to reflect scheduled
    wo = db.get_document("work_orders", work_order_id)
    if wo:
        db.update_document("issues", wo["issueId"], {"status": "IN_PROGRESS"})
    return f"Work order {work_order_id} scheduled for {date_str}."

def send_notification(user_id: str, message: str, notification_type: str) -> str:
    # FCM Simulator: just save an audit log / print
    print(f"Notification sent to User {user_id}: {message} ({notification_type})")
    return f"FCM notification sent successfully to citizen device."

def get_similar_past_issues(lat: float, lng: float, category: str, radius_m: float = 100.0) -> list:
    # Simple proximity check
    issues = db.list_documents("issues")
    matches = []
    for issue in issues:
        if issue.get("category") == category:
            loc = issue.get("location", {})
            dist = ((loc.get("lat", 0) - lat)**2 + (loc.get("lng", 0) - lng)**2)**0.5 * 111000
            if dist <= radius_m:
                matches.append(issue)
    return [{"id": x["id"], "status": x["status"], "reportedAt": x["reportedAt"]} for x in matches]

def escalate_to_senior(issue_id: str, reason: str) -> str:
    db.update_document("issues", issue_id, {
        "status": "REPORTED",
        "communityNotes": [f"Escalation Flag: {reason}"]
    })
    return f"Issue escalated to Chief Engineer. Reason: {reason}."

def update_issue_status(issue_id: str, status: str) -> str:
    db.update_document("issues", issue_id, {"status": status})
    return f"Issue status updated to {status}."

# AI Resolution loop
async def run_resolution_agent(issue_id: str) -> AsyncGenerator[str, None]:
    """
    Executes the autonomous agent reasoning and tool calling loop.
    Streams execution logs as Server-Sent Events (SSE).
    """
    # 1. Start Agent Execution
    yield json.dumps({"step": 1, "thought": "Received issue for resolution. Analyzing issue details...", "action": "get_issue_details", "output": f"Fetching issue ID {issue_id}"})
    await asyncio.sleep(1.0)
    
    issue = get_issue_details(issue_id)
    if not issue:
        yield json.dumps({"step": 2, "thought": "Issue details could not be found in database. Terminating.", "action": "terminate", "output": "Error: Issue not found"})
        return
        
    yield json.dumps({"step": 2, "thought": f"Analyzed issue: '{issue.get('title')}' under category {issue.get('category')}. Finding responsible department...", "action": "resolve_department", "output": f"Category: {issue.get('category')} in ward {issue.get('location', {}).get('ward')}"})
    await asyncio.sleep(1.0)
    
    # Department routing logic
    category = issue.get("category")
    dept_map = {
        "POTHOLE": "Roads & Bridges",
        "WATER_LEAK": "Water Supply & Sewerage",
        "STREETLIGHT": "Electrical Engineering",
        "WASTE": "Solid Waste Management",
        "ROAD_DAMAGE": "Roads & Bridges",
        "ENCROACHMENT": "Town Planning & Revenue",
        "SEWAGE": "Water Supply & Sewerage",
        "OTHER": "Ward Administration"
    }
    dept = dept_map.get(category, "Ward Administration")
    
    yield json.dumps({"step": 3, "thought": f"The responsible department is '{dept}'. Querying current department workload to check backlogs...", "action": "get_department_workload", "output": f"Querying department '{dept}'"})
    await asyncio.sleep(1.0)
    
    workload = get_department_workload(dept)
    yield json.dumps({"step": 4, "thought": f"Department workload is {workload.get('status')} ({workload.get('activeIssuesCount')} active issues). Proceeding to assign issue and draft work order.", "action": "assign_issue & draft_work_order", "output": f"Assigning to {dept}"})
    await asyncio.sleep(1.0)
    
    # Assign issue
    priority = "P3"
    sev = issue.get("aiAnalysis", {}).get("severityScore", 5)
    if sev >= 9: priority = "P1"
    elif sev >= 7: priority = "P2"
    elif sev <= 3: priority = "P4"
    
    assign_msg = assign_issue(issue_id, dept, priority)
    
    # Create Work Order
    wo = await create_work_order_tool(issue_id, dept)
    wo_id = wo.get("id")
    
    yield json.dumps({"step": 5, "thought": f"Work order {wo_id} drafted in DRAFT state. Scheduling maintenance and notifying citizen...", "action": "schedule_work_order & notify", "output": f"Created Draft Work Order: {wo.get('title')}"})
    await asyncio.sleep(1.0)
    
    # Schedule for next day
    tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
    sched_msg = schedule_work_order(wo_id, tomorrow)
    
    # Notify reporter
    notify_msg = send_notification(
        issue.get("reportedBy"),
        f"Your issue '{issue.get('title')}' has been scheduled for repair on {tomorrow} by the {dept} department.",
        "STATUS_UPDATE"
    )
    
    # Save Audit Log
    db.save_document("audit_logs", f"AUD-{uuid.uuid4().hex[:6].upper()}", {
        "issueId": issue_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": "AUTO_ASSIGNED",
        "description": f"Agent autonomously routed issue to {dept}, drafted work order {wo_id}, and scheduled for {tomorrow}."
    })
    
    yield json.dumps({
        "step": 6,
        "thought": "Autonomous resolution loop completed successfully. Issue is assigned, scheduled, and citizen notified.",
        "action": "finish",
        "output": f"Issue transitioned to ASSIGNED/IN_PROGRESS. Work order {wo_id} is active."
    })
