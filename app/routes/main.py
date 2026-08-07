from datetime import date, datetime

from flask import Blueprint, render_template
from app.extensions import db
from app.models.counter import Counter
from app.models.service import Service
from app.models.queue_entry import QueueEntry
from app.utils.queue_logic import get_ordered_queue

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    today = date.today()
    start_dt = datetime.combine(today, datetime.min.time())

    services = Service.query.filter_by(is_active=True).order_by(Service.name).all()
    waiting_today = QueueEntry.query.filter(
        QueueEntry.arrival_time >= start_dt,
        QueueEntry.status == 'waiting'
    ).count()
    completed_today = QueueEntry.query.filter(
        QueueEntry.arrival_time >= start_dt,
        QueueEntry.status == 'completed'
    ).count()
    active_counters = Counter.query.filter_by(status='active').count()

    stats = {
        'services_count': len(services),
        'waiting_today': waiting_today,
        'completed_today': completed_today,
        'active_counters': active_counters,
    }

    return render_template("index.html", services=services, stats=stats)


@main_bp.route("/display")
def display():
    """
    Public counter screen - meant for a TV/monitor in the lobby.
    Shows what each active, assigned counter is currently serving and
    who's next in line for that counter's service.
    """
    counters = Counter.query.filter(
        Counter.status == 'active',
        Counter.service_id.isnot(None)
    ).order_by(Counter.counter_number.asc()).all()

    board = []
    for counter in counters:
        called_entry = counter.queue_entries.filter_by(status='called').first()

        next_entry = None
        if counter.service_id:
            waiting = get_ordered_queue(service_id=counter.service_id)
            next_entry = waiting[0] if waiting else None

        board.append({
            'counter': counter,
            'now_serving': called_entry,
            'next_up': next_entry
        })

    return render_template("display.html", board=board)