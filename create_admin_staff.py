from werkzeug.security import generate_password_hash
from app import create_app
from app.extensions import db
from app.models.user import User

app = create_app()

with app.app_context():
    if not User.query.filter_by(email='admin@smartqueue.com').first():
        admin = User(
            name='Admin',
            email='admin@smartqueue.com',
            phone='9800000000',
            password_hash=generate_password_hash('Admin@123'),
            role='admin'
        )
        db.session.add(admin)
        print("Created admin -> admin@smartqueue.com / Admin@123")
    else:
        print("Admin account already exists.")

    if not User.query.filter_by(email='staff@smartqueue.com').first():
        staff = User(
            name='Staff One',
            email='staff@smartqueue.com',
            phone='9800000001',
            password_hash=generate_password_hash('Staff@123'),
            role='staff'
        )
        db.session.add(staff)
        print("Created staff -> staff@smartqueue.com / Staff@123")
    else:
        print("Staff account already exists.")

    db.session.commit()