from flask import (
    Blueprint, render_template, session,
    redirect, url_for, flash, request, abort
)
from clinic.extensions import db
from functools import wraps
from clinic.models import User, Patient, Appointment, Invoice, AuditLog
from clinic.extensions import csrf
from clinic.routes.auth import login_required, role_required


admin_bp = Blueprint("admin_bp", __name__)

# ================================
# ADMIN REQUIRED DECORATOR
# ================================
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin access only.", "danger")
            return redirect(url_for("auth_bp.login"))
        return f(*args, **kwargs)
    return wrapper


# ================================
# ONE-TIME ADMIN SETUP (BOOTSTRAP)
# ================================
@admin_bp.route("/setup-admin", methods=["GET", "POST"])
@csrf.exempt
def setup_admin():

    # 🚫 Agar admin already exist karta hai → block forever
    if User.query.filter_by(role="admin").first():
        abort(404)

    if request.method == "POST":
        fullname = request.form.get("fullname")
        email = request.form.get("email")
        password = request.form.get("password")

        if not fullname or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("admin_bp.setup_admin"))

        admin = User(
            fullname=fullname,
            email=email,
            role="admin"
        )
        admin.set_password(password)

        db.session.add(admin)
        db.session.commit()

        flash("Admin created successfully. Please login.", "success")
        return redirect(url_for("auth_bp.login"))

    return render_template("admin/setup_admin.html")


# ================================
# ADMIN DASHBOARD
# ================================
@admin_bp.route("/admin")
@admin_required
def admin_panel():

    total_users = User.query.count()
    total_patients = Patient.query.count()
    total_appointments = Appointment.query.count()
    total_invoices = Invoice.query.count()

    # NOTE: single hospital scope (future: clinic_id filter)
    users = User.query.order_by(User.created_at.desc()).all()

    return render_template(
        "admin/admin_panel.html",
        total_users=total_users,
        total_patients=total_patients,
        total_appointments=total_appointments,
        total_invoices=total_invoices,
        users=users
    )


# ================================
# CREATE DOCTOR / RECEPTION
# ================================
@admin_bp.route("/admin/create-user", methods=["GET", "POST"])
@admin_required
def create_user():

    if request.method == "POST":
        fullname = request.form.get("fullname")
        email = request.form.get("email")
        role = request.form.get("role")
        password = request.form.get("password")

        if role not in ["doctor", "reception"]:
            flash("Invalid role selected.", "danger")
            return redirect(url_for("admin_bp.create_user"))

        if User.query.filter_by(email=email).first():
            flash("Email already exists.", "warning")
            return redirect(url_for("admin_bp.create_user"))

        user = User(
            fullname=fullname,
            email=email,
            role=role
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash(f"{role.capitalize()} created successfully.", "success")
        return redirect(url_for("admin_bp.admin_panel"))

    return render_template("admin/create_user.html")


# ================================
# EDIT USER
# ================================
@admin_bp.route("/admin/edit_user/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_user(id):

    user = User.query.get_or_404(id)

    # 🚫 Admin cannot downgrade self
    if user.id == session.get("user_id") and request.method == "POST":
        if request.form.get("role") != "admin":
            flash("You cannot remove your own admin role.", "danger")
            return redirect(url_for("admin_bp.admin_panel"))

    if request.method == "POST":
        user.fullname = request.form.get("fullname")
        user.email = request.form.get("email")
        user.role = request.form.get("role")

        db.session.commit()
        flash("User updated successfully.", "success")
        return redirect(url_for("admin_bp.admin_panel"))

    return render_template("admin/edit_user.html", user=user)


# ================================
# DELETE USER
# ================================
@admin_bp.route("/admin/delete_user/<int:id>", methods=["POST"])
@admin_required
def delete_user(id):

    user = User.query.get_or_404(id)

    # 🚫 Cannot delete yourself
    if user.id == session.get("user_id"):
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("admin_bp.admin_panel"))

    # 🚫 Cannot delete any admin
    if user.role == "admin":
        flash("Admin account cannot be deleted.", "danger")
        return redirect(url_for("admin_bp.admin_panel"))

    # 🚫 Cannot delete user with patients
    if user.patients:
        flash("User has patients. Cannot delete.", "warning")
        return redirect(url_for("admin_bp.admin_panel"))

    db.session.delete(user)
    db.session.commit()

    flash("User deleted successfully.", "success")
    return redirect(url_for("admin_bp.admin_panel"))


# ================================
# AUDIT LOGS (READ ONLY)
# ================================
@admin_bp.route("/admin/audit-logs")
@admin_required
def audit_logs():

    page = request.args.get("page", 1, type=int)

    logs = (
        AuditLog.query
        .order_by(AuditLog.created_at.desc())
        .paginate(page=page, per_page=20, error_out=False)
    )

    users = {
        u.id: u.fullname
        for u in User.query.with_entities(User.id, User.fullname).all()
    }

    return render_template(
        "admin/audit_logs.html",
        logs=logs,
        users=users
    )
# ================================
# CREATE  RECEPTIONIST
# ================================
@admin_bp.route("/add_receptionist", methods=["GET", "POST"])
@login_required
@role_required("doctor")
def add_receptionist():
    if request.method == "POST":
        user = User(
            fullname=request.form["fullname"],
            email=request.form["email"],
            role="reception",
            created_by=session["user_id"]
        )
        user.set_password(request.form["password"])
        db.session.add(user)
        db.session.commit()
        flash("Receptionist created")
        return redirect(url_for("dashboard_bp.dashboard"))

    return render_template("admin/add_receptionist.html")
