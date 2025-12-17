from clinic.models import Invoice, Patient, AuditLog
from flask import request
from clinic.extensions import db

def generate_invoice_number(user_id):
    last_invoice = (
        Invoice.query
        .join(Patient)
        .filter(Patient.user_id == user_id)
        .order_by(Invoice.id.desc())
        .first()
    )

    if not last_invoice:
        return "INV-0001"

    last_no = int(last_invoice.invoice_number.split("-")[1])
    return f"INV-{last_no + 1:04}"




def log_action(action, user_id=None):
    try:
        log = AuditLog(
            user_id=user_id,
            action=action,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:250]
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()
        # Never break auth flow
