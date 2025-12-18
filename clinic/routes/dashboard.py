from flask import Blueprint, render_template, session, redirect, url_for
from clinic.models import User, Patient, Appointment, Invoice
from datetime import datetime, timedelta
from sqlalchemy import func
from clinic.extensions import db
from clinic.routes.auth import login_required, role_required
from clinic.utils import ROLE_LABELS, get_current_clinic_owner_id


dashboard_bp = Blueprint("dashboard_bp", __name__)

@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    

    clinic_owner_id = get_current_clinic_owner_id()
    # ✅ TOTAL PATIENTS (USER-SPECIFIC)
    total_patients = (
    Patient.query
    .filter_by(clinic_owner_id=clinic_owner_id)
    .count()
)
    # ✅ TODAY'S APPOINTMENTS (USER-SPECIFIC)
    today = datetime.now().date()
    today_appointments = (
        Appointment.query
        .join(Patient)
        .filter(
            Patient.clinic_owner_id == clinic_owner_id,            Appointment.date == today
        )
        .count()
    )

    # ✅ PENDING BILLS (USER-SPECIFIC)
    pending_bills = (
        Invoice.query
        .join(Patient)
        .filter(
            Patient.clinic_owner_id == clinic_owner_id,            Invoice.status != "Paid"
        )
        .count()
    )

    # ✅ TOTAL INVOICES (USER-SPECIFIC)
    total_invoices = (
        Invoice.query
        .join(Patient)
        .filter(Patient.clinic_owner_id == clinic_owner_id)
        .count()
    )

    # ✅ RECENT PATIENTS (USER-SPECIFIC)
    recent_patients = (
        Patient.query
        .filter_by(clinic_owner_id=clinic_owner_id)
        .order_by(Patient.id.desc())
        .limit(3)
        .all()
    )

    # 📊 PATIENTS PER DAY (LAST 7 DAYS, USER-SPECIFIC)
    start_date = datetime.now() - timedelta(days=6)

    patient_stats = (
        db.session.query(
            func.date(Patient.created_at),
            func.count(Patient.id)
        )
        .filter(
            Patient.clinic_owner_id == clinic_owner_id,            Patient.created_at >= start_date
        )
        .group_by(func.date(Patient.created_at))
        .order_by(func.date(Patient.created_at))
        .all()
    )

    chart_labels = []
    chart_data = []

    for date_val, count in patient_stats:
        # date_val may already be date object depending on DB
        date_obj = date_val if not isinstance(date_val, str) else datetime.strptime(date_val, "%Y-%m-%d")
        chart_labels.append(date_obj.strftime("%d %b"))
        chart_data.append(count)

    return render_template(
        "dashboard/dashboard.html",
        total_patients=total_patients,
        today_appointments=today_appointments,
        pending_bills=pending_bills,
        total_invoices=total_invoices,
        recent_patients=recent_patients,
        chart_labels=chart_labels,
        chart_data=chart_data,
        ROLE_LABELS=ROLE_LABELS
    )
