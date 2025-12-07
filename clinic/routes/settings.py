from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from clinic.extensions import db
from clinic.models import User
from clinic.routes.auth import login_required

settings_bp = Blueprint("settings_bp", __name__, url_prefix="/settings")

# SETTINGS PAGE
@settings_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():

    user = User.query.filter_by(email=session["user"]).first()

    # ------------ POST REQUESTS ------------
    if request.method == "POST":

        # PROFILE UPDATE
        if "update_profile" in request.form:
            user.fullname = request.form["fullname"]
            user.email = request.form["email"]
            user.phone = request.form.get("phone")
            db.session.commit()
            flash("Profile updated")

        # PASSWORD CHANGE
        if "change_password" in request.form:
            old = request.form["old_password"]
            new = request.form["new_password"]

            if user.password != old:
                flash("Incorrect old password")
                return redirect(url_for("settings_bp.settings"))

            user.password = new
            db.session.commit()
            flash("Password updated")

        # CLINIC SETTINGS UPDATE
        if "clinic_save" in request.form:
            session["clinic_name"] = request.form["clinic_name"]
            session["speciality"] = request.form["speciality"]
            session["clinic_phone"] = request.form["clinic_phone"]
            session["clinic_address"] = request.form["clinic_address"]
            flash("Clinic details updated")

        return redirect(url_for("settings_bp.settings"))

    # ------------ GET REQUEST (Render Page) ------------

    clinic = {
        "clinic_name": session.get("clinic_name", ""),
        "speciality": session.get("speciality", ""),
        "clinic_phone": session.get("clinic_phone", ""),
        "clinic_address": session.get("clinic_address", "")
    }

    return render_template("settings.html", user=user, clinic=clinic)
