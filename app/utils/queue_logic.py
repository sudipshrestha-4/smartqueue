from app.models.queue_entry import QueueEntry
from app.extensions import db, socketio

# Lower number = higher priority
PRIORITY_RANK = {
    'emergency': 0,
    'elderly': 1,
    'disabled': 1,
    'pregnant': 1,
    'normal': 2,
}


def get_ordered_queue(service_id=None, counter_id=None):
    """
    Returns waiting QueueEntry rows ordered by priority rank, then arrival time.
    Optionally filter by service or counter.
    """
    query = QueueEntry.query.filter_by(status='waiting')

    if service_id:
        query = query.filter_by(service_id=service_id)

    if counter_id:
        query = query.filter_by(counter_id=counter_id)

    entries = query.all()
    entries.sort(
        key=lambda e: (
            PRIORITY_RANK.get(e.priority_type, 2),
            e.arrival_time
        )
    )

    return entries


def get_next_customer(counter_id):
    """
    Returns the single next customer that should be called at a given counter.
    """
    from app.models.counter import Counter

    counter = Counter.query.get(counter_id)
    if not counter:
        return None

    # A counter only serves waiting customers not yet assigned to a specific
    # counter, OR ones already assigned to it (manual assignment)
    candidates = QueueEntry.query.filter(
        QueueEntry.status == 'waiting'
    ).all()

    if not candidates:
        return None

    candidates.sort(
        key=lambda e: (
            PRIORITY_RANK.get(e.priority_type, 2),
            e.arrival_time
        )
    )

    return candidates[0]


def get_customers_ahead(entry):
    """
    Counts how many people are ahead of this entry in priority order.
    Used for deterministic wait estimate.
    """
    ordered = get_ordered_queue(service_id=entry.service_id)

    for idx, e in enumerate(ordered):
        if e.id == entry.id:
            return idx

    return 0


def broadcast_queue_updates(service_id=None):
    """
    Call this after any queue change (join, call-next, complete, no-show).

    Sends fresh position numbers to each waiting customer and tells
    staff/admin dashboards to refresh.
    """
    ordered = get_ordered_queue(service_id=service_id)

    for idx, entry in enumerate(ordered):
        socketio.emit(
            'position_update',
            {
                'entry_id': entry.id,
                'token': entry.token_number,
                'position': idx + 1
            },
            room=f'customer_{entry.customer_id}'
        )

    socketio.emit(
        'queue_updated',
        {},
        room='staff_admin_room'
    )