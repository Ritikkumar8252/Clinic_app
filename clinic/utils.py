from flask import request, session, abort
from clinic.extensions import db
from clinic.models import (
    User,
    Patient,
    Invoice,
    AuditLog,
    InvoiceSequence
)

# -----------------------------
# ROLE LABELS (UI USE)
# -----------------------------
ROLE_LABELS = {
    "doctor": "Doctor (Clinic Owner)",
    "reception": "Receptionist",
    "lab": "Lab Staff",
    "pharmacy": "Pharmacy Staff"
}

# -----------------------------
# CLINIC OWNER RESOLUTION
# -----------------------------
def get_current_clinic_id():
    """
    Resolve current clinic_id from session.
    HARD FAIL if missing.
    """

    clinic_id = session.get("clinic_id")
    if not clinic_id:
        abort(401, "Clinic not found in session")

    return clinic_id



# -----------------------------
# SAFE INVOICE NUMBER GENERATION
# -----------------------------
def generate_invoice_number():
    """
    Generate invoice number safely (NO race condition).
    Uses per-clinic sequence.
    """

    clinic_id = get_current_clinic_id()

    seq = (
        InvoiceSequence.query
        .filter_by(clinic_id=clinic_id)
        .with_for_update()
        .first()
    )

    if not seq:
        seq = InvoiceSequence(
            clinic_id=clinic_id,
            last_number=0
        )
        db.session.add(seq)
        db.session.flush()

    seq.last_number += 1
    return f"INV-{seq.last_number:04d}"



# -----------------------------
# AUDIT LOGGING (LEGAL SAFE)
# -----------------------------
def log_action(action, user_id=None):
    """
    Log security / business actions.
    Always include clinic context.
    """

    try:
        log = AuditLog(
            clinic_id=get_current_clinic_id(),
            user_id=user_id or session.get("user_id"),
            action=action,
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get("User-Agent", "")[:250]
            if request else None
        )

        db.session.add(log)
        db.session.commit()

    except Exception:
        db.session.rollback()
