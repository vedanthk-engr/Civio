from datetime import datetime, timedelta

from backend.services.gemini_service import analyze_image_triage
from backend.services.maps_service import reverse_geocode

async def run_triage_agent(image_data: str, lat: float, lng: float, user_description: str = "") -> dict:
    """
    Triage a reported issue by combining location geocoding and Gemini Vision analysis.
    """
    # 1. Geocode location coordinates to retrieve address and ward details
    location_details = await reverse_geocode(lat, lng)
    location_info = {
        "lat": lat,
        "lng": lng,
        "address": location_details["address"],
        "ward": location_details["ward"],
        "zone": location_details["zone"]
    }
    
    # 2. Invoke Gemini Vision Triage
    triage_result = await analyze_image_triage(image_data, location_info, user_description)
    
    # 3. Calculate SLA deadlines based on Severity and Risk
    reported_at = datetime.utcnow()
    severity = triage_result.get("severityScore", 5)
    safety_risk = triage_result.get("safetyRisk", "MEDIUM")
    
    if safety_risk == "CRITICAL" or severity >= 9:
        sla_hours = 24
    elif safety_risk == "HIGH" or severity >= 7:
        sla_hours = 72
    elif safety_risk == "MEDIUM" or severity >= 4:
        sla_hours = 168  # 7 days
    else:
        sla_hours = 336  # 14 days
        
    sla_deadline = reported_at + timedelta(hours=sla_hours)
    
    # Format response compatible with Issue Pydantic Schema
    return {
        "title": triage_result.get("title", f"Civic Issue: {triage_result.get('category')}"),
        "category": triage_result.get("category", "OTHER"),
        "subcategory": triage_result.get("subcategory", "General issue"),
        "location": location_info,
        "aiAnalysis": {
            "severityScore": severity,
            "confidenceScore": triage_result.get("confidenceScore", 0.8),
            "estimatedRepairCost": triage_result.get("estimatedRepairCost", 5000),
            "estimatedRepairTime": triage_result.get("estimatedRepairTime", "2 hours"),
            "safetyRisk": safety_risk,
            "structuralDamage": triage_result.get("structuralDamage", False),
            "geminiDescription": triage_result.get("geminiDescription", "Triage completed by Gemini Vision."),
            "urgencyJustification": triage_result.get("urgencyJustification", "Issue processed via automated AI scanner."),
            "affectedArea": triage_result.get("affectedArea", "Local area"),
            "requiredExpertise": triage_result.get("requiredExpertise", "Standard crew")
        },
        "reportedAt": reported_at.isoformat() + "Z",
        "slaDeadline": sla_deadline.isoformat() + "Z",
        "status": "REPORTED"
    }
