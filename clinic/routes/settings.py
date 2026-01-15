import csv
from io import StringIO
import clinic
from clinic.models import Patient, Appointment, Prescription, Invoice,User,Clinic
from clinic.subscription_plans import PLANS
from clinic.utils import can_add_staff, get_current_clinic_id, log_action
from flask import Blueprint, abort, render_template, request, redirect, url_for, flash, session, current_app, Response
from clinic.extensions import db
from clinic.routes.auth import login_required, role_required
from werkzeug.utils import secure_filename
import os
from datetime import datetime

settings_bp = Blueprint("settings_bp", __name__, url_prefix="/settings")

ALLOWED_EXT = {"png", "jpg", "jpeg", "pdf"}

def allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


@settings_bp.route("/", methods=["GET", "POST"])
@login_required
@role_required("doctor")
def settings():

    user = User.query.get_or_404(session["user_id"])
    clinic_id = session.get("clinic_id")
    clinic = Clinic.query.get_or_404(clinic_id)
    trial_days_left = None
    if clinic.subscription_status == "trial" and clinic.trial_ends_at:
        delta = clinic.trial_ends_at - datetime.utcnow()
        trial_days_left = max(delta.days, 0)
    if request.method == "POST":

        # -------- PROFILE UPDATE ----------
        if "update_profile" in request.form:

            user.fullname = request.form["fullname"]
            new_email = request.form["email"].strip().lower()

            if new_email != user.email:
                if User.query.filter_by(email=new_email).first():
                    flash("email already in use.", "danger")
                    return redirect(url_for("settings_bp.settings"))

            user.email = new_email
            user.phone = request.form.get("phone")

            photo = request.files.get("profile_photo")
            if photo and photo.filename and allowed(photo.filename):
                filename = secure_filename(photo.filename)
                base_path = current_app.config["UPLOAD_FOLDER"]
                profile_dir = os.path.join(base_path, "doctors", "profile")

                os.makedirs(profile_dir, exist_ok=True)

                save_path = os.path.join(profile_dir, filename)
                photo.save(save_path)

                user.profile_photo = f"uploads/doctors/profile/{filename}"

            db.session.commit()
            flash("Profile updated successfully.")
            return redirect(url_for("settings_bp.settings"))

        # -------- DOCUMENT UPLOAD ----------
        if "upload_docs" in request.form:

            doc_fields = {
                "aadhar": request.files.get("aadhar"),
                "mrc_certificate": request.files.get("mrc"),
                "clinic_license": request.files.get("clinic_license")
            }

            base_path = current_app.config["UPLOAD_FOLDER"]
            doc_dir = os.path.join(base_path, "doctors", "documents")

            os.makedirs(doc_dir, exist_ok=True)

            for field, file in doc_fields.items():
                if file and file.filename and allowed(file.filename):
                    filename = secure_filename(file.filename)

                    save_path = os.path.join(doc_dir, filename)
                    file.save(save_path)

                    # store RELATIVE path in DB
                    setattr(user, field, f"uploads/doctors/documents/{filename}")

            db.session.commit()
            flash("Documents uploaded successfully.")
            return redirect(url_for("settings_bp.settings"))


        # -------- CHANGE PASSWORD ----------
        if "change_password" in request.form:

            old = request.form["old_password"]
            new = request.form["new_password"]

            if not user.check_password(old):
                flash("Old password incorrect.")
                return redirect(url_for("settings_bp.settings"))

            user.set_password(new)
            db.session.commit()

            flash("Password updated successfully.")
            return redirect(url_for("settings_bp.settings"))


        
        # -------- CLINIC SETTINGS ----------
        if "clinic_save" in request.form:

            clinic_id = session.get("clinic_id")

            clinic = Clinic.query.get_or_404(clinic_id)

            clinic.name = request.form["clinic_name"]
            clinic.phone = request.form["clinic_phone"]
            clinic.address = request.form["clinic_address"]

            # doctor-specific field stays in User
            user.speciality = request.form.get("speciality")

            db.session.commit()
            flash("Clinic details updated successfully.")
            return redirect(url_for("settings_bp.settings"))

    return render_template("dashboard/settings.html", user=user,clinic=clinic,
                           trial_days_left=trial_days_left)

# ----------------STAFF ADD-------
@settings_bp.route("/add-staff", methods=["POST"])
@login_required
@role_required("doctor")
def add_staff():

    email = request.form["email"].strip().lower()
    clinic = Clinic.query.get(session["clinic_id"])

    if not can_add_staff(clinic):
        flash("Staff limit reached. Upgrade your plan.", "warning")
        return redirect(url_for("settings_bp.settings"))
    # 🚫 DUPLICATE EMAIL CHECK
    if User.query.filter_by(email=email).first():
        flash("Email already exists. Use a different email.", "danger")
        return redirect(url_for("settings_bp.settings"))

    role = request.form["role"]
    clinic_id = session.get("clinic_id")
    user = User(
        fullname=request.form["fullname"],
        email=email,
        role=role,
        clinic_id=clinic_id,
        created_by=session["user_id"]
    )
    user.set_password(request.form["password"])

    db.session.add(user)
    db.session.commit()

    flash(f"{role.capitalize()} added successfully", "success")
    return redirect(url_for("settings_bp.settings"))
# ----------------STAFF ADD-------
@settings_bp.route("/add-staff", methods=["POST"])
@login_required
@role_required("doctor")
def add_staff():

    email = request.form["email"].strip().lower()
    clinic = Clinic.query.get(session["clinic_id"])

    if not can_add_staff(clinic):
        flash("Staff limit reached. Upgrade your plan.", "warning")
        return redirect(url_for("settings_bp.settings"))
    # 🚫 DUPLICATE EMAIL CHECK
    if User.query.filter_by(email=email).first():
        flash("Email already exists. Use a different email.", "danger")
        return redirect(url_for("settings_bp.settings"))

    role = request.form["role"]
    clinic_id = session.get("clinic_id")
    user = User(
        fullname=request.form["fullname"],
        email=email,
        role=role,
        clinic_id=clinic_id,
        created_by=session["user_id"]
    )
    user.set_password(request.form["password"])

    db.session.add(user)
    db.session.commit()

    flash(f"{role.capitalize()} added successfully", "success")
    return redirect(url_for("settings_bp.settings"))
# ----------------STAFF ADD-------
@settings_bp.route("/add-staff", methods=["POST"])
@login_required
@role_required("doctor")
def add_staff():

    email = request.form["email"].strip().lower()
    clinic = Clinic.query.get(session["clinic_id"])

    if not can_add_staff(clinic):
        flash("Staff limit reached. Upgrade your plan.", "warning")
        return redirect(url_for("settings_bp.settings"))
    # 🚫 DUPLICATE EMAIL CHECK
    if User.query.filter_by(email=email).first():
        flash("Email already exists. Use a different email.", "danger")
        return redirect(url_for("settings_bp.settings"))

    role = request.form["role"]
    clinic_id = session.get("clinic_id")
    user = User(
        fullname=request.form["fullname"],
        email=email,
        role=role,
        clinic_id=clinic_id,
        created_by=session["user_id"]
    )
    user.set_password(request.form["password"])

    db.session.add(user)
    db.session.commit()

    flash(f"{role.capitalize()} added successfully", "success")
    return redirect(url_for("settings_bp.settings"))
# ----------------STAFF ADD-------
@settings_bp.route("/add-staff", methods=["POST"])
@login_required
@role_required("doctor")
def add_staff():

    email = request.form["email"].strip().lower()
    clinic = Clinic.query.get(session["clinic_id"])

    if not can_add_staff(clinic):
        flash("Staff limit reached. Upgrade your plan.", "warning")
        return redirect(url_for("settings_bp.settings"))
    # 🚫 DUPLICATE EMAIL CHECK
    if User.query.filter_by(email=email).first():
        flash("Email already exists. Use a different email.", "danger")
        return redirect(url_for("settings_bp.settings"))

    role = request.form["role"]
    clinic_id = session.get("clinic_id")
    user = User(
        fullname=request.form["fullname"],
        email=email,
        role=role,
        clinic_id=clinic_id,
        created_by=session["user_id"]
    )
    user.set_password(request.form["password"])

    db.session.add(user)
    db.session.commit()

    flash(f"{role.capitalize()} added successfully", "success")
    return redirect(url_for("settings_bp.settings"))
# ----------------STAFF ADD-------
@settings_bp.route("/add-staff", methods=["POST"])
@login_required
@role_required("doctor")
def add_staff():

    email = request.form["email"].strip().lower()
    clinic = Clinic.query.get(session["clinic_id"])

    if not can_add_staff(clinic):
        flash("Staff limit reached. Upgrade your plan.", "warning")
        return redirect(url_for("settings_bp.settings"))
    # 🚫 DUPLICATE EMAIL CHECK
    if User.query.filter_by(email=email).first():
        flash("Email already exists. Use a different email.", "danger")
        return redirect(url_for("settings_bp.settings"))

    role = request.form["role"]
    clinic_id = session.get("clinic_id")
    user = User(
        fullname=request.form["fullname"],
        email=email,
        role=role,
        clinic_id=clinic_id,
        created_by=session["user_id"]
    )
    user.set_password(request.form["password"])

    db.session.add(user)
    db.session.commit()

    flash(f"{role.capitalize()} added successfully", "success")
    return redirect(url_for("settings_bp.settings"))
# ----------------STAFF ADD-------
@settings_bp.route("/add-staff", methods=["POST"])
@login_required
@role_required("doctor")
def add_staff():

    email = request.form["email"].strip().lower()
    clinic = Clinic.query.get(session["clinic_id"])

    if not can_add_staff(clinic):
        flash("Staff limit reached. Upgrade your plan.", "warning")
        return redirect(url_for("settings_bp.settings"))
    # 🚫 DUPLICATE EMAIL CHECK
    if User.query.filter_by(email=email).first():
        flash("Email already exists. Use a different email.", "danger")
        return redirect(url_for("settings_bp.settings"))

    role = request.form["role"]
    clinic_id = session.get("clinic_id")
    user = User(
        fullname=request.form["fullname"],
        email=email,
        role=role,
        clinic_id=clinic_id,
        created_by=session["user_id"]
    )
    user.set_password(request.form["password"])

    db.session.add(user)
    db.session.commit()

    flash(f"{role.capitalize()} added successfully", "success")
    return redirect(url_for("settings_bp.settings"))
# ----------------STAFF ADD-------
@settings_bp.route("/add-staff", methods=["POST"])
@login_required
@role_required("doctor")
def add_staff():

    email = request.form["email"].strip().lower()
    clinic = Clinic.query.get(session["clinic_id"])

    if not can_add_staff(clinic):
        flash("Staff limit reached. Upgrade your plan.", "warning")
        return redirect(url_for("settings_bp.settings"))
    # 🚫 DUPLICATE EMAIL CHECK
    if User.query.filter_by(email=email).first():
        flash("Email already exists. Use a different email.", "danger")
        return redirect(url_for("settings_bp.settings"))

    role = request.form["role"]
    clinic_id = session.get("clinic_id")
    user = User(
        fullname=request.form["fullname"],
        email=email,
        role=role,
        clinic_id=clinic_id,
        created_by=session["user_id"]
    )
    user.set_password(request.form["password"])

    db.session.add(user)
    db.session.commit()

    flash(f"{role.capitalize()} added successfully", "success")
    return redirect(url_for("settings_bp.settings"))
# ----------------STAFF ADD-------
@settings_bp.route("/add-staff", methods=["POST"])
@login_required
@role_required("doctor")
def add_staff():

    email = request.form["email"].strip().lower()
    clinic = Clinic.query.get(session["clinic_id"])

    if not can_add_staff(clinic):
        flash("Staff limit reached. Upgrade your plan.", "warning")
        return redirect(url_for("settings_bp.settings"))
    # 🚫 DUPLICATE EMAIL CHECK
    if User.query.filter_by(email=email).first():
        flash("Email already exists. Use a different email.", "danger")
        return redirect(url_for("settings_bp.settings"))

    role = request.form["role"]
    clinic_id = session.get("clinic_id")
    user = User(
        fullname=request.form["fullname"],
        email=email,
        role=role,
        clinic_id=clinic_id,
        created_by=session["user_id"]
    )
    user.set_password(request.form["password"])

    db.session.add(user)
    db.session.commit()

    flash(f"{role.capitalize()} added successfully", "success")
    return redirect(url_for("settings_bp.settings"))
# ----------------STAFF ADD-------
@settings_bp.route("/add-staff", methods=["POST"])
@login_required
@role_required("doctor")
def add_staff():

    email = request.form["email"].strip().lower()
    clinic = Clinic.query.get(session["clinic_id"])

    if not can_add_staff(clinic):
        flash("Staff limit reached. Upgrade your plan.", "warning")
        return redirect(url_for("settings_bp.settings"))
    # 🚫 DUPLICATE EMAIL CHECK
    if User.query.filter_by(email=email).first():
        flash("Email already exists. Use a different email.", "danger")
        return redirect(url_for("settings_bp.settings"))

    role = request.form["role"]
    clinic_id = session.get("clinic_id")
    user = User(
        fullname=request.form["fullname"],
        email=email,
        role=role,
        clinic_id=clinic_id,
        created_by=session["user_id"]
    )
    user.set_password(request.form["password"])

    db.session.add(user)
    db.session.commit()

    flash(f"{role.capitalize()} added successfully", "success")
    return redirect(url_for("settings_bp.settings"))
# ----------------STAFF ADD-------
@settings_bp.route("/add-staff", methods=["POST"])
@login_required
@role_required("doctor")
def add_staff():

    email = request.form["email"].strip().lower()
    clinic = Clinic.query.get(session["clinic_id"])

    if not can_add_staff(clinic):
        flash("Staff limit reached. Upgrade your plan.", "warning")
        return redirect(url_for("settings_bp.settings"))
    # 🚫 DUPLICATE EMAIL CHECK
    if User.query.filter_by(email=email).first():
        flash("Email already exists. Use a different email.", "danger")
        return redirect(url_for("settings_bp.settings"))

    role = request.form["role"]
    clinic_id = session.get("clinic_id")
    user = User(
        fullname=request.form["fullname"],
        email=email,
        role=role,
        clinic_id=clinic_id,
        created_by=session["user_id"]
    )
    user.set_password(request.form["password"])

    db.session.add(user)
    db.session.commit()

    flash(f"{role.capitalize()} added successfully", "success")
    return redirect(url_for("settings_bp.settings"))
# ----------------STAFF ADD-------
@settings_bp.route("/add-staff", methods=["POST"])
@login_required
@role_required("doctor")
def add_staff():

    email = request.form["email"].strip().lower()
    clinic = Clinic.query.get(session["clinic_id"])

    if not can_add_staff(clinic):
        flash("Staff limit reached. Upgrade your plan.", "warning")
        return redirect(url_for("settings_bp.settings"))
    # 🚫 DUPLICATE EMAIL CHECK
    if User.query.filter_by(email=email).first():
        flash("Email already exists. Use a different email.", "danger")
        return redirect(url_for("settings_bp.settings"))

    role = request.form["role"]
    clinic_id = session.get("clinic_id")
    user = User(
        fullname=request.form["fullname"],
        email=email,
        role=role,
        clinic_id=clinic_id,
        created_by=session["user_id"]
    )
    user.set_password(request.form["password"])

    db.session.add(user)
    db.session.commit()

    flash(f"{role.capitalize()} added successfully", "success")
    return redirect(url_for("settings_bp.settings"))
# ----------------STAFF ADD-------
@settings_bp.route("/add-staff", methods=["POST"])
@login_required
@role_required("doctor")
def add_staff():

    email = request.form["email"].strip().lower()
    clinic = Clinic.query.get(session["clinic_id"])

    if not can_add_staff(clinic):
        flash("Staff limit reached. Upgrade your plan.", "warning")
        return redirect(url_for("settings_bp.settings"))
    # 🚫 DUPLICATE EMAIL CHECK
    if User.query.filter_by(email=email).first():
        flash("Email already exists. Use a different email.", "danger")
        return redirect(url_for("settings_bp.settings"))

    role = request.form["role"]
    clinic_id = session.get("clinic_id")
    user = User(
        fullname=request.form["fullname"],
        email=email,
        role=role,
        clinic_id=clinic_id,
        created_by=session["user_id"]
    )
    user.set_password(request.form["password"])

    db.session.add(user)
    db.session.commit()

    flash(f"{role.capitalize()} added successfully", "success")
    return redirect(url_for("settings_bp.settings"))
# ----------------STAFF ADD-------
@settings_bp.route("/add-staff", methods=["POST"])
@login_required
@role_required("doctor")
def add_staff():

    email = request.form["email"].strip().lower()
    clinic = Clinic.query.get(session["clinic_id"])

    if not can_add_staff(clinic):
        flash("Staff limit reached. Upgrade your plan.", "warning")
        return redirect(url_for("settings_bp.settings"))
    # 🚫 DUPLICATE EMAIL CHECK
    if User.query.filter_by(email=email).first():
        flash("Email already exists. Use a different email.", "danger")
        return redirect(url_for("settings_bp.settings"))

    role = request.form["role"]
    clinic_id = session.get("clinic_id")
    user = User(
        fullname=request.form["fullname"],
        email=email,
        role=role,
        clinic_id=clinic_id,
        created_by=session["user_id"]
    )
    user.set_password(request.form["password"])

    db.session.add(user)
    db.session.commit()

    flash(f"{role.capitalize()} added successfully", "success")
    return redirect(url_for("settings_bp.settings"))
# ----------------STAFF ADD-------
@settings_bp.route("/add-staff", methods=["POST"])
@login_required
@role_required("doctor")
def add_staff():

    email = request.form["email"].strip().lower()
    clinic = Clinic.query.get(session["clinic_id"])

    if not can_add_staff(clinic):
        flash("Staff limit reached. Upgrade your plan.", "warning")
        return redirect(url_for("settings_bp.settings"))
    # 🚫 DUPLICATE EMAIL CHECK
    if User.query.filter_by(email=email).first():
        flash("Email already exists. Use a different email.", "danger")
        return redirect(url_for("settings_bp.settings"))

    role = request.form["role"]
    clinic_id = session.get("clinic_id")
    user = User(
        fullname=request.form["fullname"],
        email=email,
        role=role,
        clinic_id=clinic_id,
        created_by=session["user_id"]
    )
    user.set_password(request.form["password"])

    db.session.add(user)
    db.session.commit()

    flash(f"{role.capitalize()} added successfully", "success")
    return redirect(url_for("settings_bp.settings"))
# ---------------- STAFF ADD ----------------
@settings_bp.route("/add-staff", methods=["POST"])
@login_required
@role_required("doctor")
def add_staff():

    clinic_id = session.get("clinic_id")
    doctor_id = session.get("user_id")

    email = request.form["email"].strip().lower()
    role = request.form["role"]

    clinic = Clinic.query.get_or_404(clinic_id)

    # 🚫 1. STAFF LIMIT CHECK (FIRST)
    if not can_add_staff(clinic):
        flash(
            "Staff limit reached. Please upgrade your plan to add more staff.",
            "warning"
        )
        return redirect(url_for("settings_bp.settings"))

    # 🚫 2. DUPLICATE EMAIL CHECK (GLOBAL)
    if User.query.filter_by(email=email).first():
        flash(
            "Email already exists. Use a different email.",
            "danger"
        )
        return redirect(url_for("settings_bp.settings"))

    # ✅ 3. CREATE STAFF USER
    user = User(
        fullname=request.form["fullname"],
        email=email,
        role=role,
        clinic_id=clinic_id,
        created_by=doctor_id
    )
    user.set_password(request.form["password"])

    db.session.add(user)
    db.session.commit()

    flash(f"{role.capitalize()} added successfully.", "success")
    return redirect(url_for("settings_bp.settings"))

# ---------Export Patients--------------
@settings_bp.route("/export/patients")
@login_required
@role_required("doctor")
def export_patients():
    clinic_id = get_current_clinic_id()

    patients = Patient.query.filter_by(
        clinic_id=clinic_id,
        is_deleted=False
    ).all()

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(["Patient No", "Name", "Age", "Gender", "Phone", "Disease", "Last Visit"])

    for p in patients:
        writer.writerow([
            p.patient_no,
            p.name,
            p.age,
            p.gender,
            p.phone,
            p.disease,
            p.last_visit
        ])

    return Response(
        si.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=patients.csv"
        }
    )
# ---------Export Prescriptions--------------
@settings_bp.route("/export/prescriptions")
@login_required
@role_required("doctor")
def export_prescriptions():
    clinic_id = get_current_clinic_id()

    rows = (
        db.session.query(
            Appointment.id,
            Patient.name,
            Prescription.final_text,
            Prescription.finalized_at
        )
        .join(Patient)
        .join(Prescription)
        .filter(
            Appointment.clinic_id == clinic_id,
            Prescription.finalized == True
        )
        .all()
    )

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(["Appointment ID", "Patient Name", "Prescription", "Date"])

    for r in rows:
        writer.writerow(r)

    return Response(
        si.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=prescriptions.csv"
        }
    )
# ---------Export Invoices--------------
@settings_bp.route("/export/invoices")
@login_required
@role_required("doctor")
def export_invoices():
    clinic_id = get_current_clinic_id()

    invoices = Invoice.query.filter_by(
        clinic_id=clinic_id,
        is_deleted=False
    ).all()

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(["Invoice No", "Patient ID", "Amount", "Status", "Date"])

    for inv in invoices:
        writer.writerow([
            inv.invoice_number,
            inv.patient_id,
            inv.total_amount,
            inv.status,
            inv.created_at
        ])

    return Response(
        si.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=invoices.csv"
        }
    )
# --------change plan
@settings_bp.route("/change-plan", methods=["POST"])
@login_required
@role_required("doctor")
def change_plan():
    clinic = Clinic.query.get_or_404(session["clinic_id"])
    plan = request.form.get("plan")

    if plan not in PLANS:
        abort(400, "Invalid plan")
    clinic.plan = plan  
    clinic.trial_ends_at = None

    db.session.commit()
    log_action(f"PLAN_CHANGED_TO_{plan.upper()}")

    flash("Plan activated successfully.", "success")
    return redirect(url_for("settings_bp.settings"))
