from flask import Flask
import os

from .extensions import db, mail, csrf

# IMPORTANT: import models so SQLAlchemy knows them
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
    # 👇 enable instance folder
    app = Flask(__name__, instance_relative_config=True)
    app.secret_key = "secret123"

    # ---------------- INSTANCE FOLDER ----------------
    os.makedirs(app.instance_path, exist_ok=True)

    # ---------------- DATABASE (INSIDE instance/) ----------------
    db_path = os.path.join(app.instance_path, "site.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    print(">>> USING DATABASE:", db_path)

    # ---------------- MAIL ----------------
    app.config["MAIL_SERVER"] = "smtp.gmail.com"
    app.config["MAIL_PORT"] = 587
    app.config["MAIL_USE_TLS"] = True
    app.config["MAIL_USERNAME"] = "yourgmail@gmail.com"
    app.config["MAIL_PASSWORD"] = "your_app_password"

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
