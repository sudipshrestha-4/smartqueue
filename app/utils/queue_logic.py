from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db, socketio
from app.models.counter import Counter
from app.models.queue_entry import QueueEntry
from app.models.service import Service
from app.models.pending_service import PendingService
from app.utils.token_generator import generate_token_number

# Lower number = higher priority
PRIORITY_RANK = {
    'emergency': 0,
    'elderly': 1,
    'disabled': 1,
    'pregnant': 1,
    'normal': 2,
}

ACTIVE_STATUSES = ('waiting', 'called', 'in_service')
TERMINAL_STATUSES = ('completed', 'cancelled', 'no_show')

STATUS_DISPLAY = {
    'waiting': ('Waiting', 'primary'),
    'called': ('Called', 'warning'),
    'in_service': ('Serving', 'info'),
    'completed': ('Completed', 'success'),
    'cancelled': ('Cancelled', 'secondary'),
    'no_show': ('Missed', 'danger'),
}


def get_status_display(status):
    return STATUS_DISPLAY.get(status, (status.replace('_', ' ').title(), 'secondary'))


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
    considered.
    """
    counter = Counter.query.get(counter_id)
    if not counter:
        return None

    if not counter.service_id:
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
    """Counts how many people are ahead of this entry in priority order."""
    ordered = get_ordered_queue(service_id=entry.service_id)

    for idx, e in enumerate(ordered):
        if e.id == entry.id:
            return idx

    return 0


def get_entry_position(entry):
    """Returns 1-based queue position for a waiting entry, else None."""
    if entry.status != 'waiting':
        return None

    ordered = get_ordered_queue(service_id=entry.service_id)
    for idx, e in enumerate(ordered):
        if e.id == entry.id:
            return idx + 1
    return None


def get_assigned_counter_number(entry):
    if not entry.counter_id:
        return None
    counter = Counter.query.get(entry.counter_id)
    return counter.counter_number if counter else None


def calculate_deterministic_estimate(entry):
    """
    Estimated Waiting Time = (Customers Ahead x Average Service Duration)
    / Number of Open Counters for this service.
    Uses each service's avg_service_duration from historical data when available.
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


def calculate_queue_progress(position, total_waiting):
    """Returns 0-100 progress percentage based on position in queue."""
    if not position or not total_waiting or total_waiting <= 1:
        return 100.0 if position == 1 else 0.0
    customers_ahead = position - 1
    return round((1 - customers_ahead / total_waiting) * 100, 1)


def build_tracking_payload(entry, position=None, total_waiting=None):
    """Builds the live tracking data dict for an entry."""
    if position is None and entry.status == 'waiting':
        position = get_entry_position(entry)

    if total_waiting is None:
        total_waiting = len(get_ordered_queue(service_id=entry.service_id))

    customers_ahead = max(position - 1, 0) if position else 0
    estimate = calculate_deterministic_estimate(entry) if entry.status == 'waiting' else 0.0
    entry.deterministic_estimate = estimate

    status_label, status_color = get_status_display(entry.status)

    return {
        'entry_id': entry.id,
        'token': entry.token_number,
        'position': position,
        'customers_ahead': customers_ahead,
        'estimate': estimate,
        'status': entry.status,
        'status_label': status_label,
        'status_color': status_color,
        'counter': get_assigned_counter_number(entry),
        'total_waiting': total_waiting,
        'progress': calculate_queue_progress(position, total_waiting) if position else 100.0,
        'service_name': entry.service.name if entry.service else '',
    }


def get_active_entry(customer_id):
    return QueueEntry.query.filter_by(customer_id=customer_id).filter(
        QueueEntry.status.in_(ACTIVE_STATUSES)
    ).first()


def create_queue_entry(customer_id, service_id, priority_type='normal'):
    """Creates a new waiting queue entry with a unique, per-service daily token."""
    prefix = 'E' if priority_type == 'emergency' else ('P' if priority_type != 'normal' else 'N')

    try:
        service = Service.query.filter_by(id=service_id).with_for_update().first()
        if not service:
            return None

        token_number = generate_token_number(service, prefix)

        entry = QueueEntry(
            token_number=token_number,
            customer_id=customer_id,
            service_id=service_id,
            priority_type=priority_type,
            status='waiting',
            arrival_time=datetime.utcnow()
        )
        db.session.add(entry)
        db.session.commit()

        entry.deterministic_estimate = calculate_deterministic_estimate(entry)
        db.session.commit()
        return entry
    except IntegrityError as e:
        print("IntegrityError:", e)
        db.session.rollback()
    except SQLAlchemyError as e:
        print("SQLAlchemyError:", e)
        db.session.rollback()
    except Exception as e:
        print("Unexpected token creation error:", e)
        db.session.rollback()

    return None


def cancel_queue_entry(entry):
    """
    Cancels a waiting queue entry. Returns (success, message).
    """
    if entry.status != 'waiting':
        return False, 'Token can only be cancelled while waiting.'

    entry.status = 'cancelled'
    db.session.commit()

    broadcast_queue_updates(service_id=entry.service_id)

    socketio.emit(
        'queue_cancelled',
        {
            'entry_id': entry.id,
            'token': entry.token_number,
            'service_name': entry.service.name if entry.service else '',
        },
        room=f'customer_{entry.customer_id}'
    )

    return True, f'Token {entry.token_number} has been cancelled.'


def activate_next_pending_service(customer_id, priority_type='normal'):
    """
    After a service completes, auto-create the next pending queue entry.
    Returns the new QueueEntry or None.
    """
    if get_active_entry(customer_id):
        return None

    pending = PendingService.query.filter_by(
        customer_id=customer_id
    ).order_by(PendingService.sequence_order.asc()).first()

    if not pending:
        return None

    entry = create_queue_entry(
        customer_id,
        pending.service_id,
        pending.priority_type or priority_type
    )
    if not entry:
        return None

    db.session.delete(pending)
    db.session.commit()

    broadcast_queue_updates(service_id=entry.service_id)

    socketio.emit(
        'next_service_activated',
        {
            'entry_id': entry.id,
            'token': entry.token_number,
            'service_name': entry.service.name,
        },
        room=f'customer_{customer_id}'
    )

    return entry


def get_queue_history(customer_id, limit=20):
    """Returns past queue entries for a customer, newest first."""
    return QueueEntry.query.filter_by(customer_id=customer_id).filter(
        QueueEntry.status.in_(TERMINAL_STATUSES)
    ).order_by(QueueEntry.arrival_time.desc()).limit(limit).all()


def broadcast_queue_updates(service_id=None, notify_staff=True):
    """
    Sends fresh position numbers and updated wait estimates to each waiting
    customer, and tells staff/admin dashboards to refresh.
    """
    ordered = get_ordered_queue(service_id=service_id)
    total_waiting = len(ordered)

    for idx, entry in enumerate(ordered):
        payload = build_tracking_payload(entry, position=idx + 1, total_waiting=total_waiting)
        socketio.emit('position_update', payload, room=f'customer_{entry.customer_id}')

    db.session.commit()

    if notify_staff:
        socketio.emit('queue_updated', {}, room='staff_admin_room')


def emit_entry_status_update(entry):
    """Pushes a full tracking update for a single non-waiting entry."""
    payload = build_tracking_payload(entry)
    socketio.emit('position_update', payload, room=f'customer_{entry.customer_id}')


def recalculate_avg_service_duration(service_id, min_samples=5, lookback_days=30):
    """
    Recomputes a service's average service duration from completed entries.
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
