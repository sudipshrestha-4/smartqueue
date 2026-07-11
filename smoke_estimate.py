from app import create_app
from app.extensions import db
from app.models.queue_entry import QueueEntry
from app.models.service import Service
from app.models.user import User
from app.utils.queue_logic import calculate_deterministic_estimate
from seed_data import seed_base_data
from werkzeug.security import generate_password_hash

app = create_app('testing')
with app.app_context():
    db.drop_all()
    db.create_all()
    seed_base_data(app)
    service = Service(name='Test Service', avg_service_duration=15)
    db.session.add(service)
    db.session.commit()
    customer = User(name='Test Customer', email='customer2@test.com', phone='9800000002', password_hash=generate_password_hash('customer123'), role='customer')
    db.session.add(customer)
    db.session.commit()
    entry1 = QueueEntry(token_number='T-100', customer_id=customer.id, service_id=service.id, status='waiting')
    entry2 = QueueEntry(token_number='T-101', customer_id=customer.id, service_id=service.id, status='waiting')
    entry3 = QueueEntry(token_number='T-102', customer_id=customer.id, service_id=service.id, status='waiting')
    db.session.add_all([entry1, entry2, entry3])
    db.session.commit()
    print(calculate_deterministic_estimate(entry3))
