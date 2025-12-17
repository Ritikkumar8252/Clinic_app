from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from clinic.extensions import db
from functools import wraps
from clinic.models import User
from clinic import mail
from flask_mail import Message
import secrets,time

auth_bp = Blueprint("auth_bp", __name__)

# ---------------- LOGIN REQUIRED ----------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.")
            return redirect(url_for("auth_bp.login"))
        return f(*args, **kwargs)
    return wrapper


# ---------------- LOGIN ----------------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        # unified error (don’t leak which one failed)
        if not user or not user.check_password(password):
            flash("Invalid email or password.")
            return redirect(url_for("auth_bp.login"))

        # store session
        session["user_id"] = user.id
        session["user_email"] = user.email
        session["role"] = user.role

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
            flash("Passwords do not match.")
            return redirect(url_for("auth_bp.signup"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered.")
            return redirect(url_for("auth_bp.signup"))

        user = User(
            fullname=fullname,
            email=email,
            role="staff"
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("Account created successfully. Please login.")
        return redirect(url_for("auth_bp.login"))

    return render_template("auth/signup.html")


# ---------------- FORGOT PASSWORD ----------------
@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":
        email = request.form["email"]
        user = User.query.filter_by(email=email).first()

        if not user:
            flash("Email not found.")
            return redirect(url_for("auth_bp.forgot_password"))

        otp = str(secrets.randbelow(900000) + 100000)

        session.clear()  # clear old auth data safely
        session["reset_email"] = email
        session["reset_otp"] = otp
        session["otp_expiry"] = time.time() + 300  # 5 minutes
        session["otp_attempts"] = 0

        msg = Message(
            "Password Reset OTP",
            recipients=[email]
        )
        msg.body = f"Your OTP for password reset is: {otp}"

        try:
            mail.send(msg)
        except Exception as e:
            print("Mail error:", e)
            flash("Unable to send OTP email. Try again later.")
            return redirect(url_for("auth_bp.forgot_password"))

        flash("OTP sent to your email.")
        return redirect(url_for("auth_bp.verify_otp"))

    return render_template("auth/forgot_password.html")


# ---------------- VERIFY OTP ----------------
@auth_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():

    if "reset_otp" not in session:
        flash("Session expired. Try again.")
        return redirect(url_for("auth_bp.forgot_password"))

    if time.time() > session.get("otp_expiry", 0):
        session.clear()
        flash("OTP expired. Request a new one.")
        return redirect(url_for("auth_bp.forgot_password"))

    if request.method == "POST":
        entered = request.form["otp"]

        session["otp_attempts"] += 1

        if session["otp_attempts"] > 5:
            session.clear()
            flash("Too many attempts. Try again later.")
            return redirect(url_for("auth_bp.forgot_password"))

        if entered == session.get("reset_otp"):
            session.pop("reset_otp")  # invalidate OTP
            flash("OTP verified. Set a new password.")
            return redirect(url_for("auth_bp.reset_password"))

        flash("Invalid OTP.")

    return render_template("auth/verify_otp.html")



# ---------------- RESET PASSWORD ----------------
@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():

    email = session.get("reset_email")
    if not email:
        flash("Session expired. Try again.")
        return redirect(url_for("auth_bp.forgot_password"))

    user = User.query.filter_by(email=email).first_or_404()

    if request.method == "POST":
        password = request.form["password"]
        confirm = request.form["confirm_password"]

        if password != confirm:
            flash("Passwords do not match.")
            return redirect(url_for("auth_bp.reset_password"))

        user.set_password(password)
        db.session.commit()

        session.clear()

        flash("Password reset successfully. Please login.")
        return redirect(url_for("auth_bp.login"))

    return render_template("auth/reset_password.html")



# ---------------- LOGOUT ----------------
@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.")
    return redirect(url_for("auth_bp.login"))
