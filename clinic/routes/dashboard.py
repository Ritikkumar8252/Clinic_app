from flask import Blueprint, render_template, session, redirect, url_for
from clinic.models import User, Patient, Appointment, Invoice
from datetime import datetime
from sqlalchemy import func

dashboard_bp = Blueprint("dashboard_bp", __name__)


@dashboard_bp.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect(url_for("auth_bp.login"))

    current_user = User.query.filter_by(email=session["user"]).first()

    total_patients = Patient.query.count()
    today = datetime.now().strftime("%Y-%m-%d")

    today_appointments = Appointment.query.filter_by(date=today).count()

    unpaid = (
        Invoice.query.filter(Invoice.status != "Paid")
        .with_entities(func.count(Invoice.id), func.sum(Invoice.total_amount))
        .first()
    )
    pending_bills = unpaid[0]

    recent_patients = Patient.query.order_by(Patient.id.desc()).limit(3).all()
    total_invoices = Invoice.query.count()

    return render_template(
    "dashboard.html",
    total_patients=total_patients,
    today_appointments=today_appointments,
    pending_bills=pending_bills,
    total_invoices=total_invoices,
    recent_patients=recent_patients
)


