import os
import json
import base64
import httpx
from typing import List, Any, Optional
import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse

# Configure Gemini if API key is present
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
model_name = "gemini-2.0-flash"
gemini_configured = False

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_configured = True
        print("Civio AI: Initialized Gemini SDK successfully.")
    except Exception as e:
        print(f"Civio AI: Failed to configure Gemini SDK: {e}. Running with mock fallbacks.")
else:
    print("Civio AI: No GEMINI_API_KEY found. Running with mock fallbacks.")

# 1. Triage Agent Function
async def analyze_image_triage(image_data_url_or_base64: str, location: dict, user_description: str = "") -> dict:
    """
    Triage an issue from an image and optional description using Gemini 2.0 Flash.
    """
    prompt = f"""
    You are a civic infrastructure assessment AI. Analyze this image of a reported community issue.
    Location Context: {json.dumps(location)}
    User Description: "{user_description}"
    
    Return a JSON object with exactly these fields:
    {{
      "category": one of ["POTHOLE", "WATER_LEAK", "STREETLIGHT", "WASTE", "ROAD_DAMAGE", "ENCROACHMENT", "SEWAGE", "OTHER"],
      "subcategory": string (specific type, e.g. "deep pothole with water pooling"),
      "title": string (concise issue title, max 60 chars),
      "severityScore": integer 1-10 (1=cosmetic, 10=immediate danger),
      "safetyRisk": one of ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
      "structuralDamage": boolean,
      "estimatedRepairCost": integer (INR, realistic estimate),
      "estimatedRepairTime": string (e.g. "2-3 hours", "1-2 days"),
      "geminiDescription": string (2-3 sentence technical assessment for work order),
      "urgencyJustification": string (why this severity score),
      "affectedArea": string (e.g. "~4m x 3m road section"),
      "requiredExpertise": string (e.g. "civil works crew + 1 supervisor"),
      "confidenceScore": float 0-1
    }}
    
    Return ONLY valid JSON, no markdown codeblocks or extra text.
    """
    
    if gemini_configured:
        try:
            # Handle base64 image or url
            img_data = None
            mime_type = "image/jpeg"
            
            if image_data_url_or_base64.startswith("data:image/"):
                header, encoded = image_data_url_or_base64.split(",", 1)
                img_data = base64.b64decode(encoded)
                mime_type = header.split(";")[0].split(":")[1]
            elif image_data_url_or_base64.startswith("http"):
                # Download image
                async with httpx.AsyncClient() as client:
                    resp = await client.get(image_data_url_or_base64)
                    img_data = resp.content
                    mime_type = resp.headers.get("content-type", "image/jpeg")
            else:
                img_data = base64.b64decode(image_data_url_or_base64)
                
            model = genai.GenerativeModel(model_name)
            response = model.generate_content([
                prompt,
                {"mime_type": mime_type, "data": img_data}
            ])
            
            # Clean up markdown styling if the model wrapped it
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            return json.loads(text)
        except Exception as e:
            print(f"Gemini Triage failed: {e}. Falling back to mock response.")
            
    # Mock Fallback
    category = "POTHOLE"
    subcat = "medium depth circular pothole"
    title = "Road Pothole on Ward St"
    cost = 4500
    time_est = "2-3 hours"
    
    desc_lower = user_description.lower()
    if "leak" in desc_lower or "water" in desc_lower:
        category = "WATER_LEAK"
        subcat = "municipal pipe leakage"
        title = "Water Leakage on Street"
        cost = 8000
        time_est = "3-4 hours"
    elif "light" in desc_lower or "dark" in desc_lower:
        category = "STREETLIGHT"
        subcat = "burnt out sodium streetlight bulb"
        title = "Broken Streetlight"
        cost = 1500
        time_est = "1 hour"
    elif "waste" in desc_lower or "garbage" in desc_lower or "trash" in desc_lower:
        category = "WASTE"
        subcat = "overflowing public dumpster"
        title = "Unattended Garbage Pile"
        cost = 2000
        time_est = "1-2 hours"
    elif "encroach" in desc_lower:
        category = "ENCROACHMENT"
        subcat = "illegal footpath extension"
        title = "Footpath Encroachment"
        cost = 10000
        time_est = "1 day"
    elif "sewage" in desc_lower or "drain" in desc_lower:
        category = "SEWAGE"
        subcat = "blocked main sewage pipe"
        title = "Sewage Overflow"
        cost = 15000
        time_est = "5-6 hours"
        
    return {
        "category": category,
        "subcategory": subcat,
        "title": title,
        "severityScore": 6 if "urgent" in desc_lower or "dangerous" in desc_lower else 4,
        "safetyRisk": "HIGH" if "dangerous" in desc_lower else "MEDIUM",
        "structuralDamage": "damage" in desc_lower,
        "estimatedRepairCost": cost,
        "estimatedRepairTime": time_est,
        "geminiDescription": f"AI Triage detected a {subcat} near {location.get('address', 'specified location')}.",
        "urgencyJustification": "Reported issue poses general inconvenience and potential road hazard.",
        "affectedArea": "~2m x 2m area",
        "requiredExpertise": "Standard municipal response team",
        "confidenceScore": 0.89
    }

# 2. Duplicate Detection
async def detect_duplicate(new_location: dict, new_category: str, new_desc: str, existing_issues: List[dict]) -> Optional[str]:
    """
    Check if a report is a duplicate of a nearby issue.
    """
    from math import radians, cos, sin, asin, sqrt
    
    def haversine(lon1, lat1, lon2, lat2):
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371000 # Radius of earth in meters
        return c * r

    # Quick distance filter (within 50 meters, same category)
    duplicates = []
    for issue in existing_issues:
        if issue.get("status") in ["DUPLICATE", "RESOLVED", "CLOSED"]:
            continue
        if issue.get("category") != new_category:
            continue
        
        dist = haversine(
            new_location["lng"], new_location["lat"],
            issue["location"]["lng"], issue["location"]["lat"]
        )
        if dist <= 50:
            duplicates.append(issue)
            
    if not duplicates:
        return None
        
    if gemini_configured:
        try:
            # Let Gemini compare details
            comp_prompt = f"""
            Compare this newly reported issue:
            Category: {new_category}
            Description: {new_desc}
            
            With these nearby existing issues:
            {json.dumps([{'id': x['id'], 'title': x['title'], 'description': x['description']} for x in duplicates])}
            
            Determine if the new issue is a duplicate of one of the existing ones.
            Return a JSON object with:
            {{ "isDuplicate": boolean, "duplicateOfId": string or null }}
            """
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(comp_prompt)
            
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            res = json.loads(text.strip())
            if res.get("isDuplicate"):
                return res.get("duplicateOfId")
        except Exception:
            pass
            
    # Fallback to closest matching
    return duplicates[0]["id"] if duplicates else None

# 3. Work Order Drafting
async def draft_work_order(issue: dict) -> dict:
    """
    Generate detailed technical work order for municipal workers.
    """
    prompt = f"""
    You are a municipal engineering director. Draft a highly technical work order for this issue:
    Category: {issue.get('category')}
    Title: {issue.get('title')}
    Description: {issue.get('description')}
    Technical Assessment: {issue.get('aiAnalysis', {}).get('geminiDescription')}
    Severity Score: {issue.get('aiAnalysis', {}).get('severityScore')}
    
    Return a JSON object with exactly these fields:
    {{
      "title": string (professional work order title),
      "description": string (step-by-step repair instruction log, safety guidelines, exact specifications),
      "requiredMaterials": array of strings (e.g. ["cold asphalt mix", "bitumen emulsion", "shovels", "compactor"]),
      "estimatedCost": number (in INR),
      "estimatedDuration": string (e.g. "2 hours", "1 day"),
      "requiredSkills": array of strings (e.g. ["asphalt paving", "safety coordination"]),
      "safetyNotes": string (hazard warnings, required PPE, traffic management notes),
      "priority": one of ["P1", "P2", "P3", "P4"] (based on severity: 9-10 -> P1, 7-8 -> P2, 5-6 -> P3, 1-4 -> P4)
    }}
    
    Return ONLY valid JSON.
    """
    
    if gemini_configured:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())
        except Exception as e:
            print(f"Gemini WorkOrder failed: {e}")
            
    # Mock Fallback
    cat = issue.get("category", "OTHER")
    priority = "P3"
    sev = issue.get("aiAnalysis", {}).get("severityScore", 5)
    if sev >= 9: priority = "P1"
    elif sev >= 7: priority = "P2"
    elif sev <= 3: priority = "P4"
    
    materials = ["Standard Maintenance Kit"]
    skills = ["General Labor"]
    notes = "Wear high-visibility vests. Maintain pedestrian safety."
    
    if cat == "POTHOLE":
        materials = ["Bituminous cold mix (2 bags)", "Tack coat emulsion (10L)", "Compactor", "Asphalt rake"]
        skills = ["Asphalt Repair", "Compactor Operation"]
        notes = "Cordon off the lane with cones. Wear steel-toed boots. Keep fire extinguisher handy."
    elif cat == "WATER_LEAK":
        materials = ["PVC Repair Sleeve", "Sump Pump", "Trench Shoring Clamps", "Joint Sealant"]
        skills = ["Plumbing", "Hydraulic Systems"]
        notes = "Shut off upstream valve before starting. Check for muddy trench hazards."
    elif cat == "STREETLIGHT":
        materials = ["150W LED bulb replacement", "Fuse block", "Wiring clamps"]
        skills = ["Electrical Works", "High-altitude climbing"]
        notes = "Ensure power source is isolated. Use insulated safety gloves (Class 0)."
        
    return {
        "title": f"Repair Work Order: {issue.get('title')}",
        "description": f"Perform site inspection. Safely cordon off the affected area. Excavate/clean the surrounding surface. Apply {', '.join(materials[:2])}. Compact and seal the joint. Verify structural durability and log resolution details.",
        "requiredMaterials": materials,
        "estimatedCost": issue.get("aiAnalysis", {}).get("estimatedRepairCost", 5000),
        "estimatedDuration": issue.get("aiAnalysis", {}).get("estimatedRepairTime", "2 hours"),
        "requiredSkills": skills,
        "safetyNotes": notes,
        "priority": priority
    }

# 4. Budget Impact Simulation Explanation
async def explain_budget_simulation(impact_data: dict) -> str:
    """
    Gemini explanation for the budget impact slider dashboard.
    """
    prompt = f"""
    You are a municipal chief financial officer. Explain this simulated budget scenario to the ward committee:
    Time Horizon: {impact_data.get('horizon')} months
    Ward: {impact_data.get('ward')}
    Immediate Repair Cost: ₹{impact_data.get('immediate_cost')} Cr
    Deferred Damage Cost (if delayed): ₹{impact_data.get('deferred_cost')} Cr
    Net Loss due to inaction: ₹{impact_data.get('loss')} Cr
    Count of issues simulated: {impact_data.get('issue_count')}
    
    Provide a concise (3-4 sentences), highly professional narrative explaining why early action saves taxpayer money. Emphasize preventative maintenance vs catastrophic repair.
    """
    if gemini_configured:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception:
            pass
            
    return f"Delaying repairs on {impact_data.get('issue_count')} infrastructure elements in {impact_data.get('ward')} over a {impact_data.get('horizon')}-month horizon will result in rapid asset degradation. The cost of deferred repairs increases from ₹{impact_data.get('immediate_cost')} Cr to ₹{impact_data.get('deferred_cost')} Cr due to structural water seepage and asphalt cracking. Taking immediate action will save the ward ₹{impact_data.get('loss')} Cr in catastrophic repair expenditures, optimizing overall tax utilization."

# 5. Civic Pulse Report Digest
async def generate_civic_pulse_report(ward: str, issues_summary: dict) -> str:
    """
    Weekly AI generated civic digest for authority briefing.
    """
    prompt = f"""
    You are the Senior Executive Officer for Ward {ward}. Write a weekly civic briefing digest.
    Stats:
    Total Active Issues: {issues_summary.get('active')}
    Resolved this week: {issues_summary.get('resolved')}
    Critical severity: {issues_summary.get('critical')}
    SLA Breaches: {issues_summary.get('breached')}
    
    Provide a professional, 3-paragraph summary highlighting current operations, hotspots, and strategic recommendations for the commissioner. Include HTML tags like <p>, <ul>, <li> for structured formatting.
    """
    if gemini_configured:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception:
            pass
            
    return f"""
    <p><strong>Ward {ward} Operations Briefing:</strong> Civic monitoring has detected {issues_summary.get('active')} active infrastructure failures, with a high concentration of water leakages and potholes. Our response teams successfully resolved {issues_summary.get('resolved')} issues this past week, stabilizing public complaint frequencies.</p>
    <p><strong>Hotspots & Alerts:</strong> We currently track {issues_summary.get('critical')} critical severity alerts. Furthermore, {issues_summary.get('breached')} SLA deadlines were breached due to asphalt contractor backlog, which has been escalated to senior engineering staff.</p>
    <p><strong>Strategic Recommendations:</strong> To avoid further SLA delays, we recommend redeploying standard civil crews from low-priority zones to high-risk road corridors, and enforcing penalties on contractors failing to meet the 48-hour paving timeline.</p>
    """

# 6. Multilingual Translation
async def translate_text(text: str, target_lang: str) -> str:
    """
    Translates description or UI text into regional languages.
    """
    # Languages: Hindi ("hi"), Tamil ("ta"), Telugu ("te"), Bengali ("bn")
    lang_names = {"hi": "Hindi", "ta": "Tamil", "te": "Telugu", "bn": "Bengali"}
    target = lang_names.get(target_lang, "Hindi")
    
    prompt = f"Translate the following text into {target}. Return ONLY the translated string, no notes:\n\n{text}"
    if gemini_configured:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception:
            pass
            
    # Mock translations
    mocks = {
        "hi": "नागरिक समस्या रिपोर्ट: ",
        "ta": "குடிமகன் பிரச்சனை அறிக்கை: ",
        "te": "పౌర సమస్య నివేదిక: ",
        "bn": "নাগরিক সমস্যা রিপোর্ট: "
    }
    prefix = mocks.get(target_lang, "")
    return f"{prefix}{text} [Translated to {target}]"

# 7. Draft Complaint Letter
async def draft_complaint_letter(issue: dict, citizen_name: str = "Concerned Citizen") -> dict:
    """
    Generates a formal, bureaucratic complaint letter suitable for Indian authorities.
    """
    category = issue.get("category", "OTHER")
    description = issue.get("description", "")
    reported_at = issue.get("reportedAt", "2026-06-26T12:00:00Z")
    location = issue.get("location", {})
    address = location.get("address", "Civic Location")
    ward = location.get("ward", "Local Ward")
    
    prompt = f"""
    You are a professional scribe drafting a formal civic complaint letter to the Municipal Commissioner.
    
    Issue Details:
    - ID: {issue.get('id', 'N/A')}
    - Category: {category}
    - Reported At: {reported_at}
    - Location: {address} (Ward: {ward})
    - Description: {description}
    - Severity: {issue.get('aiAnalysis', {}).get('severityScore', 5)}/10
    
    Drafter Name: {citizen_name}
    
    Write a highly formal, respectful, and structured letter to the Municipal Commissioner of Bengaluru.
    Start with "Subject: Formal Complaint Regarding [Issue Category] at [Location]"
    Follow with:
    1. Salutation (e.g. "Respected Sir/Madam,")
    2. Paragraph describing the issue and the safety/health hazards it poses.
    3. Paragraph asking for immediate action under standard municipal SLAs.
    4. Closure (e.g. "Yours sincerely, [Drafter Name]")
    
    Return the letter text. Do NOT add markdown codeblocks, notes, or explanations.
    """
    
    if gemini_configured:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            body = response.text.strip()
            subject = f"Complaint: {category} at {ward}"
            if body.startswith("Subject:"):
                subject = body.split("\n", 1)[0].replace("Subject:", "").strip()
            return {
                "subject": subject,
                "body": body
            }
        except Exception as e:
            print(f"Failed to draft complaint with Gemini: {e}")
            
    # Mock fallback
    return {
        "subject": f"Complaint: {category} at {ward}",
        "body": f"""Subject: Formal Complaint Regarding {category} at {address}

Respected Sir/Madam,

I am writing to draw your attention to a critical {category.lower()} issue reported at {address} (Ward: {ward}). This issue has been logged in the Civio platform with Reference ID {issue.get('id', 'N/A')}.

The description of the issue is as follows: {description}. This poses a direct hazard to local residents and commuters in the area.

I request your office to inspect the site and initiate repairs immediately as per municipal guidelines.

Yours sincerely,
{citizen_name}"""
    }
