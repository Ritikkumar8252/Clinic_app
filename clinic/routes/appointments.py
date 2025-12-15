from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file
from ..extensions import db
from ..models import Appointment, Patient
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet

appointments_bp = Blueprint("appointments_bp", __name__)

# ------------------------------------------------
# SECURE HELPERS
# ------------------------------------------------
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

# ------------------------------------------------
# APPOINTMENTS LIST
# ------------------------------------------------
@appointments_bp.route("/appointments")
def appointments():
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    user_id = session["user_id"]

    tab = request.args.get("tab", "queue")
    search = request.args.get("search", "").strip()
    date_filter = request.args.get("date", "").strip()

    base_query = (
        Appointment.query
        .join(Patient)
        .filter(Patient.user_id == user_id)
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
def add_appointment():
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    user_id = session["user_id"]
    patients = Patient.query.filter_by(user_id=user_id).all()

    if request.method == "POST":
        patient_id = request.form["patient_id"]
        visit_type = request.form["type"]

        date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
        time = datetime.strptime(request.form["time"], "%H:%M").time()

        patient = Patient.query.filter_by(
            id=patient_id,
            user_id=user_id
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
def delete_appointment(id):
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    appt = get_secure_appointment(id)
    db.session.delete(appt)
    db.session.commit()

    flash("Appointment deleted!")
    return redirect(url_for("appointments_bp.appointments"))

# ------------------------------------------------
# EDIT APPOINTMENT (FIXED)
# ------------------------------------------------
@appointments_bp.route("/edit_appointment/<int:id>", methods=["GET", "POST"])
def edit_appointment(id):
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

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
# WALKIN CONSULTATION
# ------------------------------------------------
@appointments_bp.route("/walkin", methods=["GET", "POST"])
def walkin():
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    user_id = session["user_id"]
    patients = Patient.query.filter_by(user_id=user_id).all()

    if request.method == "POST":
        patient_id = request.form.get("patient_id")

        # Existing patient
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

        return redirect(url_for("appointments_bp.consult", id=appt.id))

    return render_template(
        "appointments/walkin.html",
        patients=patients
    )


# ------------------------------------------------
# STATUS ACTIONS
# ------------------------------------------------
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

# ------------------------------------------------
# CONSULTATION
# ------------------------------------------------
@appointments_bp.route("/consult/<int:id>", methods=["GET", "POST"])
def consult(id):
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    appt = get_secure_appointment(id)

    patient = Patient.query.filter_by(
        id=appt.patient_id,
        user_id=session["user_id"]
    ).first_or_404()

    if request.method == "POST":
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
        medicines=[]
    )

# ------------------------------------------------
# AUTOSAVE (SAFE)
# ------------------------------------------------
@appointments_bp.route("/autosave/<int:id>", methods=["POST"])
def autosave(id):
    if "user_id" not in session:
        return {"status": "unauthorized"}, 401

    appt = get_secure_appointment(id)
    data = request.get_json()

    if not data:
        return {"status": "ignored"}

    fields = [
        "symptoms", "diagnosis", "prescription", "advice",
        "bp", "pulse", "spo2", "temperature", "weight",
        "follow_up_date"
    ]

    for field in fields:
        if field not in data:
            continue

        if field == "follow_up_date":
            appt.follow_up_date = (
                datetime.strptime(data[field], "%Y-%m-%d").date()
                if data[field] else None
            )
        else:
            setattr(appt, field, data[field])

    db.session.commit()
    return {"status": "saved"}

# ------------------------------------------------
# PRESCRIPTION PDF
# ------------------------------------------------
@appointments_bp.route("/prescription/<int:id>")
def prescription_pdf(id):
    appt = get_secure_appointment(id)

    if not appt.prescription_locked:
        flash("Finalize prescription before downloading", "warning")
        return redirect(url_for("appointments_bp.consult", id=id))

    patient = Patient.query.filter_by(
        id=appt.patient_id,
        user_id=session["user_id"]
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
    text = appt.prescription or "No medicines prescribed"
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

# ------------------------------------------------
# FINALIZE PRESCRIPTION
# ------------------------------------------------
@appointments_bp.route("/finalize_prescription/<int:id>", methods=["POST"])
def finalize_prescription(id):
    appt = get_secure_appointment(id)
    appt.prescription_locked = True
    db.session.commit()

    return redirect(url_for("appointments_bp.prescription_pdf", id=id))
