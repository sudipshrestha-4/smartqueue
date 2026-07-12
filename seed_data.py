from app import create_app
from app.extensions import db
from app.models.service import Service
from app.models.counter import Counter


def seed_base_data(app):
    with app.app_context():
        if Service.query.count() == 0:
            services = [
                Service(name='Cash Deposit', description='Deposit cash into an account', avg_service_duration=5),
                Service(name='Cash Withdrawal', description='Withdraw cash from an account', avg_service_duration=5),
                Service(name='Customer Service', description='General inquiries and support', avg_service_duration=10),
            ]
            db.session.add_all(services)

        if Counter.query.count() == 0:
            counters = [Counter(counter_number=i, status='active') for i in range(1, 5)]
            db.session.add_all(counters)

        db.session.commit()
        print("Seed data inserted successfully.")


if __name__ == '__main__':
    app = create_app()
    seed_base_data(app)