from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_wtf import CSRFProtect
from flask_migrate import Migrate

db = SQLAlchemy()
mail = Mail()
csrf = CSRFProtect()
migrate = Migrate()