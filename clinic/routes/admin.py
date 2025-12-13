from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from clinic.extensions import db
from functools import wraps
from clinic.models import User, Patient, Appointment, Invoice

admin_bp = Blueprint("admin_bp", __name__)

# ---------------- ADMIN REQUIRED ----------------
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session or session.get("role") != "admin":
            flash("Admin access only.")
            return redirect(url_for("auth_bp.login"))
        return f(*args, **kwargs)
    return wrapper

# ---------------- ADMIN DASHBOARD ----------------
@admin_bp.route("/admin")
@admin_required
def admin_panel():

    total_users = User.query.count()
    total_patients = Patient.query.count()
    total_appointments = Appointment.query.count()
    total_invoices = Invoice.query.count()

    users = User.query.all()

    return render_template(
        "admin/admin_panel.html",
        total_users=total_users,
        total_patients=total_patients,
        total_appointments=total_appointments,
        total_invoices=total_invoices,
        users=users
    )

# ---------------- EDIT USER ----------------
@admin_bp.route("/admin/edit_user/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_user(id):
    user = User.query.get_or_404(id)

    # Prevent admin from changing own role
    if user.id == session["user_id"] and request.method == "POST":
        if request.form["role"] != "admin":
            flash("You cannot remove your own admin role.")
            return redirect(url_for("admin_bp.admin_panel"))

    if request.method == "POST":
        user.fullname = request.form["fullname"]
        user.email = request.form["email"]
        user.role = request.form["role"]

        db.session.commit()
        flash("User updated successfully!")
        return redirect(url_for("admin_bp.admin_panel"))

    return render_template("admin/edit_user.html", user=user)

# ---------------- DELETE USER ----------------
@admin_bp.route("/admin/delete_user/<int:id>")
@admin_required
def delete_user(id):
    user = User.query.get_or_404(id)

    # Cannot delete yourself
    if user.id == session["user_id"]:
        flash("You cannot delete your own account.")
        return redirect(url_for("admin_bp.admin_panel"))

    # Cannot delete any admin
    if user.role == "admin":
        flash("Cannot delete admin account.")
        return redirect(url_for("admin_bp.admin_panel"))

    # Cannot delete user with data
    if user.patients:
        flash("Cannot delete user with existing patients.")
        return redirect(url_for("admin_bp.admin_panel"))

    db.session.delete(user)
    db.session.commit()

    flash("User deleted.")
    return redirect(url_for("admin_bp.admin_panel"))
