from fastapi import APIRouter, Response, HTTPException
import csv
import io
from backend.database import db

router = APIRouter(prefix="/admin", tags=["Admin Operations"])

@router.get("/export-spam-csv")
async def export_spam_csv():
    """
    GET /api/admin/export-spam-csv - download spam_issues as CSV for model retraining.
    CSV columns: text, label (label matches 'spam', 'abuse', 'test', etc.)
    """
    try:
        spam_docs = db.list_documents("spam_issues")
        
        verdict_to_label = {
            'spam':       'spam',
            'abuse':      'abuse',
            'test':       'test',
            'ban':        'spam',
            'reject':     'spam',
            'real':       'real'
        }
        
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(['text', 'label'])
        
        exported = 0
        for doc in spam_docs:
            verdict = doc.get("spam_verdict") or doc.get("verdict") or ""
            label = verdict_to_label.get(str(verdict).lower(), "spam")
            text = (doc.get("description") or "").strip()
            if text:
                writer.writerow([text, label])
                exported += 1
                
        buf.seek(0)
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=spam_export.csv",
                "X-Row-Count": str(exported),
                "Access-Control-Expose-Headers": "X-Row-Count"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export spam CSV: {e}")

@router.get("/export-real-csv")
async def export_real_csv():
    """
    GET /api/admin/export-real-csv - download approved (real) issues as CSV for model retraining.
    CSV columns: text, label (label = 'real')
    """
    try:
        issues_docs = db.list_documents("issues")
        
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(['text', 'label'])
        
        exported = 0
        for doc in issues_docs:
            text = (doc.get("description") or "").strip()
            # Only export real issues (non-duplicate)
            if text and doc.get("status") != "DUPLICATE":
                writer.writerow([text, "real"])
                exported += 1
                
        buf.seek(0)
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=real_export.csv",
                "X-Row-Count": str(exported),
                "Access-Control-Expose-Headers": "X-Row-Count"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export real CSV: {e}")
