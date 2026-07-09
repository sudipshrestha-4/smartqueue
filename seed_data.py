from app import create_app
from app.extensions import db
from app.models.counter import Counter
from app.models.service import Service
from app.models.user import User
from werkzeug.security import generate_password_hash


def seed_base_data(app=None):
    app = app or create_app()

    with app.app_context():
        db.create_all()

        if Service.query.count() == 0:
            services = [
                Service(name='Account Opening', description='Open a new bank account', avg_service_duration=15),
                Service(name='Loan Inquiry', description='Ask about loan products', avg_service_duration=20),
                Service(name='Cash Deposit', description='Deposit cash into an account', avg_service_duration=5),
                Service(name='Cash Withdrawal', description='Withdraw cash from an account', avg_service_duration=5),
                Service(name='Customer Support', description='General inquiries and support', avg_service_duration=10),
            ]
            db.session.add_all(services)

        if Counter.query.count() == 0:
            counters = [Counter(counter_number=i, status='active') for i in range(1, 5)]
            db.session.add_all(counters)

        counter1 = Counter.query.filter_by(counter_number=1).first()
        if not counter1:
            counter1 = Counter(counter_number=1, status='active')
            db.session.add(counter1)

        staff_user = User.query.filter_by(role='staff').first()
        if not staff_user:
            staff_user = User(
                name='Test Staff',
                email='staff@test.com',
                phone='9800000000',
                password_hash=generate_password_hash('staff123'),
                role='staff',
            )
            db.session.add(staff_user)

        if staff_user and not staff_user.assigned_counter_id:
            staff_user.assigned_counter_id = counter1.id

        db.session.commit()

        if staff_user:
            print(f"Assigned {staff_user.email} to counter {counter1.counter_number}")

        print('Seed data inserted successfully.')
        return counter1, staff_user


if __name__ == '__main__':
    seed_base_data()
