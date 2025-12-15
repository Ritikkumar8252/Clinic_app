from flask import Blueprint, render_template, request, redirect, url_for, session, flash, make_response,send_file
from ..extensions import db
from ..models import Appointment,Patient
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from io import BytesIO
from reportlab.lib import colors


appointments_bp = Blueprint("appointments_bp", __name__)


@appointments_bp.route("/appointments")
def appointments():
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))
    user_id = session["user_id"]


    tab = request.args.get("tab", "queue")
    search = request.args.get("search", "").strip()
    date_filter = request.args.get("date", "").strip()

    # Base Query (join with patient)
    base_query = (
        Appointment.query
        .join(Patient)
        .filter(Patient.user_id == user_id)
    )

    # Apply Search Filter – patient name
    if search:
        base_query = base_query.filter(Patient.name.ilike(f"%{search}%"))

    # Apply Date Filter
    if date_filter:
        date_obj = datetime.strptime(date_filter, "%Y-%m-%d").date()
        base_query = base_query.filter(Appointment.date == date_obj)

    # GET DATA FOR EACH TAB
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




@appointments_bp.route("/add_appointment", methods=["GET", "POST"])
def add_appointment():

    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))
    
    user_id = session["user_id"]

    patients = Patient.query.filter_by(user_id=user_id).all()

    if request.method == "POST":
        patient_id = request.form["patient_id"]
        visit_type = request.form["type"]
        time_str = request.form["time"]
        time = datetime.strptime(time_str, "%H:%M").time()
        date_str = request.form["date"]
        date = datetime.strptime(date_str, "%Y-%m-%d").date()

        patient = Patient.query.filter_by(
            id=patient_id,
            user_id=user_id
        ).first_or_404()

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

    return render_template("appointments/add_appointment.html", patients=patients)


@appointments_bp.route("/delete_appointment/<int:id>")
def delete_appointment(id):
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    app_item = get_secure_appointment(id)
    db.session.delete(app_item)
    db.session.commit()
    flash("Appointment deleted!")
    return redirect(url_for("appointments_bp.appointments"))


@appointments_bp.route("/edit_appointment/<int:id>", methods=["GET", "POST"])
def edit_appointment(id):
    app_item = get_secure_appointment(id)

    if request.method == "POST":
        app_item.patient_name = request.form["patient_name"]
        app_item.doctor = request.form["doctor"]
        date_str = request.form.get("date")
        time_str = request.form.get("time")

        if date_str:
            app_item.date = datetime.strptime(date_str, "%Y-%m-%d").date()

        if time_str:
            app_item.time = datetime.strptime(time_str, "%H:%M").time()

        app_item.status = request.form["status"]

        db.session.commit()
        flash("Appointment updated!")
        return redirect(url_for("appointments_bp.appointments"))

    return render_template("appointments/edit_appointment.html", app=app_item)


# ---------------- STATUS ACTIONS ----------------
def get_secure_appointment(id):
    return (
        Appointment.query
        .join(Patient)
        .filter(
            Appointment.id == id,
            Patient.user_id == session["user_id"]
        )
        .first_or_404()
    )

@appointments_bp.route("/start/<int:id>")
def start(id):
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    appt = get_secure_appointment(id)
    appt.status = "In Progress"
    db.session.commit()

    return redirect(url_for("appointments_bp.consult", id=id))

@appointments_bp.route("/complete/<int:id>")
def complete(id):
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    appt = get_secure_appointment(id)
    appt.prescription_locked = True
    appt.status = "Completed"
    db.session.commit()
    return redirect(url_for("appointments_bp.appointments"))

@appointments_bp.route("/cancel/<int:id>")
def cancel(id):
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    appt = get_secure_appointment(id)
    appt.status = "Cancelled"
    db.session.commit()
    return redirect(url_for("appointments_bp.appointments"))


@appointments_bp.route("/consult/<int:id>", methods=["GET", "POST"])
def consult(id):
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    appt = get_secure_appointment(id)
    patient = Patient.query.get_or_404(appt.patient_id)

    if request.method == "POST":

        # Save consultation fields
        appt.symptoms = request.form.get("symptoms")
        appt.diagnosis = request.form.get("diagnosis")
        appt.prescription = request.form.get("prescription")
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

    return render_template(
        "appointments/consultation.html",
        appt=appt,
        patient=patient,
        medicines=[],  # future pharmacy DB
    )


@appointments_bp.route("/autosave/<int:id>", methods=["POST"])
def autosave(id):
    appt = get_secure_appointment(id)
    data = request.get_json()

    # 🚨 ignore empty or invalid payload
    if not data:
        return {"status": "ignored"}

    # only update fields that are actually sent
    fields = [
        "symptoms", "diagnosis", "prescription", "advice",
        "bp", "pulse", "spo2", "temperature", "weight",
        "follow_up_date"
    ]

    for field in fields:
        if field == "follow_up_date" and data[field]:
            appt.follow_up_date = datetime.strptime(data[field], "%Y-%m-%d").date()
        else:
            setattr(appt, field, data[field])


    db.session.commit()
    return {"status": "saved"}




@appointments_bp.route("/prescription/<int:id>")
def prescription_pdf(id):
    appt = get_secure_appointment(id)

    # 🚫 Block download if not finalized
    if not getattr(appt, "prescription_locked", False):
        flash("Finalize prescription before downloading", "warning")
        return redirect(url_for("appointments_bp.consult", id=id))

    patient = Patient.query.get_or_404(appt.patient_id)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4
    y = height - 2 * cm

    # ---------- HEADER ----------
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(2 * cm, y, "Your Clinic Name")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(2 * cm, y - 20, "General Physician")
    pdf.drawString(2 * cm, y - 35, "Phone: +91 XXXXXXXX")

    pdf.line(2*cm, y - 55, width - 2*cm, y - 55)
    y -= 90

    # ---------- PATIENT INFO ----------
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(2 * cm, y, "Patient Information")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(2 * cm, y - 20, f"Name: {patient.name}")
    pdf.drawString(2 * cm, y - 40, f"Age: {patient.age} | Gender: {patient.gender}")
    pdf.drawString(2 * cm, y - 60, f"Phone: {patient.phone}")

    y -= 100

    # ---------- PRESCRIPTION ----------
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(2 * cm, y, "Prescription (Rx)")
    y -= 25

    # ✅ SAFE TEXT WRAPPING (REAL CLINIC STYLE)
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph

    styles = getSampleStyleSheet()

    prescription_text = appt.prescription or "No medicines prescribed"
    prescription_text = prescription_text.replace("\n", "<br/>")

    p = Paragraph(prescription_text, styles["Normal"])
    w, h = p.wrap(width - 4*cm, height)
    p.drawOn(pdf, 2*cm, y - h)
    y = y - h - 25

    # ---------- DIAGNOSIS ----------
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(2 * cm, y, "Diagnosis")
    y -= 20
    pdf.setFont("Helvetica", 12)
    pdf.drawString(2.2 * cm, y, appt.diagnosis or "-")

    y -= 40

    # ---------- ADVICE ----------
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(2 * cm, y, "Advice")
    y -= 20
    pdf.setFont("Helvetica", 12)
    pdf.drawString(2.2 * cm, y, appt.advice or "-")

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Prescription_{patient.name}.pdf",
        mimetype="application/pdf"
    )


@appointments_bp.route("/finalize_prescription/<int:id>", methods=["POST"])
def finalize_prescription(id):
    appt = get_secure_appointment(id)
    appt.prescription_locked = True
    db.session.commit()

    return redirect(url_for("appointments_bp.prescription_pdf", id=id))


# -----------walkin-----
#  walkin landing page
@appointments_bp.route("/walkin", methods=["GET", "POST"])
def walkin():

    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    user_id = session["user_id"]
    patients = Patient.query.filter_by(user_id=user_id).all()

    if request.method == "POST":

        patient_id = request.form.get("patient_id")

        # ---------- NEW PATIENT ----------
        if patient_id == "new":

            name = request.form["name"]
            phone = request.form["phone"]
            age = int(request.form.get("age")) if request.form.get("age") else None

            gender = request.form.get("gender")

            last_patient = Patient.query.filter_by(
                user_id=user_id
            ).order_by(Patient.patient_no.desc()).first()

            patient_no = last_patient.patient_no + 1 if last_patient else 1

            patient = Patient(
                patient_no=patient_no,
                user_id=user_id,
                name=name,
                phone=phone,
                age=age,
                gender=gender,
                disease="Pending Diagnosis",   # ✔ SAFE
                last_visit=datetime.today().date(),
                status="Active",
                image="default_patient.png"
            )

            db.session.add(patient)
            db.session.flush()  # get patient.id safely

        # ---------- EXISTING PATIENT ----------
        else:
            patient = Patient.query.filter_by(
                id=patient_id,
                user_id=user_id
            ).first_or_404()

        # ---------- CREATE WALK-IN APPOINTMENT ----------
        appt = Appointment(
            patient_id=patient.id,
            type="Walk-in",
            date=datetime.today().date(),
            time=datetime.now().time(), 
            status="In Progress"
        )

        db.session.add(appt)
        db.session.commit()

        return redirect(url_for("appointments_bp.consult", id=appt.id))

    return render_template(
        "appointments/walkin.html",
        patients=patients
    )


@appointments_bp.route("/walkin/create", methods=["POST"])
def create_walkin():
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    patient_id = request.form.get("patient_id")
    user_id = session["user_id"]

    patient = Patient.query.filter_by(
        id=patient_id,
        user_id=user_id
    ).first_or_404()

    now = datetime.now()

    appt = Appointment(
        patient_id=patient.id,
        type="Walk-in",
        date=now.date(),
        time=now.time(),
        status="In Progress"
    )

    patient.last_visit = now.date()

    db.session.add(appt)
    db.session.commit()

    return redirect(
        url_for("appointments_bp.consult", id=appt.id)
    )

