from flask import Blueprint, render_template, request, redirect, url_for, session, flash,current_app
from ..extensions import db
from ..models import Patient, Invoice, Appointment ,MedicalRecord

from datetime import datetime
import os
from werkzeug.utils import secure_filename


patients_bp = Blueprint("patients_bp", __name__)


@patients_bp.route("/patients")
def patients():
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    q = request.args.get("q", "")
    date_filter = request.args.get("date", "")

    # ✅ FILTER BY LOGGED-IN USER
    query = Patient.query.filter_by(user_id=session["user_id"])

    # Search by name or phone
    if q:
        query = query.filter(
            (Patient.name.ilike(f"%{q}%")) |
            (Patient.phone.ilike(f"%{q}%"))
        )

    # Filter by last visit date
    if date_filter:
        query = query.filter(Patient.last_visit == date_filter)

    patients = query.order_by(Patient.patient_no.desc()).all()

    return render_template("patients/patients.html", patients=patients)



@patients_bp.route("/add_patient", methods=["GET", "POST"])
def add_patient():
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    from_page = request.args.get("from_page")

    if request.method == "POST":
        name = request.form.get("name")
        age = request.form.get("age")
        gender = request.form.get("gender")
        phone = request.form.get("phone")
        disease = request.form.get("disease")
        last_visit = request.form.get("last_visit")
        status = request.form.get("status", "Active")

        address = request.form.get("address")
        pincode = request.form.get("pincode")
        city = request.form.get("city")
        state = request.form.get("state")

        # ---------- PATIENT NO LOGIC (NEW) ----------
        last_patient = (
            Patient.query
            .filter_by(user_id=session["user_id"])
            .order_by(Patient.patient_no.desc())
            .first()
        )

        patient_no = (last_patient.patient_no + 1) if last_patient else 1
        # --------------------------------------------

        # PHOTO UPLOAD
        image_file = request.files.get("image")
        filename = "default_profile.png"

        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            save_path = os.path.join(
                current_app.config["PATIENT_UPLOAD_FOLDER"],
                filename
            )
            image_file.save(save_path)

        # Create patient entry
        new_patient = Patient(
            user_id=session["user_id"],
            patient_no=patient_no,   # 👈 IMPORTANT

            name=name,
            age=age,
            gender=gender,
            phone=phone,
            disease=disease,
            last_visit=last_visit,
            status=status,
            address=address,
            pincode=pincode,
            city=city,
            state=state,
            image=filename
        )

        db.session.add(new_patient)
        db.session.commit()

        flash("Patient added successfully!", "success")

        if request.form.get("from_page") == "add_appointment":
            return redirect(url_for("appointments_bp.add_appointment"))

        return redirect(url_for("patients_bp.patients"))

    return render_template("patients/add_patient.html", from_page=from_page)


@patients_bp.route("/delete_patient/<int:id>")
def delete_patient(id):
    patient = Patient.query.filter_by(
        id=id,
        user_id=session["user_id"]
    ).first_or_404()
    db.session.delete(patient)
    db.session.commit()
    flash("Patient deleted!")
    return redirect(url_for("patients_bp.patients"))


@patients_bp.route("/edit_patient/<int:id>", methods=["GET", "POST"])
def edit_patient(id):
    patient = Patient.query.filter_by(
        id=id,
        user_id=session["user_id"]
    ).first_or_404()

    if request.method == "POST":
        patient.name = request.form["name"]
        patient.disease = request.form["disease"]
        patient.last_visit = request.form["last_visit"]
        patient.status = request.form["status"]

        db.session.commit()
        flash("Patient updated successfully!")
        return redirect(url_for("patients_bp.patient_profile",  id=patient.id))

    return render_template("patients/edit_patient.html", patient=patient)


@patients_bp.route("/patient/<int:id>")
def patient_profile(id):
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    patient = Patient.query.filter_by(
        id=id,
        user_id=session["user_id"]
    ).first_or_404()

    # FIX: fetch appointments via patient_id
    apps = Appointment.query.filter_by(patient_id=patient.id).all()

    return render_template(
        "patients/patient_profile.html",
        patient=patient,
        apps=apps,
        from_patient_profile=True
    )


from clinic.models import MedicalRecord

@patients_bp.route("/upload_record/<int:id>", methods=["GET", "POST"])
def upload_record(id):

    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    patient = Patient.query.filter_by(
        id=id,
        user_id=session["user_id"]
    ).first_or_404()

    if request.method == "POST":
        file = request.files.get("record")

        if file and file.filename:
            filename = secure_filename(file.filename)

            # Upload folder
            upload_dir = current_app.config["RECORD_UPLOAD_FOLDER"]
            os.makedirs(upload_dir, exist_ok=True)

            filepath = os.path.join(upload_dir, filename)
            file.save(filepath)

            # ✅ SAVE RECORD IN DB (THIS WAS MISSING)
            record = MedicalRecord(
                patient_id=patient.id,
                filename=filename
            )
            db.session.add(record)
            db.session.commit()

            flash("Record uploaded successfully!", "success")
            return redirect(
                url_for("patients_bp.patient_profile", id=id)
            )

    return render_template(
        "records/upload_record.html",
        patient=patient
    )

@patients_bp.route("/delete_record/<int:record_id>")
def delete_record(record_id):

    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    record = MedicalRecord.query.get_or_404(record_id)

    # Security check: record must belong to logged-in user's patient
    patient = Patient.query.filter_by(
        id=record.patient_id,
        user_id=session["user_id"]
    ).first_or_404()

    # Delete file from disk
    file_path = os.path.join(
        current_app.config["RECORD_UPLOAD_FOLDER"],
        record.filename
    )

    if os.path.exists(file_path):
        os.remove(file_path)

    # Delete DB record
    db.session.delete(record)
    db.session.commit()

    flash("Medical record deleted successfully", "success")
    return redirect(
        url_for("patients_bp.patient_profile", id=patient.id)
    )


@patients_bp.route("/generate_certificate/<int:id>")
def generate_certificate(id):
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))
    patient = Patient.query.filter_by(
    id=id,
    user_id=session["user_id"]
    ).first_or_404()
    return f"Certificate generation is coming soon for: {patient.name}"

@patients_bp.route("/<int:patient_id>/visits")
def patient_visits(patient_id):
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    patient = Patient.query.filter_by(
        id=patient_id,
        user_id=session["user_id"]
    ).first_or_404()

    visits = (
        Appointment.query
        .filter_by(patient_id=patient.id, status="Completed")
        .order_by(Appointment.date.desc())
        .all()
    )

    return render_template(
        "patients/visit_history.html",
        patient=patient,
        visits=visits
    )
