from .extensions import db
from datetime import datetime


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(20), default="staff")
    phone = db.Column(db.String(20))
    aadhar = db.Column(db.String(200))
    mrc_certificate = db.Column(db.String(200))
    clinic_license = db.Column(db.String(200))
    profile_photo = db.Column(db.String(200))
    # Clinic details
    clinic_name = db.Column(db.String(200))
    clinic_phone = db.Column(db.String(50))
    clinic_address = db.Column(db.String(300))
    speciality = db.Column(db.String(100))
    patients = db.relationship('Patient', backref='user', lazy=True)



class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_no = db.Column(db.Integer, nullable=False)  # 👈 NEW
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    phone = db.Column(db.String(20))
    disease = db.Column(db.String(120), nullable=False)
    last_visit = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    image = db.Column(db.String(255), default="default_patient.png")
    address = db.Column(db.String(200))
    pincode = db.Column(db.String(20))
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    records = db.relationship("MedicalRecord", back_populates="patient", lazy=True)




class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)

    type = db.Column(db.String(100))
    date = db.Column(db.String(20))
    time = db.Column(db.String(20))

    status = db.Column(db.String(50), default="Queue")

    # Consultation fields
    symptoms = db.Column(db.Text, default="")
    diagnosis = db.Column(db.Text, default="")
    prescription = db.Column(db.Text, default="")
    advice = db.Column(db.Text, default="")

    # Vitals
    bp = db.Column(db.String(20), default="")
    pulse = db.Column(db.String(20), default="")
    spo2 = db.Column(db.String(20), default="")
    temperature = db.Column(db.String(20), default="")
    weight = db.Column(db.String(20), default="")

    # Follow-up
    follow_up_date = db.Column(db.String(20), default="")

    # Relationship
    patient = db.relationship("Patient", backref="appointments")


class Visit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    visit_date = db.Column(db.String(20), default=datetime.now().strftime("%Y-%m-%d"))
    diagnosis = db.Column(db.String(255))
    treatment = db.Column(db.String(255))
    notes = db.Column(db.Text)

    patient = db.relationship('Patient', backref=db.backref('visits', lazy=True))

class MedicalRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"))
    filename = db.Column(db.String(200), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship("Patient", back_populates="records")


class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    invoice_number = db.Column(db.String(40), unique=True, nullable=False)
    description = db.Column(db.String(255))
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.String(20), default=datetime.now().strftime("%Y-%m-%d"))
    due_date = db.Column(db.String(20))
    status = db.Column(db.String(20), default="Unpaid")

    patient = db.relationship('Patient', backref=db.backref('invoices', lazy=True))


class InvoiceItem(db.Model):
    __tablename__ = "invoice_item"
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"), nullable=False)
    item_name = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)

    invoice = db.relationship("Invoice", backref=db.backref("items", lazy=True))


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(50), default="Cash")
    paid_at = db.Column(db.String(20), default=datetime.now().strftime("%Y-%m-%d"))

    invoice = db.relationship('Invoice', backref=db.backref('payments', lazy=True))