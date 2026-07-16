from datetime import datetime, timedelta
from app.extensions import db, socketio
from app.models.counter import Counter
from app.models.queue_entry import QueueEntry
from app.models.service import Service

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
    Only customers waiting for the service this counter is assigned to are
    considered - a counter set up for "Cash Deposit" should never be offered
    a "Loan Inquiry" customer.
    """
    counter = Counter.query.get(counter_id)
    if not counter:
        return None

    if not counter.service_id:
        # Counter has no service assigned yet - nothing it can correctly serve.
        return None

    candidates = QueueEntry.query.filter(
        QueueEntry.status == 'waiting',
        QueueEntry.service_id == counter.service_id
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


def calculate_deterministic_estimate(entry):
    """
    Estimated Waiting Time = (Customers Ahead x Average Service Duration) / Active Counters.
    Matches section 3.1.6 of the proposal.
    "Active Counters" means counters that are active AND assigned to this
    entry's specific service - a counter serving a different service doesn't
    help this customer's wait time.
    """
    customers_ahead = get_customers_ahead(entry)
    avg_duration = getattr(entry.service, 'avg_service_duration', None)

    active_counters = Counter.query.filter_by(
        status='active',
        service_id=entry.service_id
    ).count()
    active_counters = max(active_counters, 1)

    if avg_duration is None:
        return 0.0

    estimate = (customers_ahead * avg_duration) / active_counters
    return round(estimate, 2)


def broadcast_queue_updates(service_id=None):
    """
    Call this after any queue change (join, call-next, complete, no-show).
    Sends fresh position numbers and updated wait estimates to each waiting
    customer, and tells staff/admin dashboards to refresh.
    """
    ordered = get_ordered_queue(service_id=service_id)

    for idx, entry in enumerate(ordered):
        position = idx + 1
        entry.deterministic_estimate = calculate_deterministic_estimate(entry)

        socketio.emit(
            'position_update',
            {
                'entry_id': entry.id,
                'token': entry.token_number,
                'position': position,
                'estimate': entry.deterministic_estimate
            },
            room=f'customer_{entry.customer_id}'
        )

    db.session.commit()
    socketio.emit('queue_updated', {}, room='staff_admin_room')


def recalculate_avg_service_duration(service_id, min_samples=5, lookback_days=30):
    """
    Recomputes a service's average service duration from real completed
    QueueEntry history (Service Duration = Completion Time - Start Time),
    instead of the static default set when the service was created.
    Only overwrites the default once there's enough real data (min_samples),
    and only looks at recent history so one unusually slow/fast day doesn't
    permanently skew today's estimates.
    """
    service = Service.query.get(service_id)
    if not service:
        return None

    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    completed = QueueEntry.query.filter(
        QueueEntry.service_id == service_id,
        QueueEntry.status == 'completed',
        QueueEntry.service_completion_time.isnot(None),
        QueueEntry.service_start_time.isnot(None),
        QueueEntry.service_completion_time >= cutoff
    ).all()

    durations = [e.calculate_service_duration() for e in completed]
    durations = [d for d in durations if d is not None]

    if len(durations) < min_samples:
        return service.avg_service_duration

    new_avg = round(sum(durations) / len(durations), 2)
    service.avg_service_duration = new_avg
    db.session.commit()
    return new_avg


def recalculate_all_service_durations():
    """Runs the recalculation for every service. Called from the admin panel."""
    results = {}
    for service in Service.query.all():
        results[service.name] = recalculate_avg_service_duration(service.id)
    return results