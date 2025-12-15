from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from clinic.extensions import db
from functools import wraps
from clinic.models import User
from clinic import mail

auth_bp = Blueprint("auth_bp", __name__)

# LOGIN REQUIRED DECORATOR
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.")
            return redirect(url_for("auth_bp.login"))
        return f(*args, **kwargs)
    return wrapper



@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        # user not found
        if not user:
            flash("User not found.")
            return redirect(url_for("auth_bp.login"))

        # wrong password
        if user.password != password:
            flash("Incorrect password.")
            return redirect(url_for("auth_bp.login"))

        # store session
        session["user_id"] = user.id
        session["user_email"] = user.email
        session["role"] = user.role
        


        # redirect according to role
        if user.role == "admin":
            return redirect(url_for("admin_bp.admin_panel"))
        else:
            return redirect(url_for("dashboard_bp.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":
        fullname = request.form.get("fullname")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm = request.form.get("confirm_password")

        if password != confirm:
            flash("Passwords do not match.")
            return redirect(url_for('auth_bp.signup'))

        # already exists?
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("Email already registered.")
            return redirect(url_for('auth_bp.signup'))

        new_user = User(fullname=fullname, email=email, password=password, role="staff")
        db.session.add(new_user)
        db.session.commit()

        flash("Account created, please login.")
        return redirect(url_for("auth_bp.login"))

    return render_template("auth/signup.html")

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]
        user = User.query.filter_by(email=email).first()

        if not user:
            flash("Email not found.")
            return redirect(url_for("auth_bp.forgot_password"))

        # Generate OTP
        import random
        otp = random.randint(100000, 999999)

        session["reset_email"] = email
        session["reset_otp"] = str(otp)

        # Send Email
        from flask_mail import Message
        msg = Message("Password Reset OTP", recipients=[email])
        msg.body = f"Your OTP for resetting password is: {otp}"
        mail.send(msg)

        flash("OTP sent to your email.")
        return redirect(url_for("auth_bp.verify_otp"))

    return render_template("auth/forgot_password.html")

@auth_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    if request.method == "POST":
        entered = request.form["otp"]

        if entered == session.get("reset_otp"):
            flash("OTP verified. Set new password.")
            return redirect(url_for("auth_bp.reset_password"))

        flash("Invalid OTP. Try again.")

    return render_template("auth/verify_otp.html")

@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    email = session.get("reset_email")

    if not email:
        flash("Session expired. Try again.")
        return redirect(url_for("auth_bp.forgot_password"))

    user = User.query.filter_by(email=email).first()

    if request.method == "POST":
        new_pass = request.form["password"]
        user.password = new_pass
        db.session.commit()

        session.pop("reset_email", None)
        session.pop("reset_otp", None)

        flash("Password reset successfully. Please login.")
        return redirect(url_for("auth_bp.login"))

    return render_template("auth/reset_password.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.")
    return redirect(url_for("auth_bp.login"))
