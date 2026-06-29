import os
import json
import urllib.request
import urllib.error
from typing import List, Optional, Dict

RESEND_API_URL = 'https://api.resend.com/emails'

class EmailService:
    @staticmethod
    def is_available() -> bool:
        return bool(os.environ.get('RESEND_API_KEY'))

    @staticmethod
    def send_complaint(
        to_email: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        attachments: Optional[List[Dict[str, str]]] = None,
        reply_to: Optional[str] = None
    ) -> dict:
        api_key = os.environ.get('RESEND_API_KEY')
        if not api_key:
            print("[email_service] RESEND_API_KEY not configured. Simulating dispatch.")
            return {'error': 'RESEND_API_KEY not configured', '_status': 'not_configured'}

        sender = os.environ.get('RESEND_FROM', 'Civio <onboarding@resend.dev>')

        # resend free tier limits: enforce recipient override if DEMO_RECIPIENT_EMAIL is set
        demo_to = os.environ.get('DEMO_RECIPIENT_EMAIL', '').strip()
        if demo_to:
            original_to = to_email
            to_email = demo_to
            if not str(subject).startswith('[DEMO'):
                subject = f'[DEMO → {original_to}] {subject}'

        payload = {
            'from': sender,
            'to': [to_email] if isinstance(to_email, str) else to_email,
            'subject': subject,
            'html': body_html,
        }
        if body_text:
            payload['text'] = body_text
        if reply_to:
            payload['reply_to'] = reply_to
        if attachments:
            payload['attachments'] = [{
                'filename': a['filename'],
                'content': a['content_b64'],
                'content_type': a.get('content_type', 'image/jpeg'),
            } for a in attachments]

        print(f'[email_service] POST → from={sender} to={to_email} subject={subject[:60]!r}')

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            RESEND_API_URL, data=data, method='POST',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'User-Agent': 'Civio/1.0 (+https://civio.app)',
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read().decode('utf-8')
                result = json.loads(body) if body else {}
                print(f'[email_service] ✓ sent id={result.get("id", "?")}')
                return {'success': True, 'id': result.get('id', ''), 'raw': result}
        except urllib.error.HTTPError as e:
            err_body = ''
            try:
                err_body = e.read().decode('utf-8')
            except Exception as r_err:
                err_body = f'(could not read body: {r_err})'

            print(f'[email_service] ✗ HTTP {e.code}')
            print(f'[email_service] response body: {err_body}')

            msg = err_body
            try:
                err_json = json.loads(err_body)
                msg = err_json.get('message') or err_json.get('error') or err_json.get('name') or err_body
            except Exception:
                pass

            if e.code == 403:
                hint = ''
                ml = (msg or '').lower()
                if 'verify' in ml or 'domain' in ml or 'testing' in ml or 'own' in ml:
                    hint = (' · Resend free tier requires you to send FROM a verified email AND TO your '
                            'own Resend account email. Verify your domain at https://resend.com/domains or '
                            'set DEMO_RECIPIENT_EMAIL to your Resend signup email.')
                else:
                    hint = ' · Check RESEND_API_KEY is valid and RESEND_FROM is a verified sender.'
                msg = (msg or 'forbidden') + hint

            return {'error': f'{msg}', '_status': 'api_error', '_code': e.code, '_body': err_body[:500]}
        except Exception as e:
            print(f'[email_service] ✗ exception: {type(e).__name__}: {e}')
            return {'error': str(e), '_status': 'exception'}
