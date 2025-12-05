from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from ..extensions import db
from ..models import Patient, Invoice, Visit, Appointment
from datetime import datetime
import os
from werkzeug.utils import secure_filename


patients_bp = Blueprint("patients_bp", __name__)


@patients_bp.route("/patients")
def patients():
    if "user" not in session:
        return redirect(url_for("auth_bp.login"))

    all_patients = Patient.query.order_by(Patient.id.desc()).all()

    return render_template("patients.html", patients=all_patients)





@patients_bp.route("/add_patient", methods=["GET", "POST"])
def add_patient():
    if "user" not in session:
        return redirect(url_for("auth_bp.login"))

    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        age = request.form["age"]
        gender = request.form["gender"]
        disease = request.form["disease"]

        new_patient = Patient(
            name=name,
            phone=phone,
            gender=gender,
            age=age,
            disease=disease,
            last_visit=""
        )

        db.session.add(new_patient)
        db.session.commit()

        flash("Patient added successfully!")
        return redirect(url_for("patients_bp.patients"))

    return render_template("add_patient.html")



@patients_bp.route("/delete_patient/<int:id>")
def delete_patient(id):
    patient = Patient.query.get_or_404(id)
    db.session.delete(patient)
    db.session.commit()
    flash("Patient deleted!")
    return redirect(url_for("patients_bp.patients"))


@patients_bp.route("/edit_patient/<int:id>", methods=["GET", "POST"])
def edit_patient(id):
    patient = Patient.query.get_or_404(id)

    if request.method == "POST":
        patient.name = request.form["name"]
        patient.disease = request.form["disease"]
        patient.last_visit = request.form["last_visit"]
        patient.status = request.form["status"]

        db.session.commit()
        flash("Patient updated successfully!")
        return redirect(url_for("patients_bp.patients"))

    return render_template("edit_patient.html", patient=patient)


@patients_bp.route("/patient/<int:id>")
def patient_profile(id):
    if "user" not in session:
        return redirect(url_for("auth_bp.login"))

    patient = Patient.query.get_or_404(id)

    # FIX: fetch appointments via patient_id
    apps = Appointment.query.filter_by(patient_id=patient.id).all()

    return render_template(
        "patient_profile.html",
        patient=patient,
        apps=apps
    )


@patients_bp.route("/upload_record/<int:id>", methods=["GET", "POST"])
def upload_record(id):
    patient = Patient.query.get_or_404(id)

    if request.method == "POST":
        file = request.files["record"]

        if file:
            filename = file.filename
            filepath = os.path.join("clinic/static/records", filename)
            file.save(filepath)

            flash("Record uploaded successfully!")
            return redirect(url_for("patients_bp.patient_profile", id=id))

    return render_template("upload_record.html", patient=patient)

@patients_bp.route("/generate_certificate/<int:id>")
def generate_certificate(id):
    patient = Patient.query.get_or_404(id)
    return f"Certificate generation is coming soon for: {patient.name}"
