from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from ..extensions import db
from ..models import Patient, Invoice, Appointment, MedicalRecord ,Prescription
from clinic.routes.auth import login_required, role_required
from clinic.utils import get_current_clinic_id
from datetime import datetime
import os
from werkzeug.utils import secure_filename


patients_bp = Blueprint("patients_bp", __name__)


# =====================================================
# PATIENT LIST
# =====================================================
@patients_bp.route("/patients")
@login_required
@role_required("doctor", "reception")
def patients():
    q = request.args.get("q", "")
    date_filter = request.args.get("date", "")

    clinic_id = get_current_clinic_id()

    query = Patient.query.filter_by(
    clinic_id=clinic_id,
    is_deleted=False
    )


    if q:
        query = query.filter(
            (Patient.name.ilike(f"%{q}%")) |
            (Patient.phone.ilike(f"%{q}%"))
        )

    if date_filter:
        date_obj = datetime.strptime(date_filter, "%Y-%m-%d").date()
        query = query.filter(Patient.last_visit == date_obj)

    page = request.args.get("page", 1, type=int)

    patients = (
        query
        .order_by(Patient.patient_no.desc())
        .paginate(page=page, per_page=20, error_out=False)
    )

    return render_template("patients/patients.html", patients=patients)


# =====================================================
# ADD PATIENT
# =====================================================
@patients_bp.route("/add_patient", methods=["GET", "POST"])
@login_required
@role_required( "reception")
def add_patient():
    from_page = request.args.get("from_page")
    clinic_id = get_current_clinic_id()

    if request.method == "POST":
        name = request.form.get("name")
        age = int(request.form.get("age")) if request.form.get("age") else None
        gender = request.form.get("gender")
        phone = request.form.get("phone")
        disease = request.form.get("disease")

        last_visit = (
            datetime.strptime(request.form["last_visit"], "%Y-%m-%d").date()
            if request.form.get("last_visit") else None
        )

        status = request.form.get("status", "Active")
        address = request.form.get("address")
        pincode = request.form.get("pincode")
        city = request.form.get("city")
        state = request.form.get("state")

        # -------- PATIENT NUMBER (CLINIC WISE) --------
        last_patient = (
            Patient.query
            .filter_by(clinic_id=clinic_id)
            .order_by(Patient.patient_no.desc())
            .first()
        )
        patient_no = (last_patient.patient_no + 1) if last_patient else 1
        # ---------------------------------------------

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

        new_patient = Patient(
            clinic_id=clinic_id,
            patient_no=patient_no,
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


# =====================================================
# DELETE PATIENT
# =====================================================
@patients_bp.route("/delete_patient/<int:id>")
@login_required
@role_required( "reception")
def delete_patient(id):
    clinic_id = get_current_clinic_id()

    patient = Patient.query.filter_by(
        id=id,
        clinic_id=clinic_id
    ).first_or_404()

    patient.is_deleted = True
    db.session.commit()
    flash("Patient deleted!")

    return redirect(url_for("patients_bp.patients"))


# =====================================================
# EDIT PATIENT
# =====================================================
@patients_bp.route("/edit_patient/<int:id>", methods=["GET", "POST"])
@login_required
@role_required( "reception")
def edit_patient(id):
    clinic_id = get_current_clinic_id()

    patient = Patient.query.filter_by(
        id=id,
        clinic_id=clinic_id
    ).first_or_404()

    if request.method == "POST":
        patient.name = request.form["name"]
        patient.disease = request.form["disease"]
        patient.status = request.form["status"]

        last_visit_str = request.form.get("last_visit")
        patient.last_visit = (
            datetime.strptime(last_visit_str, "%Y-%m-%d").date()
            if last_visit_str else None
        )

        db.session.commit()
        flash("Patient updated successfully!")

        return redirect(url_for("patients_bp.patient_profile", id=patient.id))

    return render_template("patients/edit_patient.html", patient=patient)


# =====================================================
# PATIENT PROFILE
# =====================================================
@patients_bp.route("/patient/<int:id>")
@login_required
@role_required("reception", "doctor")
def patient_profile(id):
    clinic_id = get_current_clinic_id()

    patient = Patient.query.filter_by(
        id=id,
        clinic_id=clinic_id,
        is_deleted=False
    ).first_or_404()

    # All appointments (non-deleted)
    apps = (
        Appointment.query
        .filter_by(
            patient_id=patient.id,
            is_deleted=False
        )
        .order_by(Appointment.date.desc())
        .all()
    )

    # ✅ FINALIZED PRESCRIPTIONS ONLY
    prescriptions = (
        Prescription.query
        .join(Appointment)
        .join(Patient)
        .filter(
            Patient.id == patient.id,
            Patient.clinic_id == clinic_id,
            Appointment.is_deleted == False,
            Prescription.finalized == True
        )
        .order_by(Appointment.date.desc())
        .all()
    )

    return render_template(
        "patients/patient_profile.html",
        patient=patient,
        apps=apps,
        prescriptions=prescriptions,
        from_patient_profile=True
    )

# =====================================================
# UPLOAD MEDICAL RECORD
# =====================================================
@patients_bp.route("/upload_record/<int:id>", methods=["GET", "POST"])
@login_required
@role_required( "doctor")
def upload_record(id):
    clinic_id = get_current_clinic_id()

    patient = Patient.query.filter_by(
        id=id,
        clinic_id=clinic_id
    ).first_or_404()

    if request.method == "POST":
        file = request.files.get("record")

        if file and file.filename:
            filename = secure_filename(file.filename)

            upload_dir = current_app.config["RECORD_UPLOAD_FOLDER"]
            os.makedirs(upload_dir, exist_ok=True)

            filepath = os.path.join(upload_dir, filename)
            file.save(filepath)

            record = MedicalRecord(
                clinic_id=clinic_id,
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


# =====================================================
# DELETE MEDICAL RECORD
# =====================================================
@patients_bp.route("/delete_record/<int:record_id>")
@login_required
@role_required( "doctor")
def delete_record(record_id):
    clinic_id = get_current_clinic_id()

    record = MedicalRecord.query.get_or_404(record_id)

    patient = Patient.query.filter_by(
        id=record.patient_id,
        clinic_id=clinic_id
    ).first_or_404()

    file_path = os.path.join(
        current_app.config["RECORD_UPLOAD_FOLDER"],
        record.filename
    )

    if os.path.exists(file_path):
        os.remove(file_path)

    db.session.delete(record)
    db.session.commit()

    flash("Medical record deleted successfully", "success")
    return redirect(
        url_for("patients_bp.patient_profile", id=patient.id)
    )


# =====================================================
# GENERATE CERTIFICATE
# =====================================================
@patients_bp.route("/generate_certificate/<int:id>")
@login_required
@role_required( "doctor")
def generate_certificate(id):
    clinic_id = get_current_clinic_id()

    patient = Patient.query.filter_by(
        id=id,
        clinic_id=clinic_id
    ).first_or_404()

    return f"Certificate generation is coming soon for: {patient.name}"


# =====================================================
# VISIT HISTORY
# =====================================================
@patients_bp.route("/<int:patient_id>/visits")
@login_required
@role_required( "doctor")
def patient_visits(patient_id):
    clinic_id = get_current_clinic_id()

    patient = Patient.query.filter_by(
        id=patient_id,
        clinic_id=clinic_id
    ).first_or_404()

    visits = (
        Appointment.query
        .filter_by(
            patient_id=patient.id,
            status="Completed",
            is_deleted=False
        )
        .order_by(Appointment.date.desc())
        .all()
    )


    return render_template(
        "patients/visit_history.html",
        patient=patient,
        visits=visits
    )

# =====================================================
# RESTORE PATIENT
# =====================================================
@patients_bp.route("/restore_patient/<int:id>")
@login_required
@role_required("doctor")
def restore_patient(id):
    clinic_id = get_current_clinic_id()

    patient = Patient.query.filter_by(
        id=id,
        clinic_id=clinic_id,
        is_deleted=True
    ).first_or_404()

    patient.is_deleted = False
    db.session.commit()

    flash("Patient restored successfully", "success")
    return redirect(url_for("patients_bp.patients"))
