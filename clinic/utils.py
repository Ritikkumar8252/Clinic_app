from flask import request, session
from clinic.extensions import db
from clinic.models import Invoice, Patient, AuditLog, User


ROLE_LABELS = {
    "doctor": "Doctor",
    "reception": "Receptionist"
}


def get_clinic_owner_id():
    """
    Resolve clinic owner (doctor) ID.
    """
    user_id = session.get("user_id")
    role = session.get("role")

    if not user_id:
        return None

    user = User.query.get(user_id)
    if not user:
        return None

    if role in ("doctor"):
        return user.id

    if role == "reception":
        return user.created_by

    return None


def generate_invoice_number():
    clinic_owner_id = get_clinic_owner_id()

    last_invoice = (
        Invoice.query
        .join(Patient)
        .filter(Patient.user_id == clinic_owner_id)
        .order_by(Invoice.id.desc())
        .first()
    )

    if not last_invoice:
        return "INV-0001"

    try:
        last_no = int(last_invoice.invoice_number.split("-")[1])
    except Exception:
        last_no = 0

    return f"INV-{last_no + 1:04d}"


def log_action(action, user_id=None):
    try:
        log = AuditLog(
            user_id=user_id,
            action=action,
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get("User-Agent", "")[:250]
            if request else None
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()



