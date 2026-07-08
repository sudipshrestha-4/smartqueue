import random
import string
from datetime import date
from app.extensions import db
from app.models.queue_entry import QueueEntry


def generate_token_number(prefix='A'):
    """
    Generates a daily-sequential token like 'A-001', 'A-002', ...
    Resets implicitly each day since it counts today's entries only.
    """
    today = date.today()
    today_count = QueueEntry.query.filter(
        db.func.date(QueueEntry.arrival_time) == today
    ).count()

    next_number = today_count + 1
    return f"{prefix}-{next_number:03d}"  # e.g. A-001, A-002 ... A-999