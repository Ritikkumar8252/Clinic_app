from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from clinic.extensions import db, mail
from clinic.models import User, PasswordResetToken
from clinic.utils import log_action
from flask_mail import Message
from functools import wraps
import secrets
from datetime import datetime, timedelta
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

# ---------------- ROLE REQUIRED ----------------
from flask import session, redirect, url_for, flash
from functools import wraps

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):

            # 🚨 request ke bahar ho to allow (CLI / migrations)
            if not session:
                return f(*args, **kwargs)

            user_role = session.get("role")

            if user_role not in roles:
                flash("Access denied.", "danger")
                return redirect(url_for("dashboard_bp.dashboard"))

            return f(*args, **kwargs)
        return wrapper
    return decorator



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
            user = User(fullname=fullname, email=email, role="doctor")
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

        # ---- CREATE RESET TOKEN ----
        token = secrets.token_urlsafe(32)

        reset = PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(minutes=30)
        )

        db.session.add(reset)
        db.session.commit()

        reset_link = url_for(
            "auth_bp.reset_password",
            token=token,
            _external=True
        )

        msg = Message(
            subject="Reset your password",
            recipients=[email],
            body=(
                "Click the link below to reset your password:\n\n"
                f"{reset_link}\n\n"
                "This link is valid for 30 minutes."
            )
        )

        mail.send(msg)

        log_action("PASSWORD_RESET_LINK_SENT", user.id)

        flash("Password reset link sent to your email.", "success")
        return redirect(url_for("auth_bp.login"))

    return render_template("auth/forgot_password.html")


# ---------------- RESET PASSWORD ----------------
@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):

    reset = PasswordResetToken.query.filter_by(
        token=token,
        used=False
    ).first()

    if not reset or reset.expires_at < datetime.utcnow():
        flash("Invalid or expired reset link.", "danger")
        return redirect(url_for("auth_bp.forgot_password"))

    user = User.query.get_or_404(reset.user_id)

    if request.method == "POST":
        password = request.form.get("password")
        confirm = request.form.get("confirm_password")

        if password != confirm or len(password) < 6:
            flash("Invalid password.", "danger")
            return redirect(request.url)

        user.set_password(password)

        reset.used = True
        db.session.commit()

        log_action("PASSWORD_RESET_SUCCESS", user.id)

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
