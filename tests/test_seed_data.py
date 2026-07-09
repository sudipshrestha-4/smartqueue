import unittest

from app import create_app
from app.extensions import db
from app.models.counter import Counter
from app.models.queue_entry import QueueEntry
from app.models.service import Service
from app.models.user import User
from app.utils.queue_logic import calculate_deterministic_estimate
from seed_data import seed_base_data
from werkzeug.security import generate_password_hash


class SeedDataTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.drop_all()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_seed_base_data_creates_counter_and_assigns_staff(self):
        seed_base_data(self.app)

        counter = Counter.query.filter_by(counter_number=1).first()
        staff_user = User.query.filter_by(role='staff').first()

        self.assertIsNotNone(counter)
        self.assertIsNotNone(staff_user)
        self.assertEqual(staff_user.assigned_counter_id, counter.id)

    def test_seed_base_data_creates_second_active_counter(self):
        seed_base_data(self.app)

        counter2 = Counter.query.filter_by(counter_number=2).first()

        self.assertIsNotNone(counter2)
        self.assertEqual(counter2.status, 'active')

    def test_calculate_deterministic_estimate_uses_active_counter_count(self):
        service = Service(name='Test Service', avg_service_duration=15)
        db.session.add(service)
        db.session.commit()

        for counter_number in (1, 2):
            counter = Counter.query.filter_by(counter_number=counter_number).first()
            if not counter:
                counter = Counter(counter_number=counter_number, status='active')
                db.session.add(counter)

        customer = User(
            name='Test Customer',
            email='customer@test.com',
            phone='9800000001',
            password_hash=generate_password_hash('customer123'),
            role='customer',
        )
        db.session.add(customer)
        db.session.commit()

        entry1 = QueueEntry(token_number='T-100', customer_id=customer.id, service_id=service.id, status='waiting')
        entry2 = QueueEntry(token_number='T-101', customer_id=customer.id, service_id=service.id, status='waiting')
        entry3 = QueueEntry(token_number='T-102', customer_id=customer.id, service_id=service.id, status='waiting')
        db.session.add_all([entry1, entry2, entry3])
        db.session.commit()

        estimate = calculate_deterministic_estimate(entry3)

        self.assertEqual(estimate, 15.0)


if __name__ == '__main__':
    unittest.main()
