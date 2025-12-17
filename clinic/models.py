from .extensions import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


# =========================
# USER / DOCTOR
# =========================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    fullname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(20), default="staff")
    phone = db.Column(db.String(20))

    # Documents
    aadhar = db.Column(db.String(200))
    mrc_certificate = db.Column(db.String(200))
    clinic_license = db.Column(db.String(200))
    profile_photo = db.Column(db.String(200))

    # Clinic details
    clinic_name = db.Column(db.String(200))
    clinic_phone = db.Column(db.String(50))
    clinic_address = db.Column(db.String(300))
    speciality = db.Column(db.String(100))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patients = db.relationship("Patient", backref="user", lazy=True)

    # ---------- PASSWORD METHODS ----------
    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


# =========================
# PATIENT
# =========================
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    patient_no = db.Column(db.Integer, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    phone = db.Column(db.String(20), index=True)

    disease = db.Column(db.String(120), nullable=False)

    last_visit = db.Column(db.Date)
    status = db.Column(db.String(20), default="Active")

    image = db.Column(db.String(255), default="default_patient.png")

    address = db.Column(db.String(200))
    pincode = db.Column(db.String(20))
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    appointments = db.relationship("Appointment", backref="patient", lazy=True)
    records = db.relationship("MedicalRecord", backref="patient", lazy=True)
    invoices = db.relationship("Invoice", backref="patient", lazy=True)


# =========================
# APPOINTMENT / CONSULTATION
# =========================
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)

    type = db.Column(db.String(50))  # First / Follow-up / Walk-in
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)

    status = db.Column(db.String(20), default="Queue")
    # Queue | In Progress | Completed | Cancelled

    # -------- Consultation --------
    symptoms = db.Column(db.Text, default="")
    diagnosis = db.Column(db.Text, default="")
    prescription = db.Column(db.Text, default="")
    advice = db.Column(db.Text, default="")

    # -------- Vitals --------
    bp = db.Column(db.String(20))
    pulse = db.Column(db.String(20))
    spo2 = db.Column(db.String(20))
    temperature = db.Column(db.String(20))
    weight = db.Column(db.String(20))

    follow_up_date = db.Column(db.Date)

    # -------- Control --------
    prescription_locked = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =========================
# MEDICAL RECORDS
# =========================
class MedicalRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    filename = db.Column(db.String(200), nullable=False)

    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)


# =========================
# INVOICE SEQUENCE (CRITICAL)
# =========================
class InvoiceSequence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    last_number = db.Column(db.Integer, nullable=False, default=0)


# =========================
# INVOICE
# =========================
class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)

    invoice_number = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255))

    total_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default="Unpaid")

    is_locked = db.Column(db.Boolean, default=False)  
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.Date)

    items = db.relationship("InvoiceItem", backref="invoice", lazy=True)
    payments = db.relationship("Payment", backref="invoice", lazy=True)


# =========================
# INVOICE ITEMS
# =========================
class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"), nullable=False)

    item_name = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)


# =========================
# PAYMENTS
# =========================
class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)

    method = db.Column(db.String(50), default="Cash")
    paid_at = db.Column(db.DateTime, default=datetime.utcnow)

# =========================
# AUDIT LOG (SECURITY)
# =========================
class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)

    # ✅ THIS IS THE FIX
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True
    )

    action = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ✅ Relationship now works
    user = db.relationship(
        "User",
        backref=db.backref("audit_logs", lazy="dynamic")
    )
