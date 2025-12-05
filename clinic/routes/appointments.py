from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from ..extensions import db
from ..models import Appointment,Patient
from datetime import datetime

appointments_bp = Blueprint("appointments_bp", __name__)


@appointments_bp.route("/appointments")
def appointments():
    if "user" not in session:
        return redirect(url_for("auth_bp.login"))

    tab = request.args.get("tab", "queue")  # default tab = queue

    today = datetime.now().strftime("%Y-%m-%d")

    # Load appointments by tab
    if tab == "queue":
        apps = Appointment.query.filter_by(status="Queue").all()
    elif tab == "finished":
        apps = Appointment.query.filter_by(status="Finished").all()
    elif tab == "cancelled":
        apps = Appointment.query.filter_by(status="Cancelled").all()
    else:
        apps = Appointment.query.all()

    # Counts for tabs
    queue_count = Appointment.query.filter_by(status="Queue").count()
    finished_count = Appointment.query.filter_by(status="Finished").count()
    cancelled_count = Appointment.query.filter_by(status="Cancelled").count()

    return render_template(
        "appointments.html",
        apps=apps,
        tab=tab,
        queue_count=queue_count,
        finished_count=finished_count,
        cancelled_count=cancelled_count,
        date_selected=today,
    )




@appointments_bp.route("/add_appointment", methods=["GET", "POST"])
def add_appointment():

    if "user" not in session:
        return redirect(url_for("auth_bp.login"))

    patients = Patient.query.all()

    if request.method == "POST":
        patient_id = request.form["patient_id"]
        visit_type = request.form["type"]
        time = request.form["time"]
        date = request.form["date"]

        patient = Patient.query.get(patient_id)

        ap = Appointment(
            patient_id=patient.id,
            type=visit_type,
            time=time,
            date=date,
            status="Queue"
        )

        patient.last_visit = date

        db.session.add(ap)
        db.session.commit()

        flash("Appointment booked successfully!")
        return redirect(url_for("appointments_bp.appointments"))

    return render_template("add_appointment.html", patients=patients)


@appointments_bp.route("/delete_appointment/<int:id>")
def delete_appointment(id):
    app_item = Appointment.query.get_or_404(id)
    db.session.delete(app_item)
    db.session.commit()
    flash("Appointment deleted!")
    return redirect(url_for("appointments_bp.appointments"))


@appointments_bp.route("/edit_appointment/<int:id>", methods=["GET", "POST"])
def edit_appointment(id):
    app_item = Appointment.query.get_or_404(id)

    if request.method == "POST":
        app_item.patient_name = request.form["patient_name"]
        app_item.doctor = request.form["doctor"]
        app_item.date = request.form["date"]
        app_item.time = request.form["time"]
        app_item.status = request.form["status"]

        db.session.commit()
        flash("Appointment updated!")
        return redirect(url_for("appointments_bp.appointments"))

    return render_template("edit_appointment.html", app=app_item)
