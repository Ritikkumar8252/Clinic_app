from flask import Blueprint, render_template, session, redirect, url_for, flash,request
from clinic.extensions import db
from functools import wraps
from clinic.models import User, Patient, Appointment, Invoice

admin_bp = Blueprint("admin_bp", __name__)


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "role" not in session or session["role"] != "admin":
            flash("Admin access only.")
            return redirect(url_for("dashboard_bp.dashboard"))
        return f(*args, **kwargs)
    return wrapper


@admin_bp.route("/admin")
@admin_required
def admin_panel():

    total_users = User.query.count()
    total_patients = Patient.query.count()
    total_appointments = Appointment.query.count()
    total_invoices = Invoice.query.count()

    users = User.query.all()

    return render_template(
        "admin_panel.html",
        total_users=total_users,
        total_patients=total_patients,
        total_appointments=total_appointments,
        total_invoices=total_invoices,
        users=users
    )

@admin_bp.route("/admin/edit_user/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_user(id):
    user = User.query.get_or_404(id)

    if request.method == "POST":
        user.fullname = request.form["fullname"]
        user.email = request.form["email"]
        user.role = request.form["role"]

        db.session.commit()
        flash("User updated successfully!")
        return redirect(url_for("admin_bp.admin_panel"))

    return render_template("admin/edit_user.html", user=user)

@admin_bp.route("/admin/delete_user/<int:id>")
@admin_required
def delete_user(id):
    user = User.query.get_or_404(id)

    # Safety: Do not delete main admin
    if user.email == "admin@gmail.com":
        flash("Cannot delete main admin account.")
        return redirect(url_for("admin_bp.admin_panel"))

    db.session.delete(user)
    db.session.commit()

    flash("User deleted.")
    return redirect(url_for("admin_bp.admin_panel"))
