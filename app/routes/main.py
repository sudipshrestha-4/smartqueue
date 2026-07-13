from flask import Blueprint, render_template
from app.models.counter import Counter
from app.utils.queue_logic import get_ordered_queue

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    return render_template("index.html")


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