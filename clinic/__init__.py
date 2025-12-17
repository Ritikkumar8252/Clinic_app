from flask import Flask
import os
from datetime import timedelta
from .extensions import db, mail, csrf
from . import models
from .routes.auth import auth_bp
from .routes.dashboard import dashboard_bp
from .routes.patients import patients_bp
from .routes.appointments import appointments_bp
from .routes.billing import billing_bp
from .routes.admin import admin_bp
from .routes.settings import settings_bp
from .routes.home import home_bp


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # 🔐 SECRET KEY (move to env later)
    app.secret_key = "secret123"

    # ---------------- INSTANCE FOLDER ----------------
    os.makedirs(app.instance_path, exist_ok=True)

    # ---------------- DATABASE ----------------
    db_path = os.path.join(app.instance_path, "site.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    print(">>> USING DATABASE:", db_path)

    # ---------------- MAIL CONFIG ----------------
    app.config.update(
        MAIL_SERVER="sandbox.smtp.mailtrap.io",
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME="f01ffa9fd0ba38",      #  real gmail
        MAIL_PASSWORD="b79474cd0e8dae",         #  gmail app password
        MAIL_DEFAULT_SENDER="cliniccare.dev"
    )

    # ---------------- SESSION + CSRF HARDENING ----------------
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,            # JS cannot access cookies
        SESSION_COOKIE_SECURE=not app.debug,     # 🔥 Auto: True in prod, False locally
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_NAME="clinic_session",
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=60),
        SESSION_REFRESH_EACH_REQUEST=True,
        WTF_CSRF_TIME_LIMIT=None                 # Prevent CSRF expiry issues
    )


    # ---------------- UPLOAD FOLDERS ----------------
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    app.config["PATIENT_UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "static/patient_images")
    app.config["DOC_UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "static/uploads")
    app.config["RECORD_UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "static/records")

    os.makedirs(app.config["PATIENT_UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["DOC_UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["RECORD_UPLOAD_FOLDER"], exist_ok=True)

    # ---------------- INIT EXTENSIONS ----------------
    db.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)

    # ---------------- CREATE TABLES ----------------
    with app.app_context():
        db.create_all()

    # ---------------- BLUEPRINTS ----------------
    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(patients_bp)
    app.register_blueprint(appointments_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(settings_bp)

    return app
