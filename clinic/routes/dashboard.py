from flask import Blueprint, render_template, session, redirect, url_for
from clinic.models import User, Patient, Appointment, Invoice
from datetime import datetime, timedelta
from sqlalchemy import func
from clinic.extensions import db


dashboard_bp = Blueprint("dashboard_bp", __name__)


@dashboard_bp.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect(url_for("auth_bp.login"))

    total_patients = Patient.query.count()

    today = datetime.now().strftime("%Y-%m-%d")
    today_appointments = Appointment.query.filter_by(date=today).count()

    unpaid = (
        Invoice.query.filter(Invoice.status != "Paid")
        .with_entities(func.count(Invoice.id))
        .first()
    )
    pending_bills = unpaid[0] if unpaid else 0

    total_invoices = Invoice.query.count()

    recent_patients = (
        Patient.query
        .order_by(Patient.id.desc())
        .limit(3)
        .all()
    )

    # 📊 PATIENTS PER DAY (LAST 7 DAYS)
    start_date = datetime.now() - timedelta(days=6)

    patient_stats = (
        db.session.query(
            func.date(Patient.created_at),
            func.count(Patient.id)
        )
        .filter(Patient.created_at >= start_date)
        .group_by(func.date(Patient.created_at))
        .order_by(func.date(Patient.created_at))
        .all()
    )

    chart_labels = []
    chart_data = []

    for date_str, count in patient_stats:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
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
        chart_data=chart_data
    )
