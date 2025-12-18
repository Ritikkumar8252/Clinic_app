from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from clinic.extensions import db
from clinic.models import User
from clinic.routes.auth import login_required, role_required
from werkzeug.utils import secure_filename
import os

settings_bp = Blueprint("settings_bp", __name__, url_prefix="/settings")

ALLOWED_EXT = {"png", "jpg", "jpeg", "pdf"}

def allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


@settings_bp.route("/settings", methods=["GET", "POST"])
@login_required
@role_required("doctor")
def settings():

    user = User.query.get_or_404(session["user_id"])

    if request.method == "POST":

        # -------- PROFILE UPDATE ----------
        if "update_profile" in request.form:

            user.fullname = request.form["fullname"]
            user.email = request.form["email"]
            user.phone = request.form.get("phone")

            photo = request.files.get("profile_photo")
            if photo and photo.filename and allowed(photo.filename):
                filename = secure_filename(photo.filename)
                save_path = os.path.join(current_app.config["DOC_UPLOAD_FOLDER"], filename)
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

            for field, file in doc_fields.items():
                if file and file.filename and allowed(file.filename):
                    filename = secure_filename(file.filename)
                    save_path = os.path.join(current_app.config["DOC_UPLOAD_FOLDER"], filename)
                    file.save(save_path)
                    setattr(user, field, f"uploads/{filename}")

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

            user.clinic_name = request.form["clinic_name"]
            user.speciality = request.form["speciality"]
            user.clinic_phone = request.form["clinic_phone"]
            user.clinic_address = request.form["clinic_address"]

            db.session.commit()
            flash("Clinic details updated successfully.")
            return redirect(url_for("settings_bp.settings"))



    return render_template("dashboard/settings.html", user=user)
