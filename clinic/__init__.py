from flask import Flask
from flask_migrate import Migrate
import os
from datetime import timedelta
from .extensions import db, mail, csrf
from . import models
from .routes.auth import auth_bp
from .routes.dashboard import dashboard_bp
from .routes.patients import patients_bp
from .routes.appointments import appointments_bp
from .routes.billing import billing_bp
from .routes.settings import settings_bp
from .routes.home import home_bp
from dotenv import load_dotenv
from clinic.commands.debug import clinic_debug

load_dotenv()

# $env:FLASK_APP="app.py"
# Ye command har new terminal mein ek baar chalani hoti hai

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # ---------------- SECRET KEY ----------------
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

    # ---------------- INSTANCE FOLDER ----------------
    os.makedirs(app.instance_path, exist_ok=True)

    # ---------------- DATABASE (SQLite → PostgreSQL auto) ----------------
    DATABASE_URL = os.environ.get("DATABASE_URL")

    if DATABASE_URL:
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # ---------------- MAIL CONFIG ----------------
    app.config.update(
        MAIL_SERVER=os.environ.get("MAIL_SERVER"),
        MAIL_PORT=int(os.environ.get("MAIL_PORT", 587)),
        MAIL_USE_TLS=os.environ.get("MAIL_USE_TLS") == "true",
        MAIL_USERNAME=os.environ.get("MAIL_USERNAME"),
        MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD"),
        MAIL_DEFAULT_SENDER=os.environ.get("MAIL_DEFAULT_SENDER"),
    )

    # ---------------- SESSION + CSRF ----------------
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=True,   # IN PRODUCTION = True
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_NAME="clinic_session",
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=60),
        SESSION_REFRESH_EACH_REQUEST=True,
        WTF_CSRF_TIME_LIMIT=None
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
    Migrate(app, db)

    # ---------------- BLUEPRINTS ----------------
    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(patients_bp)
    app.register_blueprint(appointments_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(settings_bp)
    app.cli.add_command(clinic_debug)

    return app
