from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file,jsonify
from ..extensions import db
from ..models import Appointment, Patient,Prescription, PrescriptionItem,PrescriptionTemplateItem,PrescriptionTemplate
from datetime import datetime
from io import BytesIO
from clinic.routes.auth import login_required, role_required
from clinic.utils import get_current_clinic_id, log_action
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from clinic.extensions import csrf
from sqlalchemy import or_

appointments_bp = Blueprint("appointments_bp", __name__)

# ------------------------------------------------
# SECURE HELPERS (CLINIC SAFE)
# ------------------------------------------------
def get_secure_appointment(id):
    clinic_id = get_current_clinic_id()

    return (
        Appointment.query
        .join(Patient)
        .filter(
            Appointment.id == id,
            Appointment.is_deleted == False,
            Patient.is_deleted == False,
            Patient.clinic_id == clinic_id
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
    clinic_id = get_current_clinic_id()
    page_queue = request.args.get("page_queue", 1, type=int)
    page_inprogress = request.args.get("page_inprogress", 1, type=int)
    page_completed = request.args.get("page_completed", 1, type=int)
    page_cancelled = request.args.get("page_cancelled", 1, type=int)

    PER_PAGE = 20

    tab = request.args.get("tab", "queue")
    search = request.args.get("search", "").strip()
    today = datetime.now().date()
    date_filter = request.args.get("date")

    # default = today
    if not date_filter:
        date_filter = today.strftime("%Y-%m-%d")

    base_query = (
    Appointment.query
    .join(Patient)
    .filter(
        Appointment.clinic_id == clinic_id,
        Appointment.is_deleted == False,
        Patient.is_deleted == False
        )
    )


    if search:
        base_query = base_query.filter(
            or_(
                Patient.name.ilike(f"%{search}%"),
                Patient.phone.ilike(f"%{search}%")
            )
        )


    if date_filter:
        date_obj = datetime.strptime(date_filter, "%Y-%m-%d").date()
        base_query = base_query.filter(Appointment.date == date_obj)

    queue = (
        base_query
        .filter(Appointment.status == "Queue")
        .paginate(page=page_queue, per_page=PER_PAGE, error_out=False)
    )
    inprogress = (
        base_query
        .filter(Appointment.status == "In Progress")
        .paginate(page=page_inprogress, per_page=PER_PAGE, error_out=False)
    )
    completed = (
        base_query
        .filter(Appointment.status == "Completed")
        .paginate(page=page_completed, per_page=PER_PAGE, error_out=False)
    )

    cancelled = (
        base_query
        .filter(Appointment.status == "Cancelled")
        .paginate(page=page_cancelled, per_page=PER_PAGE, error_out=False)
    )

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
    clinic_id = get_current_clinic_id()
    patients = Patient.query.filter_by(clinic_id=clinic_id,
                                       is_deleted=False).all()

    if request.method == "POST":
        patient_id = request.form["patient_id"]
        visit_type = request.form["type"]
        date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
        time = datetime.strptime(request.form["time"], "%H:%M").time()

        patient = Patient.query.filter_by(
            id=patient_id,
            clinic_id=clinic_id
        ).first_or_404()

        appt = Appointment(
            clinic_id=clinic_id,
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
    appt.is_deleted = True
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
    clinic_id = get_current_clinic_id()
    patients = Patient.query.filter_by(clinic_id=clinic_id,
                                       is_deleted=False).all()

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
                .filter_by(clinic_id=clinic_id)
                .order_by(Patient.patient_no.desc())
                .first()
            )
            patient_no = (last_patient.patient_no + 1) if last_patient else 1

            patient = Patient(
                clinic_id=clinic_id,
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
                clinic_id=clinic_id
            ).first_or_404()

            patient.last_visit = datetime.now().date()

        # =====================
        # CREATE APPOINTMENT
        # =====================
        now = datetime.utcnow()


        appt = Appointment(
            clinic_id=clinic_id, 
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
    clinic_id = get_current_clinic_id()

    patient = Patient.query.filter_by(
        id=appt.patient_id,
        clinic_id=clinic_id
    ).first_or_404()

    if request.method == "POST":
        appt.symptoms = request.form.get("symptoms")
        appt.diagnosis = request.form.get("diagnosis")
        appt.advice = request.form.get("advice")
        appt.lab_tests = request.form.get("lab_tests")

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

    prescription = (
        Prescription.query
        .join(Appointment)
        .filter(
            Prescription.appointment_id == appt.id,
            Appointment.clinic_id == get_current_clinic_id()
        )
        .first()
    )


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
    if appt.prescription_locked:
        return jsonify({"status": "locked"}), 200


    if not request.is_json:
        return jsonify({"status": "ignored"}), 200

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "ignored"}), 200

    allowed_fields = [
        "symptoms", "diagnosis", "advice", "lab_tests",
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
    log_action("CONSULT_AUTOSAVE")  
    return jsonify({"status": "saved"}), 200



# ------------------------------------------------
# PRESCRIPTION PDF (FULL & FINAL)
# ------------------------------------------------
@appointments_bp.route("/prescription/<int:id>")
@login_required
@role_required("reception", "doctor")
def prescription_pdf(id):

    appt = get_secure_appointment(id)

    if not appt.prescription_locked:
        flash("Finalize prescription before downloading", "warning")
        return redirect(url_for("appointments_bp.consult", id=id))

    clinic_id = get_current_clinic_id()
    patient = Patient.query.filter_by(
        id=appt.patient_id,
        clinic_id=clinic_id
    ).first_or_404()

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4
    y = height - 2 * cm

    def new_page():
        nonlocal y
        pdf.showPage()
        pdf.setFont("Helvetica", 11)
        y = height - 2 * cm

    def check_space(space=40):
        nonlocal y
        if y < space:
            new_page()

    # ---------------- HEADER ----------------
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(2 * cm, y, "Your Clinic Name")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(2 * cm, y - 18, "General Physician")

    pdf.line(2 * cm, y - 40, width - 2 * cm, y - 40)
    y -= 70

    # ---------------- PATIENT INFO ----------------
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(2 * cm, y, "Patient Information")
    y -= 20

    pdf.setFont("Helvetica", 11)
    pdf.drawString(2 * cm, y, f"Name: {patient.name}")
    y -= 14
    pdf.drawString(2 * cm, y, f"Age: {patient.age} | Gender: {patient.gender}")
    y -= 25

    # ---------------- VITALS ----------------
    vitals = [
        ("BP", appt.bp),
        ("Pulse", appt.pulse),
        ("SpO2", appt.spo2),
        ("Temperature", appt.temperature),
        ("Weight", appt.weight),
    ]

    if any(v for _, v in vitals):
        check_space()
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(2 * cm, y, "Vitals")
        y -= 18

        pdf.setFont("Helvetica", 11)
        for label, value in vitals:
            if value:
                pdf.drawString(2.2 * cm, y, f"{label}: {value}")
                y -= 14
        y -= 10

    # ---------------- SYMPTOMS ----------------
    if appt.symptoms:
        check_space()
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(2 * cm, y, "Symptoms")
        y -= 18

        pdf.setFont("Helvetica", 11)
        for s in appt.symptoms.split(","):
            pdf.drawString(2.2 * cm, y, f"- {s.strip()}")
            y -= 14
        y -= 10

    # ---------------- DIAGNOSIS ----------------
    if appt.diagnosis:
        check_space()
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(2 * cm, y, "Diagnosis")
        y -= 18

        pdf.setFont("Helvetica", 11)
        for d in appt.diagnosis.split(","):
            pdf.drawString(2.2 * cm, y, f"- {d.strip()}")
            y -= 14
        y -= 10

    # ---------------- MEDICINES ----------------
    check_space()
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(2 * cm, y, "Prescription")
    y -= 18

    prescription = (
        Prescription.query
        .join(Appointment)
        .filter(
            Prescription.appointment_id == appt.id,
            Appointment.clinic_id == get_current_clinic_id()
        )
        .first()
    )


    pdf.setFont("Helvetica", 11)
    line_height = 16

    if prescription and prescription.items:
        for item in prescription.items:
            check_space()
            line = item.medicine_name
            if item.dose:
                line += f" | {item.dose}"
            if item.duration_days:
                line += f" | {item.duration_days} days"
            if item.instructions:
                line += f" | {item.instructions}"

            pdf.drawString(2 * cm, y, line)
            y -= line_height
    else:
        pdf.drawString(2 * cm, y, "No medicines prescribed")
        y -= 16

    y -= 10

    # ---------------- LAB TESTS ----------------
    if hasattr(appt, "lab_tests") and appt.lab_tests:
        check_space()
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(2 * cm, y, "Lab Tests")
        y -= 18

        pdf.setFont("Helvetica", 11)
        for line in appt.lab_tests.split("\n"):
            pdf.drawString(2.2 * cm, y, f"- {line.strip()}")
            y -= 14
        y -= 10

    # ---------------- ADVICE ----------------
    if appt.advice:
        check_space()
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(2 * cm, y, "Advice")
        y -= 18

        pdf.setFont("Helvetica", 11)
        for a in appt.advice.split(","):
            pdf.drawString(2.2 * cm, y, f"- {a.strip()}")
            y -= 14
        y -= 10

    # ---------------- FOLLOW UP ----------------
    if appt.follow_up_date:
        check_space()
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(2 * cm, y, "Follow-up Date")
        y -= 18

        pdf.setFont("Helvetica", 11)
        pdf.drawString(2.2 * cm, y, str(appt.follow_up_date))
        y -= 20

    # ---------------- FOOTER ----------------
    check_space()
    pdf.line(2 * cm, y, width - 2 * cm, y)
    y -= 14
    pdf.setFont("Helvetica", 10)
    pdf.drawString(
        2 * cm,
        y,
        "This prescription is electronically generated and does not require a signature."
    )

    # ---------------- FINALIZE ----------------
    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"Prescription_{patient.name}.pdf"
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

    prescription = (
        Prescription.query
        .join(Appointment)
        .filter(
            Prescription.appointment_id == appt.id,
            Appointment.clinic_id == get_current_clinic_id()
        )
        .first()
    )

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
    log_action("PRESCRIPTION_FINALIZED")

    db.session.commit()

    flash("Prescription finalized successfully.", "success")
    return redirect(url_for("appointments_bp.consult", id=id))

# -----------------------------------------------
# SAVE PRESCRIPTION (SAFE & FINAL)
# -----------------------------------------------

@appointments_bp.route("/save_prescription/<int:id>", methods=["POST"])
@login_required
@role_required("doctor")
@csrf.exempt
def save_prescription(id):
    appt = get_secure_appointment(id)

    # 🔐 Always lock using prescription (source of truth)
    prescription = (
        Prescription.query
        .join(Appointment)
        .filter(
            Prescription.appointment_id == appt.id,
            Appointment.clinic_id == get_current_clinic_id()
        )
        .first()
    )

    if prescription and prescription.finalized:
        log_action("PRESCRIPTION_EDIT_BLOCKED")
        return jsonify({"error": "Prescription finalized"}), 403

    # 🧾 Validate JSON
    data = request.get_json(silent=True)
    if not data or "items" not in data:
        return jsonify({"error": "Invalid payload"}), 400

    # 🆕 Create prescription if not exists
    if not prescription:
        prescription = Prescription(appointment_id=appt.id)
        db.session.add(prescription)
        db.session.flush()

    # 🔥 Remove old draft items
    PrescriptionItem.query.filter_by(
        prescription_id=prescription.id
    ).delete()

    # ➕ Insert new items
    for item in data.get("items", []):
        med = item.get("medicine", "").strip()
        if not med:
            continue

        db.session.add(
            PrescriptionItem(
                prescription_id=prescription.id,
                medicine_name=med,
                dose=item.get("dose"),
                duration_days=int(item["days"]) if str(item.get("days")).isdigit() else None,
                instructions=item.get("notes")
            )
        )

    db.session.commit()
    log_action("PRESCRIPTION_DRAFT_SAVE")

    return jsonify({"status": "saved"})