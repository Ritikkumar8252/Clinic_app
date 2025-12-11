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
    if "user" not in session:
        return redirect(url_for("auth_bp.login"))

    tab = request.args.get("tab", "queue")
    search = request.args.get("search", "").strip()
    date_filter = request.args.get("date", "").strip()

    # Base Query (join with patient)
    base_query = Appointment.query.join(Patient)

    # Apply Search Filter – patient name
    if search:
        base_query = base_query.filter(Patient.name.ilike(f"%{search}%"))

    # Apply Date Filter
    if date_filter:
        base_query = base_query.filter(Appointment.date == date_filter)

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

    return render_template("appointments/add_appointment.html", patients=patients)


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

    return render_template("appointments/edit_appointment.html", app=app_item)

@appointments_bp.route("/walkin")
def walkin():
    # Later you can replace this with a real page
    return "Walk-in consultation page coming soon!"

@appointments_bp.route("/start/<int:id>")
def start(id):
    appt = Appointment.query.get_or_404(id)
    appt.status = "In Progress"
    db.session.commit()

    return redirect(url_for("appointments_bp.consult", id=id))

@appointments_bp.route("/complete/<int:id>")
def complete(id):
    appt = Appointment.query.get_or_404(id)
    appt.status = "Completed"
    db.session.commit()
    return redirect(url_for("appointments_bp.appointments"))

@appointments_bp.route("/cancel/<int:id>")
def cancel(id):
    appt = Appointment.query.get_or_404(id)
    appt.status = "Cancelled"
    db.session.commit()
    return redirect(url_for("appointments_bp.appointments"))


@appointments_bp.route("/consult/<int:id>", methods=["GET", "POST"])
def consult(id):
    if "user" not in session:
        return redirect(url_for("auth_bp.login"))

    appt = Appointment.query.get_or_404(id)
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

        appt.follow_up_date = request.form.get("follow_up_date")

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
    appt = Appointment.query.get_or_404(id)

    data = request.get_json()

    # Update symptoms & findings
    appt.symptoms = data.get("symptoms", "")
    appt.diagnosis = data.get("diagnosis", "")
    appt.prescription = data.get("prescription", "")
    appt.advice = data.get("advice", "")

    # Update vitals
    appt.bp = data.get("bp", "")
    appt.pulse = data.get("pulse", "")
    appt.spo2 = data.get("spo2", "")
    appt.temperature = data.get("temperature", "")
    appt.weight = data.get("weight", "")

    # Follow-up
    appt.follow_up_date = data.get("follow_up_date", "")

    db.session.commit()

    return {"status": "saved"}



@appointments_bp.route("/prescription/<int:id>")
def prescription_pdf(id):
    appt = Appointment.query.get_or_404(id)
    patient = Patient.query.get_or_404(appt.patient_id)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4
    y = height - 2 * cm

    # -------------------- HEADER -------------------------
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(2 * cm, y, "Your Clinic Name")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(2 * cm, y - 20, "Specialization: General Physician")
    pdf.drawString(2 * cm, y - 35, "Phone: +91 9876543210")
    pdf.drawString(2 * cm, y - 50, "Address: Your Clinic Full Address")
    
    # Optional Logo
    # pdf.drawImage("static/images/logo.png", width - 4*cm, y - 10, width=60, height=60)

    # Divider Line
    pdf.setStrokeColor(colors.grey)
    pdf.setLineWidth(1)
    pdf.line(2*cm, y - 65, width - 2*cm, y - 65)

    # -------------------- PATIENT BOX -------------------------
    y -= 110
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(2 * cm, y, "Patient Information")

    # Patient Box Border
    pdf.rect(2*cm, y - 55, width - 4*cm, 50, stroke=1, fill=0)

    pdf.setFont("Helvetica", 12)
    pdf.drawString(2.3 * cm, y - 20, f"Name: {patient.name}")
    pdf.drawString(width/2, y - 20, f"Age: {patient.age}")
    pdf.drawString(2.3 * cm, y - 40, f"Gender: {patient.gender}")
    pdf.drawString(width/2, y - 40, f"Phone: {patient.phone}")

    y -= 90

    # -------------------- PRESCRIPTION SECTION -------------------------
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(2 * cm, y, "Prescription (Rx)")
    y -= 20

    pdf.setFont("Helvetica", 12)

    # Table Header
    headers = ["Medicine", "Dosage", "Duration", "Notes"]
    col_widths = [6*cm, 3*cm, 3*cm, 5*cm]

    x_start = 2 * cm
    y_table = y

    # Background
    pdf.setFillColor(colors.lightgrey)
    pdf.rect(x_start, y_table - 15, sum(col_widths), 18, fill=1, stroke=0)
    pdf.setFillColor(colors.black)

    # Draw header text
    x = x_start
    for i, header in enumerate(headers):
        pdf.drawString(x + 5, y_table - 5, header)
        x += col_widths[i]

    y_table -= 25

    # Example medicines — replace later with DB data
    medicines = [
        ["Paracetamol 650mg", "1-0-1", "5 Days", "Fever"],
        ["Pantoprazole 40mg", "1-0-0", "7 Days", "Acidity"],
        ["ORS", "As needed", "2 Days", "Hydration"]
    ]

    for med in medicines:
        x = x_start
        for i, value in enumerate(med):
            pdf.drawString(x + 5, y_table, value)
            x += col_widths[i]
        y_table -= 18

    y = y_table - 20

    # -------------------- DOCTOR NOTES -------------------------
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(2 * cm, y, "Doctor Notes:")
    y -= 20

    pdf.setFont("Helvetica", 12)
    notes = [
        "- Drink plenty of water.",
        "- Take adequate rest.",
        "- Contact doctor if symptoms persist."
    ]

    for line in notes:
        pdf.drawString(2.3 * cm, y, line)
        y -= 16

    y -= 30

    # -------------------- SIGNATURE -------------------------
    pdf.setFont("Helvetica", 12)
    pdf.drawString(width - 8 * cm, y, "_______________________")
    pdf.drawString(width - 7 * cm, y - 15, "Doctor's Signature")

    y -= 40

    # -------------------- FOOTER -------------------------
    pdf.setStrokeColor(colors.grey)
    pdf.line(2*cm, y, width - 2*cm, y)

    pdf.setFont("Helvetica", 10)
    pdf.drawString(2*cm, y - 15, "Thank you for visiting our clinic.")
    pdf.drawString(2*cm, y - 30, "For emergencies, visit immediately or contact 9876543210.")

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Prescription_{patient.name}.pdf",
        mimetype="application/pdf"
    )




