from flask import Blueprint, render_template, request, redirect, url_for, session, flash,current_app
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

    q = request.args.get("q", "")
    date_filter = request.args.get("date", "")

    query = Patient.query

    # Search by name or phone
    if q:
        query = query.filter(
            (Patient.name.ilike(f"%{q}%")) |
            (Patient.phone.ilike(f"%{q}%"))
        )

    # Filter by last visit date
    if date_filter:
        query = query.filter(Patient.last_visit == date_filter)

    patients = query.order_by(Patient.id.desc()).all()

    return render_template("patients.html", patients=patients)



@patients_bp.route("/add_patient", methods=["GET", "POST"])
def add_patient():
    if "user" not in session:
        return redirect(url_for("auth_bp.login"))

    if request.method == "POST":
        name = request.form.get("name")
        age = request.form.get("age")
        gender = request.form.get("gender")
        phone = request.form.get("phone")
        disease = request.form.get("disease")
        last_visit = request.form.get("last_visit")
        status = request.form.get("status")

        # File upload handling
        image_file = request.files.get("image")
        filename = "default_patient.png"

        if image_file and image_file.filename != "":
            filename = secure_filename(image_file.filename)
            save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            image_file.save(save_path)

        new_patient = Patient(
        name=name,
        age=age,
        gender=gender,
        phone=phone,
        disease=disease,
        last_visit=last_visit,
        status=status,
        address=request.form.get("address"),
        pincode=request.form.get("pincode"),
        city=request.form.get("city"),
        state=request.form.get("state"),
        image=filename
        )


        db.session.add(new_patient)
        db.session.commit()

        flash("Patient added successfully!", "success")
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
        apps=apps,
        from_patient_profile=True
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
