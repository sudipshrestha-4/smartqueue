"""
Generates realistic historical queue data so the analytics dashboard,
historical duration calculation, and reports actually have something
to show. Safe to re-run - it only adds data, existing rows are untouched.
"""
import random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.service import Service
from app.models.counter import Counter
from app.models.queue_entry import QueueEntry

PRIORITY_WEIGHTS = [('normal', 70), ('elderly', 10), ('disabled', 8),
                     ('pregnant', 7), ('emergency', 5)]
DAYS_BACK = 30
CUSTOMERS_PER_DAY_RANGE = (15, 40)


def weighted_priority():
    types, weights = zip(*PRIORITY_WEIGHTS)
    return random.choices(types, weights=weights, k=1)[0]


def get_or_create_dummy_customers(app, count=25):
    with app.app_context():
        customers = User.query.filter_by(role='customer').all()
        needed = count - len(customers)
        for i in range(max(needed, 0)):
            idx = len(customers) + i + 1
            c = User(
                name=f'Sim Customer {idx}',
                email=f'sim_customer_{idx}@example.com',
                phone=f'98000{idx:05d}',
                password_hash=generate_password_hash('password123'),
                role='customer'
            )
            db.session.add(c)
        db.session.commit()
        return User.query.filter_by(role='customer').all()


def generate(app):
    with app.app_context():
        services = Service.query.all()
        counters = Counter.query.filter_by(status='active').all()
        if not services or not counters:
            print("Run seed_data.py first - no services/counters found.")
            return

        customers = get_or_create_dummy_customers(app)
        today = datetime.utcnow().date()
        total_created = 0

        for day_offset in range(DAYS_BACK, 0, -1):
            day = today - timedelta(days=day_offset)
            n_customers = random.randint(*CUSTOMERS_PER_DAY_RANGE)

            for i in range(n_customers):
                service = random.choice(services)
                counter = random.choice(counters)
                customer = random.choice(customers)
                priority = weighted_priority()

                # Spread arrivals across business hours (9am-5pm)
                arrival = datetime.combine(day, datetime.min.time()) + timedelta(
                    hours=random.randint(9, 16),
                    minutes=random.randint(0, 59)
                )

                # 85% completed, 15% no-show
                is_no_show = random.random() < 0.15

                wait_minutes = max(1, random.gauss(8, 4))
                service_start = arrival + timedelta(minutes=wait_minutes)

                entry = QueueEntry(
                    token_number=f"SIM-{day_offset}-{i}",
                    customer_id=customer.id,
                    service_id=service.id,
                    counter_id=counter.id,
                    priority_type=priority,
                    arrival_time=arrival,
                )

                if is_no_show:
                    entry.status = 'no_show'
                else:
                    duration = max(2, random.gauss(service.avg_service_duration or 10, 3))
                    entry.status = 'completed'
                    entry.service_start_time = service_start
                    entry.service_completion_time = service_start + timedelta(minutes=duration)
                    entry.actual_wait_time = round(wait_minutes, 2)

                db.session.add(entry)
                total_created += 1

            db.session.commit()

        print(f"Generated {total_created} simulated queue entries over {DAYS_BACK} days.")


if __name__ == '__main__':
    app = create_app()
    generate(app)