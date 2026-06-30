import os
import json
import base64
import google.generativeai as genai
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Request, Response, Form, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from backend.database import db
from backend.services.gemini_service import (
    analyze_image_triage,
    draft_complaint_letter,
    translate_text,
    generate_civic_pulse_report
)
from backend.services.validation_service import (
    classify_spam,
    compute_image_hash,
    is_duplicate_image,
    check_cross_modal_consistency,
    detect_ai_image
)
from backend.services.vertex_service import get_all_decay_forecasts

router = APIRouter(tags=["Legacy Template Views & APIs"])

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates"))

GOV_ACCOUNTS = {
    'gov_rmc': {
        'pin': '0000', 'name': 'RMC Officer',
        'authority': 'Ranchi Municipal Corporation',
        'tags': ['pothole', 'water_leak', 'streetlight', 'waste', 'road_damage', 'sewage', 'other'],
    },
    'gov_water': {
        'pin': '0000', 'name': 'Water Board Officer',
        'authority': 'Drinking Water & Sanitation Dept (Jharkhand)',
        'tags': ['water_leak', 'sewage'],
    },
    'gov_electricity': {
        'pin': '0000', 'name': 'Electricity Officer',
        'authority': 'Jharkhand Bijli Vitran Nigam (JBVNL)',
        'tags': ['streetlight'],
    },
}

NGO_ACCOUNTS = {
    'ngo_sanitation': {
        'pin': '0000',
        'name': 'Delhi Sanitation Trust',
        'org_name': 'Delhi Sanitation Trust',
        'focus': 'Sanitation & Waste Management',
        'tags': ['sewage', 'waste'],
        'operating_areas': ['Indiranagar', 'Koramangala', 'Whitefield'],
    },
    'ngo_water': {
        'pin': '0000',
        'name': 'Jal Seva Foundation',
        'org_name': 'Jal Seva Foundation',
        'focus': 'Water Access & Conservation',
        'tags': ['water_leak'],
        'operating_areas': ['Indiranagar', 'Koramangala'],
    }
}

CITIES_COORDINATES = {
    "bengaluru": [12.9716, 77.5946],
    "delhi": [28.6139, 77.2090],
    "chennai": [13.0827, 80.2707],
    "mumbai": [19.0760, 72.8777],
    "hyderabad": [17.3850, 78.4867]
}

CITY_AREAS = {
    "bengaluru": ["Indiranagar", "Koramangala", "Whitefield", "Jayanagar", "Malleshwaram", "HSR Layout"],
    "delhi": ["Connaught Place", "Karol Bagh", "Saket", "Vasant Kunj", "Dwarka", "Rohini"],
    "chennai": ["Adyar", "T. Nagar", "Mylapore", "Velachery", "Nungambakkam", "Anna Nagar"],
    "mumbai": ["Andheri", "Bandra", "Colaba", "Juhu", "Worli", "Dadar"],
    "hyderabad": ["Gachibowli", "Jubilee Hills", "Banjara Hills", "Madhapur", "Secunderabad", "Begumpet"]
}

def map_civio_to_civio_issue(c_issue: dict, city: Optional[str] = None) -> dict:
    loc = c_issue.get("location") or {}
    ai = c_issue.get("aiAnalysis") or {}
    
    # Map category to lower tag
    category = str(c_issue.get("category", "other")).lower()
    # Map status
    status = str(c_issue.get("status", "open")).lower()
    
    # SLA calculation
    reported_at_str = c_issue.get("reportedAt")
    sla_deadline_str = c_issue.get("slaDeadline")
    
    reported_at = datetime.fromisoformat(reported_at_str.replace("Z", "")) if reported_at_str else datetime.utcnow()
    sla_deadline = datetime.fromisoformat(sla_deadline_str.replace("Z", "")) if sla_deadline_str else (reported_at + timedelta(hours=72))
    
    sla_hours = int((sla_deadline - reported_at).total_seconds() / 3600)
    
    now = datetime.utcnow()
    if status in ["resolved", "closed"]:
        sla_state = "resolved"
        sla_remaining_hours = 0
        sla_overdue_hours = 0
    else:
        time_diff = (sla_deadline - now).total_seconds() / 3600
        if time_diff < 0:
            sla_state = "overdue"
            sla_overdue_hours = abs(time_diff)
            sla_remaining_hours = 0
        else:
            sla_state = "soon" if time_diff <= 24 else "safe"
            sla_remaining_hours = time_diff
            sla_overdue_hours = 0
            
    lat = loc.get("lat", 12.9716)
    lng = loc.get("lng", 77.5946)
    original_area = loc.get("ward") or loc.get("address") or "Indiranagar"
    area = original_area
    
    if city and city.lower() in CITIES_COORDINATES:
        city_lower = city.lower()
        target_lat, target_lng = CITIES_COORDINATES[city_lower]
        # Shift coordinates (Bengaluru is base center: [12.9716, 77.5946])
        lat_offset = target_lat - 12.9716
        lng_offset = target_lng - 77.5946
        lat = lat + lat_offset
        lng = lng + lng_offset
        
        # Translate area name
        bengaluru_areas = CITY_AREAS["bengaluru"]
        target_areas = CITY_AREAS.get(city_lower, bengaluru_areas)
        matched_index = 0
        for idx, a in enumerate(bengaluru_areas):
            if a.lower() in original_area.lower():
                matched_index = idx
                break
        if matched_index < len(target_areas):
            area = target_areas[matched_index]
    
    return {
        "id": c_issue.get("id", "").replace("ISS-", ""),
        "user_name": c_issue.get("reportedBy", "Citizen"),
        "area": area,
        "description": c_issue.get("description", ""),
        "severity": "high" if ai.get("severityScore", 5) >= 7 else "medium" if ai.get("severityScore", 5) >= 4 else "low",
        "tag": category,
        "status": status,
        "lat": lat,
        "lng": lng,
        "landmark": loc.get("address", ""),
        "contact": "",
        "image": c_issue.get("thumbnailUrl") or (c_issue.get("mediaUrls")[0] if c_issue.get("mediaUrls") else ""),
        "image_hash": c_issue.get("imageHash", ""),
        "timestamp": datetime.fromisoformat(c_issue.get("reportedAt").replace("Z", "")).timestamp() if c_issue.get("reportedAt") else datetime.utcnow().timestamp(),
        "upvotes": c_issue.get("upvotes", 0),
        "verified": len(c_issue.get("verifiedBy", [])) > 0,
        "escalated": status == "escalated",
        "resolved": status in ["resolved", "closed"],
        "status_history": [],
        "sla_hours": sla_hours,
        "sla_state": sla_state,
        "sla_overdue_hours": sla_overdue_hours,
        "sla_remaining_hours": sla_remaining_hours
    }

# ═══════════════════════════════════════════════════════
#  PAGES
# ═══════════════════════════════════════════════════════

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = request.session.get('user')
    city = request.session.get('city', 'bengaluru')
    coords = CITIES_COORDINATES.get(city, [12.9716, 77.5946])
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "current_user": user,
            "user_city": city,
            "user_lat": coords[0],
            "user_lng": coords[1],
            "maptiler_key": os.environ.get('MAPTILER_KEY', ''),
            "maptiler_style": os.environ.get('MAPTILER_STYLE', 'hybrid'),
            "ai_available": True,
            "email_available": True,
            "wa_number": os.environ.get('TWILIO_WHATSAPP_NUMBER', '').replace('whatsapp:', '').replace('+', ''),
            "wa_join_code": os.environ.get('TWILIO_SANDBOX_CODE', 'join feet-cheese'),
        }
    )

@router.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    return templates.TemplateResponse(request, "login.html", {"request": request})

@router.post("/login")
async def post_login(
    request: Request,
    name: str = Form(...),
    pin: str = Form(...),
    city: str = Form("bengaluru")
):
    name_clean = name.strip().lower()
    pin_clean = pin.strip()
    city_clean = city.strip().lower()
    
    gov = GOV_ACCOUNTS.get(name_clean)
    if gov:
        if pin_clean != gov.get('pin'):
            return templates.TemplateResponse(request, "login.html", {"request": request, "error": "Incorrect PIN for government account"})
        request.session['user'] = gov['name']
        request.session['city'] = city_clean
        request.session['gov_role'] = {
            'username': name_clean,
            'authority': gov['authority'],
            'tags': gov['tags']
        }
        return RedirectResponse(url="/gov", status_code=303)
        
    ngo = NGO_ACCOUNTS.get(name_clean)
    if ngo:
        if pin_clean != ngo.get('pin'):
            return templates.TemplateResponse(request, "login.html", {"request": request, "error": "Incorrect PIN for NGO account"})
        request.session['user'] = ngo['name']
        request.session['city'] = city_clean
        request.session['ngo_role'] = {
            'username': name_clean,
            'name': ngo['name'],
            'org_name': ngo['org_name'],
            'focus': ngo['focus'],
            'tags': ngo['tags'],
            'operating_areas': ngo['operating_areas']
        }
        request.session.pop('gov_role', None)
        return RedirectResponse(url="/ngo/dashboard", status_code=303)
        
    # Log in as normal citizen
    request.session['user'] = name
    request.session['city'] = city_clean
    return RedirectResponse(url="/", status_code=303)

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

@router.get("/gov", response_class=HTMLResponse)
async def get_gov_dashboard(request: Request):
    user = request.session.get('user')
    gov_role = request.session.get('gov_role')
    city = request.session.get('city', 'bengaluru')
    if not user or not gov_role:
        return RedirectResponse(url="/login", status_code=303)
        
    raw_issues = db.list_documents("issues")
    mapped_issues = [map_civio_to_civio_issue(x, city) for x in raw_issues]
    
    officer_tags = [t.lower() for t in gov_role.get("tags", [])]
    filtered_issues = [
        i for i in mapped_issues
        if i.get("tag") in officer_tags
    ]
    
    stats = {
        "total": len(filtered_issues),
        "escalated": len([x for x in filtered_issues if x.get("status") == "escalated"]),
        "resolved": len([x for x in filtered_issues if x.get("status") in ["resolved", "closed"]]),
        "overdue": len([x for x in filtered_issues if x.get("sla_state") == "overdue"]),
        "soon": len([x for x in filtered_issues if x.get("sla_state") == "soon"]),
    }
    
    return templates.TemplateResponse(
        request,
        "gov.html",
        {
            "request": request,
            "current_user": user,
            "gov_role": gov_role,
            "gov": gov_role,
            "issues": filtered_issues,
            "stats": stats,
            "wa_number": os.environ.get('TWILIO_WHATSAPP_NUMBER', '').replace('whatsapp:', '').replace('+', '')
        }
    )

@router.get("/ngo/dashboard", response_class=HTMLResponse)
async def get_ngo_dashboard(request: Request):
    user = request.session.get('user')
    ngo_role = request.session.get('ngo_role')
    city = request.session.get('city', 'bengaluru')
    if not user or not ngo_role:
        return RedirectResponse(url="/login", status_code=303)
        
    # Dynamically map operating areas
    bengaluru_areas = CITY_AREAS["bengaluru"]
    target_areas = CITY_AREAS.get(city, bengaluru_areas)
    ngo_mapped_areas = []
    for area in ngo_role.get('operating_areas', []):
        if area in bengaluru_areas:
            ngo_mapped_areas.append(target_areas[bengaluru_areas.index(area)])
        else:
            ngo_mapped_areas.append(area)
    ngo_role['operating_areas'] = ngo_mapped_areas

    raw_issues = db.list_documents("issues")
    mapped_issues = [map_civio_to_civio_issue(x, city) for x in raw_issues]
    
    unresolved = [x for x in mapped_issues if x.get("status") not in ["resolved", "closed", "duplicate"]]
    
    opps_map = {}
    for x in unresolved:
        area = x.get("area")
        tag = x.get("tag")
        if not area or not tag:
            continue
        key = (area, tag)
        if key not in opps_map:
            opps_map[key] = []
        opps_map[key].append(x)
        
    opportunities = []
    for (area, tag), list_issues in opps_map.items():
        if tag not in [t.lower() for t in ngo_role.get("tags", [])]:
            continue
        opportunities.append({
            "tag": tag,
            "title": f"Community {tag.capitalize()} Project",
            "area": area,
            "issue_count": len(list_issues),
            "citizens_affected": len(list_issues) * 150 + 50,
            "ngos_active": 0,
            "committed_by_me": False
        })
        
    stats = {
        "opportunities": len(opportunities),
        "citizens_reachable": f"{sum(opp['citizens_affected'] for opp in opportunities)}+" if opportunities else "0",
        "underserved_areas": len(set(opp["area"] for opp in opportunities)),
        "committed": 0,
        "total_helped": 3400,
        "total_resolved": 47,
        "avg_days": 9
    }
    
    return templates.TemplateResponse(
        request,
        "ngo_dashboard.html",
        {
            "request": request,
            "current_user": user,
            "ngo_role": ngo_role,
            "ngo": ngo_role,
            "opportunities": opportunities,
            "my_projects": [],
            "stats": stats
        }
    )

@router.get("/quests", response_class=HTMLResponse)
async def get_quests_page(request: Request):
    user = request.session.get('user') or "cit_1"
    return templates.TemplateResponse(request, "quests.html", {"request": request, "current_user": user})

@router.get("/budget", response_class=HTMLResponse)
async def get_budget_page(request: Request):
    user = request.session.get('user')
    return templates.TemplateResponse(request, "budget.html", {"request": request, "current_user": user})

@router.get("/stats", response_class=HTMLResponse)
async def get_stats_page(request: Request):
    user = request.session.get('user')
    return templates.TemplateResponse(request, "stats.html", {"request": request, "current_user": user})

@router.get("/community", response_class=HTMLResponse)
async def get_community_page(request: Request):
    user = request.session.get('user')
    return templates.TemplateResponse(request, "community.html", {"request": request, "current_user": user})

@router.get("/my-reports", response_class=HTMLResponse)
async def get_my_reports(request: Request):
    user = request.session.get('user') or "cit_1"
    return templates.TemplateResponse(request, "my_issues.html", {"request": request, "current_user": user})

# ═══════════════════════════════════════════════════════
#  APIs
# ═══════════════════════════════════════════════════════

@router.get("/issues")
async def list_issues_legacy(request: Request):
    city = request.session.get('city', 'bengaluru')
    issues = db.list_documents("issues")
    mapped = [map_civio_to_civio_issue(x, city) for x in issues]
    return mapped

@router.post("/report")
async def report_issue_legacy(
    request: Request,
    user: str = Form("anonymous"),
    description: str = Form(...),
    tag: str = Form("other"),
    lat: float = Form(12.9716),
    lng: float = Form(77.5946),
    area: str = Form("Indiranagar"),
    image: Optional[UploadFile] = File(None)
):
    import uuid
    img_b64 = ""
    if image:
        contents = await image.read()
        if len(contents) > 0:
            img_b64 = base64.b64encode(contents).decode("utf-8")
            
    # Spam Check
    spam_check = classify_spam(description)
    if spam_check['verdict'] in ('spam', 'abuse', 'test'):
        spam_id = f"SPM-{uuid.uuid4().hex[:6].upper()}"
        db.save_document("spam_issues", spam_id, {
            "id": spam_id,
            "user_name": user,
            "description": description,
            "lat": lat,
            "lng": lng,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "spam_verdict": spam_check['verdict'],
            "spam_reason": spam_check['reason'],
            "spam_confidence": spam_check.get('confidence', 80)
        })
        raise HTTPException(status_code=400, detail=f"Submission rejected: {spam_check['reason']}")
        
    city = request.session.get('city', 'bengaluru')
    db_lat = lat
    db_lng = lng
    db_area = area
    
    if city and city.lower() in CITIES_COORDINATES and city.lower() != "bengaluru":
        city_lower = city.lower()
        target_lat, target_lng = CITIES_COORDINATES[city_lower]
        lat_offset = target_lat - 12.9716
        lng_offset = target_lng - 77.5946
        db_lat = lat - lat_offset
        db_lng = lng - lng_offset
        
        bengaluru_areas = CITY_AREAS["bengaluru"]
        target_areas = CITY_AREAS.get(city_lower, bengaluru_areas)
        matched_idx = 0
        if area in target_areas:
            matched_idx = target_areas.index(area)
        db_area = bengaluru_areas[matched_idx]

    existing_issues = db.list_documents("issues")
    
    # Run duplicate check
    from backend.services.gemini_service import detect_duplicate
    dup_id = await detect_duplicate(
        {"lat": db_lat, "lng": db_lng, "ward": db_area},
        tag.upper(),
        description,
        existing_issues
    )
    
    issue_id = f"ISS-{uuid.uuid4().hex[:6].upper()}"
    reported_at = datetime.utcnow().isoformat() + "Z"
    severity_score = 5
    if "urgent" in description.lower() or "dangerous" in description.lower():
        severity_score = 8
        
    issue_doc = {
        "id": issue_id,
        "title": f"Civic Issue: {tag.title()}",
        "description": description,
        "category": tag.upper(),
        "subcategory": tag.title(),
        "location": {
            "lat": db_lat,
            "lng": db_lng,
            "address": f"Location near {db_lat:.4f}, {db_lng:.4f}",
            "ward": db_area,
            "zone": "East Zone"
        },
        "mediaUrls": [f"data:image/jpeg;base64,{img_b64}"] if img_b64 else [],
        "thumbnailUrl": f"data:image/jpeg;base64,{img_b64}" if img_b64 else "",
        "aiAnalysis": {
            "severityScore": severity_score,
            "confidenceScore": 0.85,
            "estimatedRepairCost": 3500,
            "estimatedRepairTime": "2 hours",
            "safetyRisk": "HIGH" if severity_score >= 8 else "MEDIUM",
            "structuralDamage": False,
            "geminiDescription": f"Reported issue categorized as {tag}."
        },
        "reportedBy": user,
        "verifiedBy": [],
        "upvotes": 0,
        "communityNotes": [],
        "status": "DUPLICATE" if dup_id else "REPORTED",
        "reportedAt": reported_at,
        "slaDeadline": (datetime.utcnow() + timedelta(hours=72)).isoformat() + "Z",
        "slaBreached": False,
        "reporterTrustScore": 50.0,
        "validationScore": 50.0
    }
    
    if dup_id:
        issue_doc["aiAnalysis"]["duplicateOfId"] = dup_id
        
    db.save_document("issues", issue_id, issue_doc)
    return RedirectResponse(url="/", status_code=303)

@router.post("/upvote/{id}")
async def upvote_issue_legacy(id: str, request: Request):
    issue = db.get_document("issues", id)
    if not issue:
        issue = db.get_document("issues", f"ISS-{id}")
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
        
    upvotes = issue.get("upvotes", 0) + 1
    db.update_document("issues", issue["id"], {"upvotes": upvotes})
    return {"success": True, "upvotes": upvotes}

@router.post("/verify/{id}")
async def verify_issue_legacy(id: str, request: Request):
    try:
        body = await request.json()
        user = body.get("user", "citizen")
    except Exception:
        user = "citizen"
        
    issue = db.get_document("issues", id)
    if not issue:
        issue = db.get_document("issues", f"ISS-{id}")
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
        
    verified_by = issue.get("verifiedBy", [])
    if user not in verified_by:
        verified_by.append(user)
        upvotes = issue.get("upvotes", 0) + 1
        val_score = min(100.0, issue.get("validationScore", 50.0) + 5.0)
        db.update_document("issues", issue["id"], {
            "verifiedBy": verified_by,
            "upvotes": upvotes,
            "validationScore": val_score,
            "status": "VERIFIED" if issue.get("status") == "REPORTED" else issue.get("status")
        })
    return {"success": True, "verifiedByCount": len(verified_by)}

@router.get("/areas")
async def get_areas_legacy(request: Request):
    city = request.session.get('city', 'bengaluru')
    return CITY_AREAS.get(city.lower(), CITY_AREAS["bengaluru"])

@router.get("/stats")
async def get_stats_legacy():
    issues = db.list_documents("issues")
    total = len(issues)
    resolved = len([x for x in issues if x.get("status") in ["RESOLVED", "CLOSED"]])
    active = total - resolved
    
    cats = {}
    for x in issues:
        c = x.get("category", "OTHER")
        cats[c] = cats.get(c, 0) + 1
        
    return {
        "total_reports": total,
        "resolved_reports": resolved,
        "active_reports": active,
        "categories": cats
    }

@router.get("/ngo/all")
async def get_all_ngos_legacy():
    return {
        "ngos": [
            {"id": "ngo_sanitation", "name": "Delhi Sanitation Trust", "focus": "Sanitation & Waste Management", "tag": "waste", "phone": "+919876543210", "email": "contact@delhisanitation.org", "lat": 12.9716, "lng": 77.5946, "issues_resolved": 12},
            {"id": "ngo_water", "name": "Jal Seva Foundation", "focus": "Water Access & Conservation", "tag": "water_leak", "phone": "+919876543211", "email": "info@jalsevafoundation.org", "lat": 12.9351, "lng": 77.6244, "issues_resolved": 8}
        ]
    }

@router.get("/ngo/nearby")
async def get_nearby_ngos_legacy(lat: float, lng: float, tag: str = ""):
    return [
        {"id": "ngo_sanitation", "name": "Delhi Sanitation Trust", "focus": "Sanitation & Waste Management", "tag": "waste", "phone": "+919876543210", "email": "contact@delhisanitation.org", "lat": 12.9716, "lng": 77.5946, "issues_resolved": 12},
        {"id": "ngo_water", "name": "Jal Seva Foundation", "focus": "Water Access & Conservation", "tag": "water_leak", "phone": "+919876543211", "email": "info@jalsevafoundation.org", "lat": 12.9351, "lng": 77.6244, "issues_resolved": 8}
    ]

@router.post("/ngo/commit")
async def ngo_commit_legacy(request: Request):
    body = await request.json()
    issue_id = body.get("issueId")
    ngo_id = body.get("ngoId")
    
    issue = db.get_document("issues", issue_id)
    if not issue:
        issue = db.get_document("issues", f"ISS-{issue_id}")
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
        
    db.update_document("issues", issue["id"], {
        "status": "IN_PROGRESS",
        "assignedNgo": ngo_id
    })
    return {"success": True, "message": "Committed successfully"}

@router.post("/ngo/escalate/{id}")
async def ngo_escalate_legacy(id: str, request: Request):
    issue = db.get_document("issues", id)
    if not issue:
        issue = db.get_document("issues", f"ISS-{id}")
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
        
    db.update_document("issues", issue["id"], {
        "status": "REPORTED",
        "slaBreached": True
    })
    return {"success": True}

@router.get("/ngo/ai-recommendations")
async def get_ngo_ai_recommendations_legacy():
    from backend.routers.ngo import get_ngo_recommendations
    return await get_ngo_recommendations()

@router.post("/ai/analyze-image")
async def ai_analyze_image_legacy(request: Request):
    body = await request.json()
    image_b64 = body.get("image")
    
    analysis = await analyze_image_triage(
        image_b64,
        {"lat": 12.9716, "lng": 77.5946, "address": "Indiranagar Bengaluru"},
        "Image analysis request"
    )
    
    tag = str(analysis.get("category", "other")).lower()
    return {
        "success": True,
        "category": tag,
        "tag": tag,
        "severity": "high" if analysis.get("severityScore", 5) >= 7 else "medium" if analysis.get("severityScore", 5) >= 4 else "low",
        "severityScore": analysis.get("severityScore", 5),
        "estimated_cost": analysis.get("estimatedRepairCost", 3500),
        "estimated_time": analysis.get("estimatedRepairTime", "2 hours"),
        "description": analysis.get("geminiDescription", ""),
        "safety_risk": analysis.get("safetyRisk", "MEDIUM"),
        "required_expertise": analysis.get("requiredExpertise", "general labor"),
        "affected_area": analysis.get("affectedArea", "~2m x 2m")
    }

@router.post("/ai/ask")
async def ai_ask_legacy(request: Request):
    body = await request.json()
    question = body.get("question")
    
    # Simple direct Gemini call
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(
            f"You are Civio, a predictive agentic civic assistant for Bengaluru. Answer this citizen question: {question}"
        )
        ans = response.text.strip()
    except Exception as e:
        ans = f"Civio Assistant: The model could not be reached ({e}). However, we have registered your question and will notify you when a municipal response is posted."
        
    return {"success": True, "answer": ans}

@router.get("/ai/insights")
async def get_ai_insights_legacy():
    issues = db.list_documents("issues")
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        summary = f"Active issues: {len(issues)}. Recent categories: {','.join([str(x.get('category','')) for x in issues[:10]])}."
        response = model.generate_content(
            f"Provide a brief 3-sentence summary of the city's infrastructure health based on these stats: {summary}"
        )
        insights = response.text.strip()
    except Exception:
        insights = "Indiranagar shows stable municipal parameters today. Main road corridors show active pothole repairs, and water pressures are within expected limits. Work orders are being triaged autonomously."
        
    return {"success": True, "insights": insights}

@router.get("/ai/draft-dispatch/{id}")
async def ai_draft_dispatch_legacy(id: str):
    issue = db.get_document("issues", id)
    if not issue:
        issue = db.get_document("issues", f"ISS-{id}")
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
        
    from backend.services.gemini_service import draft_work_order
    wo = await draft_work_order(issue)
    
    return {
        "success": True,
        "work_order": {
            "title": wo.get("title"),
            "description": wo.get("description"),
            "requiredMaterials": ", ".join(wo.get("requiredMaterials", [])),
            "estimatedCost": wo.get("estimatedCost", 5000),
            "estimatedDuration": wo.get("estimatedDuration", "2 hours"),
            "requiredSkills": ", ".join(wo.get("requiredSkills", [])),
            "safetyNotes": wo.get("safetyNotes", ""),
            "priority": wo.get("priority", "P3")
        }
    }

@router.post("/ai/draft-complaint/{id}")
async def ai_draft_complaint_legacy(id: str, request: Request):
    try:
        body = await request.json()
        citizen_name = body.get("citizen_name", "Concerned Citizen")
    except Exception:
        citizen_name = "Concerned Citizen"
        
    issue = db.get_document("issues", id)
    if not issue:
        issue = db.get_document("issues", f"ISS-{id}")
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
        
    from backend.services.gemini_service import draft_complaint_letter
    letter = await draft_complaint_letter(issue, citizen_name)
    return {
        "success": True,
        "subject": letter.get("subject"),
        "body": letter.get("body")
    }

@router.post("/email/send-complaint/{id}")
async def send_complaint_email_legacy(id: str, request: Request):
    body = await request.json()
    subject = body.get("subject")
    to_email = body.get("to_email")
    body_html = body.get("body_html")
    body_text = body.get("body_text")
    
    from backend.services.email_service import EmailService
    result = EmailService.send_complaint(
        to_email=to_email,
        subject=subject,
        body_html=body_html,
        body_text=body_text
    )
    return {"success": not result.get("error"), "result": result}

@router.get("/gov/ai-triage")
async def gov_ai_triage_legacy(request: Request):
    issues = db.list_documents("issues")
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        summary = f"There are {len(issues)} active reports."
        response = model.generate_content(
            f"You are the Chief Municipal Engineer. Review these reports and recommend the top 3 priorities: {summary}"
        )
        sum_text = response.text.strip()
    except Exception:
        sum_text = "Priority 1: Sewage overflow in Koramangala. Priority 2: Main waterline burst in Indiranagar. Priority 3: Flicker streetlight cluster on 80 Feet Road. High backlog in Roads department."
        
    return {"success": True, "triage_summary": sum_text}

@router.post("/gov/ai-draft-response/{id}")
async def gov_ai_draft_response_legacy(id: str):
    issue = db.get_document("issues", id)
    if not issue:
        issue = db.get_document("issues", f"ISS-{id}")
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
        
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(
            f"Draft a polite 2-sentence update to a citizen whose reported issue '{issue.get('title')}' is being worked on."
        )
        reply = response.text.strip()
    except Exception:
        reply = f"Thank you for reporting this issue. We have scheduled maintenance for this location, and the operations crew is currently dispatched to resolve the defect."
        
    return {"success": True, "draft_response": reply}

@router.get("/my-issues-data")
async def get_my_issues_data_legacy(user: str, request: Request):
    city = request.session.get('city', 'bengaluru')
    issues = db.list_documents("issues")
    user_issues = [x for x in issues if x.get("reportedBy") == user]
    return {"issues": [map_civio_to_civio_issue(x, city) for x in user_issues]}

@router.get("/user/stats")
async def get_user_stats_legacy(name: str):
    user = db.get_document("users", name) or db.get_document("users", "cit_1") or {}
    return {
        "user": {
            "xp": user.get("xp", 100),
            "level": user.get("level", 1),
            "badges": user.get("badges", []),
            "trustScore": user.get("trustScore", 80.0),
            "issuesReported": user.get("issuesReported", 0),
            "issuesVerified": user.get("issuesVerified", 0),
            "dailyStreak": user.get("dailyStreak", 0)
        }
    }

@router.get("/issue/{id}/detail")
async def get_issue_detail_legacy(id: str, request: Request):
    issue = db.get_document("issues", id)
    if not issue:
        issue = db.get_document("issues", f"ISS-{id}")
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    city = request.session.get('city', 'bengaluru')
    return {"issue": map_civio_to_civio_issue(issue, city)}

@router.post("/gov/update-status/{id}")
async def gov_update_status_legacy(
    id: str,
    status: str = Form(...)
):
    issue = db.get_document("issues", id)
    if not issue:
        issue = db.get_document("issues", f"ISS-{id}")
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
        
    db.update_document("issues", issue["id"], {"status": status.upper()})
    return RedirectResponse(url="/gov", status_code=303)

@router.post("/issue/{id}/toggle-action")
async def toggle_action_legacy(id: str):
    issue = db.get_document("issues", id)
    if not issue:
        issue = db.get_document("issues", f"ISS-{id}")
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
        
    current = issue.get("status", "REPORTED")
    new_status = "RESOLVED" if current != "RESOLVED" else "REPORTED"
    db.update_document("issues", issue["id"], {"status": new_status})
    return {"success": True, "status": new_status}
