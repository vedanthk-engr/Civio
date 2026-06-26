from fastapi import APIRouter, Request, Response, Form, HTTPException
from typing import Optional
import os
import time
import base64
import httpx
import json
import uuid
from datetime import datetime

from backend.database import db
from backend.agents.triage_agent import run_triage_agent
from backend.services.gemini_service import detect_duplicate
from backend.services.validation_service import (
    classify_spam,
    compute_image_hash,
    is_duplicate_image,
    check_cross_modal_consistency
)

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Webhook"])

# Global session store for WhatsApp reporting flow
_WA_SESSIONS = {}
_WA_TTL = 300  # 5 minutes session expiry

def _wa_prune():
    now = time.time()
    expired = [k for k, v in _WA_SESSIONS.items() if now - v.get('ts', 0) > _WA_TTL]
    for k in expired:
        del _WA_SESSIONS[k]

def twiml_response(*messages: str) -> Response:
    xml = '<?xml version="1.0" encoding="UTF-8"?><Response>'
    for m in messages:
        escaped = m.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        xml += f'<Message>{escaped}</Message>'
    xml += '</Response>'
    return Response(content=xml, media_type="application/xml")

async def _wa_download_image(url: str):
    sid = os.environ.get('TWILIO_ACCOUNT_SID', '').strip()
    token = os.environ.get('TWILIO_AUTH_TOKEN', '').strip()
    auth = (sid, token) if (sid and token) else None
    
    async with httpx.AsyncClient() as client:
        if auth:
            # Twilio CDN media files might require basic auth
            resp = await client.get(url, auth=auth, follow_redirects=True)
        else:
            resp = await client.get(url, follow_redirects=True)
            
    resp.raise_for_status()
    mime = resp.headers.get('content-type', 'image/jpeg').split(';')[0].strip()
    return resp.content, mime

def wa_notify(to_phone: str, message: str) -> dict:
    """
    Sends an outbound WhatsApp notification to a citizen via Twilio.
    """
    sid = os.environ.get('TWILIO_ACCOUNT_SID', '')
    token = os.environ.get('TWILIO_AUTH_TOKEN', '')
    from_num = os.environ.get('TWILIO_WHATSAPP_NUMBER', '')
    dry_run = os.environ.get('WA_NOTIFY_DRY_RUN', '0') == '1'

    if not to_phone:
        return {'ok': False, 'mode': 'skipped', 'detail': 'no_phone'}
        
    dest = to_phone.strip()
    if not dest.startswith('whatsapp:'):
        if not dest.startswith('+'):
            dest = '+91' + dest.lstrip('+')
        dest = 'whatsapp:' + dest

    if dry_run or not (sid and token and from_num):
        print(f'[wa_notify] (simulated) -> {dest}: {message}')
        return {'ok': True, 'mode': 'simulated', 'detail': 'Twilio not configured'}

    try:
        import urllib.parse
        url = f'https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json'
        from_full = from_num if from_num.startswith('whatsapp:') else f'whatsapp:{from_num}'
        
        # Use httpx synchronously or post directly
        auth_header = base64.b64encode(f'{sid}:{token}'.encode()).decode()
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'From': from_full,
            'To': dest,
            'Body': message
        }
        resp = httpx.post(url, data=data, headers=headers)
        return {'ok': resp.status_code == 201, 'mode': 'sent', 'detail': resp.text}
    except Exception as e:
        print(f'[wa_notify] Outbound send failed: {e}')
        return {'ok': False, 'mode': 'error', 'detail': str(e)}

@router.post("")
async def whatsapp_webhook(
    request: Request
):
    """
    Twilio Webhook endpoint handling incoming WhatsApp reporting requests.
    """
    _wa_prune()
    
    # Parse form data from Twilio
    form_data = await request.form()
    from_num = form_data.get('From', '')
    body = (form_data.get('Body') or '').strip()
    num_media = int(form_data.get('NumMedia', 0))
    media_url = form_data.get('MediaUrl0', '')
    lat_str = form_data.get('Latitude', '')
    lng_str = form_data.get('Longitude', '')
    phone = from_num.replace('whatsapp:', '')
    
    sess = _WA_SESSIONS.get(from_num, {})

    # 1. Location Pin Received
    if lat_str and lng_str:
        try:
            lat, lng = float(lat_str), float(lng_str)
            if sess.get('state') == 'AWAITING_CONFIRM':
                sess['pending'].update({'lat': lat, 'lng': lng})
                sess['ts'] = time.time()
                _WA_SESSIONS[from_num] = sess
                return twiml_response(
                    "📍 Location saved!\n\nReply *YES* to submit or *NO* to cancel."
                )
        except Exception as e:
            print(f"[whatsapp_webhook] Location parsing error: {e}")

    # 2. Photo Message Received
    if num_media > 0 and media_url:
        try:
            # Download photo
            img_bytes, mime = await _wa_download_image(media_url)
            img_b64 = base64.b64encode(img_bytes).decode()
            
            # Default mock location context for triage
            lat, lng = 12.9716, 77.5946  # Bangalore default
            
            # Run AI triage agent
            triage_data = await run_triage_agent(
                image_data=img_b64,
                lat=lat,
                lng=lng,
                user_description=body
            )
            
            # Extract details
            category = triage_data.get("category", "OTHER")
            severity = triage_data.get("aiAnalysis", {}).get("severityScore", 5)
            desc = triage_data.get("aiAnalysis", {}).get("geminiDescription", "Civic issue reported via WhatsApp.")
            
            # Store in session state
            _WA_SESSIONS[from_num] = {
                'state': 'AWAITING_CONFIRM',
                'ts': time.time(),
                'img_b64': img_b64,
                'pending': {
                    'user': phone,
                    'description': body or desc,
                    'tag': category,
                    'severity': severity,
                    'lat': lat,
                    'lng': lng,
                    'title': triage_data.get("title", f"WhatsApp {category.title()} Report"),
                    'aiAnalysis': triage_data.get("aiAnalysis", {})
                }
            }
            
            return twiml_response(
                f"⚠️ *{category.replace('_',' ').title()} Detected*\n\n"
                f"Severity: *{severity}/10*\n"
                f"Description: _{desc}_\n\n"
                f"Reply *YES* to submit report ✅\n"
                f"Reply *NO* to cancel report ❌\n"
                f"Or share your 📍 *location pin* for precise coordinates."
            )
        except Exception as e:
            print(f"[whatsapp_webhook] Image processing error: {e}")
            return twiml_response("❌ Trouble analyzing that image. Please try again.")

    # 3. Text Confirmation Command
    bl = body.lower()
    if bl in ('yes', 'y', 'confirm', 'ok', 'okay', '✅'):
        if sess.get('state') == 'AWAITING_CONFIRM':
            p = sess['pending']
            try:
                issue_id = f"ISS-{uuid.uuid4().hex[:6].upper()}"
                reported_at = datetime.utcnow().isoformat() + "Z"
                
                # Check for duplicates using image hash
                img_hash = compute_image_hash(sess['img_b64'])
                p["aiAnalysis"]["imageHash"] = img_hash or ""
                
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
                                
                if not dup_id:
                    # Fallback location duplicate check
                    dup_id = await detect_duplicate(
                        {"lat": p["lat"], "lng": p["lng"]},
                        p["tag"],
                        p["description"],
                        existing_issues
                    )
                
                sla_hours = 24 if p["severity"] >= 9 else 72 if p["severity"] >= 7 else 168 if p["severity"] >= 4 else 336
                sla_deadline = datetime.utcnow() + datetime.timedelta(hours=sla_hours)
                
                issue_doc = {
                    "id": issue_id,
                    "title": p["title"],
                    "description": p["description"],
                    "category": p["tag"],
                    "subcategory": p["title"],
                    "location": {
                        "lat": p["lat"],
                        "lng": p["lng"],
                        "address": "Reported via WhatsApp",
                        "ward": "Indiranagar",
                        "zone": "East Zone"
                    },
                    "mediaUrls": ["placeholder_wa_image"],
                    "thumbnailUrl": "placeholder_wa_image",
                    "aiAnalysis": p["aiAnalysis"],
                    "imageHash": img_hash or "",
                    "reportedBy": phone,
                    "verifiedBy": [],
                    "upvotes": 0,
                    "communityNotes": [],
                    "status": "DUPLICATE" if dup_id else "REPORTED",
                    "reportedAt": reported_at,
                    "slaDeadline": sla_deadline.isoformat() + "Z",
                    "slaBreached": False,
                    "reporterTrustScore": 50.0,
                    "validationScore": 50.0
                }
                if dup_id:
                    issue_doc["aiAnalysis"]["duplicateOfId"] = dup_id
                    
                db.save_document("issues", issue_id, issue_doc)
                del _WA_SESSIONS[from_num]
                
                return twiml_response(
                    f"✅ *Issue #{issue_id} Reported Successfully!*\n\n"
                    f"Category: *{p['tag'].title()}*\n"
                    f"Severity: *{p['severity']}/10*\n\n"
                    f"Thank you for helping make our city self-healing! 🇮🇳"
                )
            except Exception as e:
                print(f"[whatsapp_webhook] Create issue from WhatsApp failed: {e}")
                return twiml_response("❌ Error saving report. Please try again.")
        return twiml_response("Please send a *photo* first, then reply YES to confirm.")
        
    if bl in ('no', 'n', 'cancel', '❌'):
        if sess.get('state') == 'AWAITING_CONFIRM':
            del _WA_SESSIONS[from_num]
            return twiml_response("❌ Cancelled. Send a new photo anytime to report an issue.")
            
    # Default intro message
    return twiml_response(
        "👋 Welcome to *Civio* — Your self-healing city!\n\n"
        "To report a civic infrastructure issue:\n"
        "1. Send a *photo* of the issue.\n"
        "2. Our AI will automatically categorize it and request confirmation."
    )
