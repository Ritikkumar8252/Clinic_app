import os
class Config:
    SECRET_KEY = "your-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///../instance/site.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # FILE UPLOAD CONFIG
    # -----------------------------
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")