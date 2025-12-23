from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file,jsonify
from ..extensions import db
from ..models import Appointment, Patient,Prescription, PrescriptionItem
from datetime import datetime
from io import BytesIO
from clinic.routes.auth import login_required, role_required
from clinic.utils import get_current_clinic_owner_id
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from clinic.extensions import csrf

appointments_bp = Blueprint("appointments_bp", __name__)

# ------------------------------------------------
# SECURE HELPERS (CLINIC SAFE)
# ------------------------------------------------
def get_secure_appointment(id):
    clinic_owner_id = get_current_clinic_owner_id()

    return (
        Appointment.query
        .join(Patient)
        .filter(
            Appointment.id == id,
            Patient.clinic_owner_id == clinic_owner_id
        )
        .first_or_404()
    )

# ------------------------------------------------
# APPOINTMENTS LIST
# ------------------------------------------------
@appointments_bp.route("/appointments")
@login_required
@role_required( "reception", "doctor")
def appointments():
    clinic_owner_id = get_current_clinic_owner_id()

    tab = request.args.get("tab", "queue")
    search = request.args.get("search", "").strip()
    date_filter = request.args.get("date", "").strip()

    base_query = (
        Appointment.query
        .join(Patient)
        .filter(Patient.clinic_owner_id == clinic_owner_id)
    )

    if search:
        base_query = base_query.filter(Patient.name.ilike(f"%{search}%"))

    if date_filter:
        date_obj = datetime.strptime(date_filter, "%Y-%m-%d").date()
        base_query = base_query.filter(Appointment.date == date_obj)

    queue = base_query.filter(Appointment.status == "Queue").all()
    inprogress = base_query.filter(Appointment.status == "In Progress").all()
    completed = base_query.filter(Appointment.status == "Completed").all()
    cancelled = base_query.filter(Appointment.status == "Cancelled").all()

    return render_template(
        "appointments/appointments.html",
        tab=tab,
        search=search,
        date_filter=date_filter,
        queue=queue,
        inprogress=inprogress,
        completed=completed,
        cancelled=cancelled
    )

# ------------------------------------------------
# ADD APPOINTMENT
# ------------------------------------------------
@appointments_bp.route("/add_appointment", methods=["GET", "POST"])
@login_required
@role_required("reception")
def add_appointment():
    clinic_owner_id = get_current_clinic_owner_id()
    patients = Patient.query.filter_by(clinic_owner_id=clinic_owner_id).all()

    if request.method == "POST":
        patient_id = request.form["patient_id"]
        visit_type = request.form["type"]
        date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
        time = datetime.strptime(request.form["time"], "%H:%M").time()

        patient = Patient.query.filter_by(
            id=patient_id,
            clinic_owner_id=clinic_owner_id
        ).first_or_404()

        appt = Appointment(
            patient_id=patient.id,
            type=visit_type,
            date=date,
            time=time,
            status="Queue"
        )

        patient.last_visit = date

        db.session.add(appt)
        db.session.commit()

        flash("Appointment booked successfully!")
        return redirect(url_for("appointments_bp.appointments"))

    return render_template("appointments/add_appointment.html", patients=patients)

# ------------------------------------------------
# DELETE APPOINTMENT
# ------------------------------------------------
@appointments_bp.route("/delete_appointment/<int:id>")
@login_required
@role_required("reception")
def delete_appointment(id):
    appt = get_secure_appointment(id)
    db.session.delete(appt)
    db.session.commit()

    flash("Appointment deleted!")
    return redirect(url_for("appointments_bp.appointments"))

# ------------------------------------------------
# EDIT APPOINTMENT
# ------------------------------------------------
@appointments_bp.route("/edit_appointment/<int:id>", methods=["GET", "POST"])
@login_required
@role_required("reception")
def edit_appointment(id):
    appt = get_secure_appointment(id)

    if request.method == "POST":
        date_str = request.form.get("date")
        time_str = request.form.get("time")
        status = request.form.get("status")

        if date_str:
            appt.date = datetime.strptime(date_str, "%Y-%m-%d").date()

        if time_str:
            appt.time = datetime.strptime(time_str, "%H:%M").time()

        if status in ["Queue", "In Progress", "Completed", "Cancelled"]:
            appt.status = status

        db.session.commit()
        flash("Appointment updated!")
        return redirect(url_for("appointments_bp.appointments"))

    return render_template("appointments/edit_appointment.html", appt=appt)

# ------------------------------------------------
# WALK-IN CONSULTATION
# ------------------------------------------------
@appointments_bp.route("/walkin", methods=["GET", "POST"])
@login_required
@role_required("doctor")
def walkin():
    clinic_owner_id = get_current_clinic_owner_id()
    patients = Patient.query.filter_by(clinic_owner_id=clinic_owner_id).all()

    if request.method == "POST":
        patient_id = request.form.get("patient_id")

        # =====================
        # NEW PATIENT FLOW
        # =====================
        if patient_id == "new":
            name = request.form.get("name")
            phone = request.form.get("phone")
            age_raw = request.form.get("age")
            gender = request.form.get("gender")

            if not name:
                flash("Patient name is required", "danger")
                return redirect(url_for("appointments_bp.walkin"))

            # safe age conversion
            age = int(age_raw) if age_raw and age_raw.isdigit() else None

            # generate patient number
            last_patient = (
                Patient.query
                .filter_by(clinic_owner_id=clinic_owner_id)
                .order_by(Patient.patient_no.desc())
                .first()
            )
            patient_no = (last_patient.patient_no + 1) if last_patient else 1

            patient = Patient(
                clinic_owner_id=clinic_owner_id,
                patient_no=patient_no,
                name=name,
                phone=phone,
                age=age,
                gender=gender,
                disease="Walk-in",   # 🔴 VERY IMPORTANT
                last_visit=datetime.now().date(),
                status="Active"
            )

            db.session.add(patient)
            db.session.flush()  # get patient.id safely

        # =====================
        # EXISTING PATIENT FLOW
        # =====================
        else:
            patient = Patient.query.filter_by(
                id=int(patient_id),
                clinic_owner_id=clinic_owner_id
            ).first_or_404()

            patient.last_visit = datetime.now().date()

        # =====================
        # CREATE APPOINTMENT
        # =====================
        now = datetime.now()

        appt = Appointment(
            patient_id=patient.id,
            type="Walk-in",
            date=now.date(),
            time=now.time(),
            status="In Progress"
        )

        db.session.add(appt)
        db.session.commit()

        return redirect(url_for("appointments_bp.consult", id=appt.id))

    return render_template(
        "appointments/walkin.html",
        patients=patients
    )

# ------------------------------------------------
# STATUS ACTIONS
# ------------------------------------------------
@appointments_bp.route("/start/<int:id>")
@login_required
@role_required("reception", "doctor")
def start(id):
    appt = get_secure_appointment(id)
    appt.status = "In Progress"
    db.session.commit()
    return redirect(url_for("appointments_bp.consult", id=id))

@appointments_bp.route("/complete/<int:id>")
@login_required
@role_required("doctor")
def complete(id):
    appt = get_secure_appointment(id)
    appt.prescription_locked = True
    appt.status = "Completed"
    db.session.commit()
    return redirect(url_for("appointments_bp.appointments"))

@appointments_bp.route("/cancel/<int:id>")
@login_required
@role_required("reception")
def cancel(id):
    appt = get_secure_appointment(id)
    appt.status = "Cancelled"
    db.session.commit()
    return redirect(url_for("appointments_bp.appointments"))

# ------------------------------------------------
# CONSULTATION
# ------------------------------------------------
@appointments_bp.route("/consult/<int:id>", methods=["GET", "POST"])
@login_required
@role_required("doctor")
def consult(id):
    appt = get_secure_appointment(id)
    clinic_owner_id = get_current_clinic_owner_id()

    patient = Patient.query.filter_by(
        id=appt.patient_id,
        clinic_owner_id=clinic_owner_id
    ).first_or_404()

    if request.method == "POST":
        appt.symptoms = request.form.get("symptoms")
        appt.diagnosis = request.form.get("diagnosis")
        appt.advice = request.form.get("advice")

        appt.bp = request.form.get("bp")
        appt.pulse = request.form.get("pulse")
        appt.spo2 = request.form.get("spo2")
        appt.temperature = request.form.get("temperature")
        appt.weight = request.form.get("weight")

        fu = request.form.get("follow_up_date")
        appt.follow_up_date = (
            datetime.strptime(fu, "%Y-%m-%d").date() if fu else None
        )

        db.session.commit()
        flash("Consultation saved")
        return redirect(url_for("appointments_bp.consult", id=id))

    
    # BUILD MEDICINES FROM DB

    prescription = Prescription.query.filter_by(
        appointment_id=appt.id
    ).first()

    medicines = []

    if prescription:
        for item in prescription.items:
            medicines.append({
                "med": item.medicine_name,
                "dose": item.dose,
                "days": item.duration_days,
                "notes": item.instructions
            })

    return render_template(
        "appointments/consultation.html",
        appt=appt,
        patient=patient,
        medicines=medicines
    )


# ------------------------------------------------
# AUTOSAVE (SAFE)
# ------------------------------------------------
@appointments_bp.route("/autosave/<int:id>", methods=["POST"])
@login_required
@csrf.exempt   # ✅ VERY IMPORTANT
def autosave(id):
    appt = get_secure_appointment(id)

    if not request.is_json:
        return jsonify({"status": "ignored"}), 200

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "ignored"}), 200

    allowed_fields = [
        "symptoms", "diagnosis", "advice",
        "bp", "pulse", "spo2", "temperature", "weight",
        "follow_up_date"
    ]

    for field in allowed_fields:
        if field not in data:
            continue

        value = data[field]

        if field == "follow_up_date":
            try:
                appt.follow_up_date = (
                    datetime.strptime(value, "%Y-%m-%d").date()
                    if value else None
                )
            except Exception:
                continue  #  invalid date ignored
        else:
            setattr(appt, field, value)

    db.session.commit()
    return jsonify({"status": "saved"}), 200



# ------------------------------------------------
# PRESCRIPTION PDF
# ------------------------------------------------
@appointments_bp.route("/prescription/<int:id>")
@login_required
@role_required( "reception", "doctor")
def prescription_pdf(id):
    appt = get_secure_appointment(id)

    if not appt.prescription_locked:
        flash("Finalize prescription before downloading", "warning")
        return redirect(url_for("appointments_bp.consult", id=id))

    clinic_owner_id = get_current_clinic_owner_id()
    patient = Patient.query.filter_by(
        id=appt.patient_id,
        clinic_owner_id=clinic_owner_id
    ).first_or_404()

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4
    y = height - 2 * cm

    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(2 * cm, y, "Your Clinic Name")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(2 * cm, y - 20, "General Physician")
    pdf.line(2 * cm, y - 50, width - 2 * cm, y - 50)

    y -= 80

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(2 * cm, y, "Patient Information")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(2 * cm, y - 20, f"Name: {patient.name}")
    pdf.drawString(2 * cm, y - 40, f"Age: {patient.age} | Gender: {patient.gender}")

    y -= 80

    styles = getSampleStyleSheet()
    prescription = Prescription.query.filter_by(
        appointment_id=appt.id
    ).first()

    text = prescription.final_text if prescription and prescription.final_text else "No medicines prescribed"

    p = Paragraph(text.replace("\n", "<br/>"), styles["Normal"])
    w, h = p.wrap(width - 4 * cm, height)
    p.drawOn(pdf, 2 * cm, y - h)

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Prescription_{patient.name}.pdf",
        mimetype="application/pdf"
    )

# -----------------------------------------------
# FINALIZE PRESCRIPTION
# -----------------------------------------------
@appointments_bp.route("/finalize_prescription/<int:id>", methods=["POST"])
@login_required
@role_required("doctor")
def finalize_prescription(id):
    appt = get_secure_appointment(id)

    if appt.prescription_locked:
        flash("Prescription already finalized.", "warning")
        return redirect(url_for("appointments_bp.consult", id=id))

    prescription = Prescription.query.filter_by(
        appointment_id=appt.id
    ).first()

    if not prescription or not prescription.items:
        flash("No medicines added to prescription.", "danger")
        return redirect(url_for("appointments_bp.consult", id=id))

    # 🔹 BUILD FINAL SNAPSHOT TEXT (LEGAL RECORD)
    lines = []
    for item in prescription.items:
        line = (
            f"{item.medicine_name}"
            f" | {item.dose or ''}"
            f" | {item.duration_days or ''} days"
            f" | {item.instructions or ''}"
        )
        lines.append(line)

    prescription.final_text = "\n".join(lines)
    prescription.finalized = True
    prescription.finalized_at = datetime.utcnow()

    appt.prescription_locked = True

    db.session.commit()

    flash("Prescription finalized successfully.", "success")
    return redirect(url_for("appointments_bp.consult", id=id))

# -----------------------------------------------
# SAVE PRESCRIPTION
# -----------------------------------------------

@appointments_bp.route("/save_prescription/<int:id>", methods=["POST"])
@login_required
@csrf.exempt
@role_required("doctor")
def save_prescription(id):
    appt = get_secure_appointment(id)

    if appt.prescription_locked:
        return jsonify({"error": "Locked"}), 403

    data = request.get_json()

    prescription = Prescription.query.filter_by(
        appointment_id=appt.id
    ).first()

    if not prescription:
        prescription = Prescription(appointment_id=appt.id)
        db.session.add(prescription)
        db.session.flush()

    # 🔥 remove old items
    PrescriptionItem.query.filter_by(
        prescription_id=prescription.id
    ).delete()

    for item in data.get("items", []):
        db.session.add(
            PrescriptionItem(
                prescription_id=prescription.id,
                medicine_name=item["medicine"],
                dose=item.get("dose"),
                duration_days=item.get("days"),
                instructions=item.get("notes")
            )
        )

    db.session.commit()
    return jsonify({"status": "saved"})
