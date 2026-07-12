from app import create_app
from app.extensions import db
from app.models.service import Service
from app.models.queue_entry import QueueEntry

app = create_app()

with app.app_context():
    # Clear existing queue entries first (they reference services)
    QueueEntry.query.delete()
    Service.query.delete()
    db.session.commit()
    print("Old services and queue entries cleared.")