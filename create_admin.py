from clinic import create_app
from clinic.extensions import db
from clinic.models import User

app = create_app()

with app.app_context():
    if User.query.filter_by(email="admin@gmail.com").first():
        print("Admin already exists")
    else:
        admin = User(
            fullname="Admin",
            email="admin@gmail.com",
            role="admin"
        )
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
        print("Admin created successfully")
