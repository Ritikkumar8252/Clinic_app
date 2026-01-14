from flask import Flask, url_for, flash, redirect, session
from flask_migrate import Migrate
import os
from datetime import datetime, timedelta
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
from clinic.routes.templates import templates_bp
from clinic.routes.symptom_templates import  symptom_templates_bp
from flask import request
from clinic.models import Clinic
from clinic.utils import is_clinic_active
from clinic.subscription_plans import PLANS
# from clinic.routes.payments import payments_bp

load_dotenv()

# $env:FLASK_APP="app.py"
# Ye command har new terminal mein ek baar chalani hoti hai

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    # ✅ REQUIRED FOR RENDER / PROXIES
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # ---------------- SECRET KEY ----------------
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY not set")

    app.secret_key = SECRET_KEY


    # ---------------- INSTANCE FOLDER ----------------
    os.makedirs(app.instance_path, exist_ok=True)

    # ---------------- DATABASE (SQLite → PostgreSQL auto) ----------------
    DATABASE_URL = os.environ.get("DATABASE_URL")

    if DATABASE_URL:
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL

        # 🔒 IMPORTANT: prevent Neon SSL connection drops
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_pre_ping": True,     # check connection before use
            "pool_recycle": 300,       # recycle every 5 minutes
            "pool_size": 400,
            "max_overflow": 60,
            "pool_timeout": 30,
            "connect_args": {
            "sslmode": "require"
            }
        }
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
        PERMANENT_SESSION_LIFETIME=timedelta(hours=6),
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
    app.register_blueprint(templates_bp)
    app.register_blueprint( symptom_templates_bp)
    # app.register_blueprint(payments_bp)

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

        # =====================================================
    # GLOBAL ERROR HANDLERS (STEP 1 – CRASH SAFETY)
    # =====================================================
    import logging
    from flask import render_template, request, session

    # -------- LOGGER SETUP --------
    if not app.debug:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(message)s"
        )

    def log_error(error):
        app.logger.error(
            f"""
            ERROR: {error}
            PATH: {request.path}
            METHOD: {request.method}
            USER_ID: {session.get('user_id')}
            CLINIC_ID: {session.get('clinic_id')}
            """,
            exc_info=True
        )

    # -------- 404 --------
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    # -------- 403 --------
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    # -------- 500 --------
    @app.errorhandler(500)
    def server_error(e):
        log_error(e)
        return render_template("errors/500.html"), 500
    
    # ---------- TRIAL / SUBSCRIPTION ----------
    @app.before_request
    def enforce_subscription():

        # ---------- PUBLIC ROUTES ----------
        if (
            request.path in ("/login", "/logout", "/signup", "/forgot-password")
            or request.path.startswith("/reset-password")
            or request.path.startswith("/static")
        ):
            return

        clinic_id = session.get("clinic_id")
        if not clinic_id:
            return

        clinic = Clinic.query.get(clinic_id)
        if not clinic:
            return

        # ---------- AUTO EXPIRE TRIAL ----------
        if (
            clinic.subscription_status == "trial"
            and clinic.trial_ends_at
            and clinic.trial_ends_at < datetime.utcnow()
        ):
            clinic.subscription_status = "expired"
            db.session.commit()

        # ---------- ALLOW SETTINGS PAGE ONLY ----------
        if (
            request.endpoint == "settings_bp.settings"
            and request.method == "GET"
        ):
            return

        # ---------- BLOCK IF INACTIVE ----------
        if not is_clinic_active(clinic):
            flash(
                "Your trial has expired. Please upgrade to continue.",
                "danger"
            )
            return redirect(url_for("settings_bp.settings"))
        
        # ---- BLOCK BILLING FOR TRIAL / NO BILLING PLAN ----
        if request.blueprint == "billing_bp":
            plan = clinic.plan
            if not PLANS.get(plan, {}).get("billing", False):
                flash("Billing is not available on your current plan.", "warning")
                return redirect(url_for("settings_bp.settings"))
            
    @app.context_processor
    def inject_subscription_status():
        clinic_id = session.get("clinic_id")
        if not clinic_id:
            return {}

        clinic = Clinic.query.get(clinic_id)
        if not clinic:
            return {}

        days_left = None
        expired = False

        if clinic.subscription_status == "trial" and clinic.trial_ends_at:
            delta = clinic.trial_ends_at - datetime.utcnow()
            days_left = max(delta.days, 0)
            expired = delta.total_seconds() <= 0

        return {
            "subscription_status": clinic.subscription_status,
            "trial_days_left": days_left,
            "trial_expired": expired,
        }
    return app
