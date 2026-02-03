from datetime import date, datetime, time
from flask import request, session, abort, redirect, url_for, flash
from clinic.extensions import db
from clinic.models import (
    User,
    Patient,
    Invoice,
    AuditLog,
    InvoiceSequence
)
from clinic.subscription_plans import PLANS

# ---------------------------
#  Check clinic Is Active
# ----------------------------
def is_clinic_active(clinic):
    if clinic.subscription_status == "active":
        return True
    
    # trial ka end date exist karta ho,  aur aaj ki date se aage ho
    if clinic.subscription_status == "trial":
        if clinic.trial_ends_at and clinic.trial_ends_at >= datetime.utcnow():
            return True

    return False

# -----------------------------
# ROLE LABELS (UI USE)
# -----------------------------
# Ye function pure app ka gatekeeper hai.
# App ke before_request me use hota hai.

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
    
    # 🧠 Rule:
    # Clinic ID = tenant boundary
    # Iske bina koi data access nahi hona chahiye

    # (Session = logged in user ka bag)
    clinic_id = session.get("clinic_id")  #Session me se clinic_id nikal rahe ho
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

    clinic_id = get_current_clinic_id()   # Invoice clinic-wise unique hona chahiye

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
        db.session.flush()  # flush() → ID mil jaye bina commit ke

    seq.last_number += 1
    return f"INV-{seq.last_number:04d}"  # eg:- INV-0001

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
            clinic_id=session.get("clinic_id"),  # Kis clinic ne kiya
            user_id=user_id or session.get("user_id"),   # Kis user ne kiya
            action=action,
            ip_address=request.remote_addr if request else None,    # IP address
            user_agent=request.headers.get("User-Agent", "")[:250]  # Browser info
            if request else None
        )

        db.session.add(log)
        db.session.commit()
        # Log save ho gaya

    except Exception:
        db.session.rollback()  # silently ignore if fail without disturb anny  feature

# ----------------------------
# Daily patient limit check
# ----------------------------
def can_add_patient(clinic):
    plan = PLANS.get(clinic.plan, {})
    limit = plan.get("patients_per_day")

    if limit is None:
        return True

    # Aaj ke din ka full range ( 00:00:00 → 23:59:59 )
    today_start = datetime.combine(date.today(), time.min)
    today_end = datetime.combine(date.today(), time.max)

    # Aaj kitne patient add hue?
    today_count = Patient.query.filter(
        Patient.clinic_id == clinic.id,
        Patient.created_at.between(today_start, today_end)
    ).count()

    return today_count < limit

# ---------------------------
# Staff limit check
# ---------------------------
def can_add_staff(clinic):
    plan = PLANS.get(clinic.plan, {})
    limit = plan.get("staff_limit")

    # Unlimited staff
    if limit is None:
        return True

    # Doctor ko count nahi karte (Sirf staff)
    staff_count = User.query.filter_by(
        clinic_id=clinic.id
    ).filter(User.role != "doctor").count()

    return staff_count < limit
