import unittest

from app import create_app
from app.extensions import db
from app.models.counter import Counter
from app.models.user import User
from seed_data import seed_base_data


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


if __name__ == '__main__':
    unittest.main()
