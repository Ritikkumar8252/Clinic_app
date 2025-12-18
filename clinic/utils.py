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
def get_current_clinic_owner_id():
    """
    Resolve clinic owner (doctor) ID.
    HARD FAILS on invalid state.
    """

    user_id = session.get("user_id")
    if not user_id:
        abort(401, "Login required")

    user = User.query.get(user_id)
    if not user:
        abort(401, "Invalid session")

    # Doctor = clinic owner
    if user.role == "doctor":
        return user.id

    # Staff roles
    if user.role in ("reception", "lab", "pharmacy"):
        if not user.created_by:
            abort(403, "Staff not linked to any clinic")
        return user.created_by

    abort(403, "Unauthorized role")


# -----------------------------
# SAFE INVOICE NUMBER GENERATION
# -----------------------------
def generate_invoice_number():
    """
    Generate invoice number safely (NO race condition).
    Uses per-clinic sequence.
    """

    clinic_owner_id = get_current_clinic_owner_id()

    # Lock sequence row (important for concurrency)
    seq = (
        InvoiceSequence.query
        .filter_by(clinic_owner_id=clinic_owner_id)
        .with_for_update()
        .first()
    )

    if not seq:
        seq = InvoiceSequence(
            clinic_owner_id=clinic_owner_id,
            last_number=0
        )
        db.session.add(seq)
        db.session.flush()  # ensure row exists before increment

    seq.last_number += 1
    invoice_no = f"INV-{seq.last_number:04d}"

    return invoice_no


# -----------------------------
# AUDIT LOGGING (LEGAL SAFE)
# -----------------------------
def log_action(action, clinic_owner_id=None, user_id=None):
    """
    Log security / business actions.
    Always include clinic context.
    """

    try:
        if not clinic_owner_id:
            # fallback (safe)
            clinic_owner_id = get_current_clinic_owner_id()

        log = AuditLog(
            clinic_owner_id=clinic_owner_id,
            user_id=user_id or session.get("user_id"),
            action=action,
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get("User-Agent", "")[:250]
            if request else None
        )

        db.session.add(log)
        db.session.commit()

    except Exception:
        # Logging must NEVER break main flow
        db.session.rollback()
