from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from clinic.extensions import db, mail
from clinic.models import User
from clinic.utils import log_action
from flask_mail import Message
from functools import wraps
import secrets
import time

auth_bp = Blueprint("auth_bp", __name__)

# ---------------- LOGIN REQUIRED ----------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("auth_bp.login"))
        return f(*args, **kwargs)
    return wrapper


# ---------------- LOGIN ----------------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    now = time.time()

    # ---- LOGIN RATE LIMIT ----
    if session.get("login_locked_until"):
        if now < session["login_locked_until"]:
            flash("Too many failed attempts. Try again later.", "danger")
            return redirect(url_for("auth_bp.login"))
        else:
            session.pop("login_locked_until", None)
            session.pop("login_attempts", None)

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            session["login_attempts"] = session.get("login_attempts", 0) + 1

            log_action("LOGIN_FAILED")

            if session["login_attempts"] >= 5:
                session["login_locked_until"] = now + (15 * 60)
                flash("Account locked for 15 minutes.", "danger")
            else:
                flash("Invalid email or password.", "danger")

            return redirect(url_for("auth_bp.login"))

        # ---- SUCCESS ----
        session.clear()
        session.permanent = True

        session["user_id"] = user.id
        session["user_email"] = user.email
        session["role"] = user.role

        log_action("LOGIN_SUCCESS", user.id)

        if user.role == "admin":
            return redirect(url_for("admin_bp.admin_panel"))

        return redirect(url_for("dashboard_bp.dashboard"))

    return render_template("auth/login.html")


# ---------------- SIGNUP ----------------
@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":
        fullname = request.form.get("fullname")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm = request.form.get("confirm_password")

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("auth_bp.signup"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for("auth_bp.signup"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "warning")
            return redirect(url_for("auth_bp.signup"))

        try:
            user = User(fullname=fullname, email=email, role="staff")
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            log_action("SIGNUP", user.id)

        except Exception as e:
            db.session.rollback()
            print("SIGNUP ERROR:", e)
            flash("Something went wrong. Try again.", "danger")
            return redirect(url_for("auth_bp.signup"))

        flash("Account created successfully. Please login.", "success")
        return redirect(url_for("auth_bp.login"))

    return render_template("auth/signup.html")


# ---------------- FORGOT PASSWORD ----------------
@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":
        email = request.form.get("email")

        if not email:
            flash("Email required.", "danger")
            return redirect(url_for("auth_bp.forgot_password"))

        user = User.query.filter_by(email=email).first()
        if not user:
            flash("Email not found.", "danger")
            return redirect(url_for("auth_bp.forgot_password"))

        now = time.time()

        # ---- OTP rate limit ----
        if session.get("otp_send_locked_until") and now < session["otp_send_locked_until"]:
            flash("Too many OTP requests. Try later.", "warning")
            return redirect(url_for("auth_bp.forgot_password"))

        session["otp_send_count"] = session.get("otp_send_count", 0) + 1
        if session["otp_send_count"] >= 3:
            session["otp_send_locked_until"] = now + 600
            flash("OTP blocked for 10 minutes.", "warning")
            return redirect(url_for("auth_bp.forgot_password"))

        otp = str(secrets.randbelow(900000) + 100000)

        session["reset_email"] = email
        session["reset_otp"] = otp
        session["otp_expiry"] = now + 300
        session["otp_attempts"] = 0

        msg = Message(
            subject="Password Reset OTP",
            recipients=[email],
            body=f"Your OTP is {otp}. Valid for 5 minutes."
        )

        mail.send(msg)

        log_action("OTP_SENT", user.id)

        flash("OTP sent to your email.", "success")
        return redirect(url_for("auth_bp.verify_otp"))

    return render_template("auth/forgot_password.html")


# ---------------- VERIFY OTP ----------------
@auth_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():

    if "reset_otp" not in session:
        flash("Session expired. Try again.", "warning")
        return redirect(url_for("auth_bp.forgot_password"))

    if time.time() > session.get("otp_expiry", 0):
        session.clear()
        flash("OTP expired. Request a new one.", "danger")
        return redirect(url_for("auth_bp.forgot_password"))

    if request.method == "POST":
        session["otp_attempts"] += 1

        if session["otp_attempts"] > 5:
            session.clear()
            flash("Too many incorrect attempts.", "danger")
            return redirect(url_for("auth_bp.forgot_password"))

        if request.form.get("otp") == session.get("reset_otp"):
            session.pop("reset_otp", None)

            log_action("OTP_VERIFIED")

            flash("OTP verified. Set a new password.", "success")
            return redirect(url_for("auth_bp.reset_password"))

        flash("Invalid OTP.", "danger")

    return render_template("auth/verify_otp.html")


# ---------------- RESET PASSWORD ----------------
@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():

    email = session.get("reset_email")
    if not email:
        flash("Session expired.", "warning")
        return redirect(url_for("auth_bp.forgot_password"))

    user = User.query.filter_by(email=email).first_or_404()

    if request.method == "POST":
        password = request.form.get("password")
        confirm = request.form.get("confirm_password")

        if password != confirm or len(password) < 6:
            flash("Invalid password.", "danger")
            return redirect(url_for("auth_bp.reset_password"))

        user.set_password(password)
        db.session.commit()

        log_action("PASSWORD_RESET", user.id)

        session.clear()
        flash("Password reset successful. Please login.", "success")
        return redirect(url_for("auth_bp.login"))

    return render_template("auth/reset_password.html")


# ---------------- LOGOUT ----------------
@auth_bp.route("/logout")
def logout():
    log_action("LOGOUT", session.get("user_id"))
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("auth_bp.login"))


# ---------------- MAIL TEST (DEV ONLY) ----------------
@auth_bp.route("/mail-test")
def mail_test():
    msg = Message(
        subject="Clinic Test Mail",
        sender=current_app.config["MAIL_USERNAME"],
        recipients=["YOUR_PERSONAL_EMAIL@gmail.com"],
        body="If you received this, SMTP is working."
    )
    mail.send(msg)
    return "Mail sent"
