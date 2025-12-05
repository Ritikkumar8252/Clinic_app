from .extensions import db
from datetime import datetime


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(20), default="staff")


class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
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



class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)

    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    type = db.Column(db.String(50))
    time = db.Column(db.String(20))
    date = db.Column(db.String(20))
    status = db.Column(db.String(20), default="Queue")

    patient = db.relationship("Patient", backref="appointments")
    

class Visit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    visit_date = db.Column(db.String(20), default=datetime.now().strftime("%Y-%m-%d"))
    diagnosis = db.Column(db.String(255))
    treatment = db.Column(db.String(255))
    notes = db.Column(db.Text)

    patient = db.relationship('Patient', backref=db.backref('visits', lazy=True))


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


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(50), default="Cash")
    paid_at = db.Column(db.String(20), default=datetime.now().strftime("%Y-%m-%d"))

    invoice = db.relationship('Invoice', backref=db.backref('payments', lazy=True))
