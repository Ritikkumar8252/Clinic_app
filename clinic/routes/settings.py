from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from clinic.extensions import db
from clinic.models import User,Clinic
from clinic.routes.auth import login_required, role_required
from werkzeug.utils import secure_filename
import os

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

                photo.save(save_path)
                user.profile_photo = f"uploads/{filename}"

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




    return render_template("dashboard/settings.html", user=user,clinic=clinic)

# ----------------resceptionist ADD-------
@settings_bp.route("/add-staff", methods=["POST"])
@login_required
@role_required("doctor")
def add_staff():

    email = request.form["email"].strip().lower()

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
