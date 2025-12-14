from flask import Flask
from flask_mail import Mail
from .extensions import db
from .models import User
from flask_migrate import Migrate

migrate = Migrate()

# create mail object
mail = Mail()

from .routes.auth import auth_bp
from .routes.dashboard import dashboard_bp
from .routes.patients import patients_bp
from .routes.appointments import appointments_bp
from .routes.billing import billing_bp
from .routes.admin import admin_bp
from .routes.settings import settings_bp
from .routes.home import home_bp
import os


def create_app():
    app = Flask(__name__)
    app.secret_key = "secret123"

    # ********* UPLOAD FOLDERS *********
    app.config["PATIENT_UPLOAD_FOLDER"] = os.path.join(app.root_path, "static/patient_images")
    app.config["DOC_UPLOAD_FOLDER"] = os.path.join(app.root_path, "static/uploads")

    os.makedirs(app.config["PATIENT_UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["DOC_UPLOAD_FOLDER"], exist_ok=True)

    # ********* DATABASE *********
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # ✅ RECORD UPLOAD CONFIG (THIS IS MANDATORY)
    app.config["RECORD_UPLOAD_FOLDER"] = os.path.join(
        app.root_path, "static", "records"
    )
    # ******** EMAIL ********
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = "yourgmail@gmail.com"
    app.config['MAIL_PASSWORD'] = "your_app_password"
    
    # Init extensions
    db.init_app(app)
    mail.init_app(app)

    # Register blueprints
    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(patients_bp)
    app.register_blueprint(appointments_bp)
    app.register_blueprint(billing_bp, url_prefix="/billing")
    app.register_blueprint(admin_bp)
    app.register_blueprint(settings_bp)

    # Auto-create admin
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(email="admin@gmail.com").first():
            admin = User(
                fullname="Admin",
                email="admin@gmail.com",
                password="admin123",
                role="admin"
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created")

    migrate.init_app(app, db)

    return app
