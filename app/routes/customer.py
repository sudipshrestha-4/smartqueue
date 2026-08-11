from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.extensions import db, socketio
from app.utils.decorators import role_required
from app.utils.queue_logic import (
    broadcast_queue_updates,
    calculate_deterministic_estimate,
    get_ordered_queue,
    get_entry_position,
    get_assigned_counter_number,
    build_tracking_payload,
    create_queue_entry,
    cancel_queue_entry,
    get_queue_history,
    get_status_display,
    activate_next_pending_service,
)
from app.utils.qr_generator import generate_qr_code
from app.utils.token_generator import get_bank_status_info, is_bank_open
from app.models.service import Service
from app.models.queue_entry import QueueEntry
from app.models.pending_service import PendingService
from app.models.feedback import Feedback

customer_bp = Blueprint('customer', __name__)

VALID_PRIORITIES = {'normal', 'elderly', 'disabled', 'pregnant', 'emergency'}


@customer_bp.app_context_processor
def inject_customer_context():
    pending_feedback_count = 0
    if current_user.is_authenticated and getattr(current_user, 'role', None) == 'customer':
        pending_feedback_count = QueueEntry.query.filter_by(
            customer_id=current_user.id,
            status='completed',
        ).outerjoin(Feedback, QueueEntry.id == Feedback.queue_entry_id).filter(
            Feedback.id.is_(None)
        ).count()

    return {
        'get_status_display': get_status_display,
        'pending_feedback_count': pending_feedback_count,
    }


@customer_bp.route('/dashboard')
@login_required
@role_required('customer')
def dashboard():
    active_entries = QueueEntry.query.filter_by(
        customer_id=current_user.id
    ).filter(
        QueueEntry.status.in_(['waiting', 'called', 'in_service'])
    ).order_by(QueueEntry.arrival_time.asc()).all()

    tracking = {}
    for entry in active_entries:
        tracking[entry.id] = build_tracking_payload(entry)

    db.session.commit()

    pending_services = PendingService.query.filter_by(
        customer_id=current_user.id
    ).order_by(PendingService.sequence_order.asc()).all()

    if not active_entries and pending_services:
        activate_next_pending_service(current_user.id)
        return redirect(url_for('customer.dashboard'))

    active_service_ids = {e.service_id for e in active_entries}
    pending_service_ids = {p.service_id for p in pending_services}
    blocked_ids = active_service_ids | pending_service_ids

    services = Service.query.filter_by(is_active=True).all()
    available_services = [s for s in services if s.id not in blocked_ids]

    qr_codes = {}
    for entry in active_entries:
        track_url = url_for('customer.track_token', entry_id=entry.id, _external=True)
        qr_codes[entry.id] = generate_qr_code(track_url)

    queue_history = get_queue_history(current_user.id)

    feedback_pending = QueueEntry.query.filter_by(
        customer_id=current_user.id,
        status='completed',
    ).outerjoin(Feedback, QueueEntry.id == Feedback.queue_entry_id).filter(
        Feedback.id.is_(None)
    ).order_by(QueueEntry.service_completion_time.desc()).all()

    submitted_feedbacks = Feedback.query.filter_by(
        customer_id=current_user.id,
    ).order_by(Feedback.created_at.desc()).limit(10).all()

    bank_status = get_bank_status_info()

    return render_template(
        'customer/dashboard.html',
        active_page='dashboard',
        available_services=available_services,
        active_entries=active_entries,
        tracking=tracking,
        pending_services=pending_services,
        qr_codes=qr_codes,
        queue_history=queue_history,
        feedback_pending=feedback_pending,
        submitted_feedbacks=submitted_feedbacks,
        bank_status=bank_status,
    )


@customer_bp.route('/track/<int:entry_id>')
@login_required
@role_required('customer')
def track_token(entry_id):
    """QR code destination — opens the live queue tracking page."""
    entry = QueueEntry.query.filter_by(
        id=entry_id,
        customer_id=current_user.id
    ).first_or_404()

    if entry.deterministic_estimate is None:
        entry.deterministic_estimate = calculate_deterministic_estimate(entry)
        db.session.commit()

    track_data = build_tracking_payload(entry)
    db.session.commit()

    track_url = url_for('customer.track_token', entry_id=entry.id, _external=True)
    qr_code_base64 = generate_qr_code(track_url)

    return render_template(
        'customer/token_details.html',
        active_page='dashboard',
        entry=entry,
        track_data=track_data,
        qr_code_base64=qr_code_base64,
    )


@customer_bp.route('/token-details/<int:entry_id>')
@login_required
@role_required('customer')
def token_details(entry_id):
    return redirect(url_for('customer.track_token', entry_id=entry_id))


@customer_bp.route('/join-queue', methods=['POST'])
@login_required
@role_required('customer')
def join_queue():
    if not is_bank_open():
        bank_status = get_bank_status_info()
        flash(bank_status['message'], 'warning')
        return redirect(url_for('customer.dashboard'))

    service_ids = request.form.getlist('service_ids')
    priority_type = request.form.get('priority_type', 'normal')

    if not service_ids:
        flash('Please select at least one service.', 'warning')
        return redirect(url_for('customer.dashboard'))

    if priority_type not in VALID_PRIORITIES:
        priority_type = 'normal'

    active_service_ids = {
        e.service_id for e in QueueEntry.query.filter_by(
            customer_id=current_user.id
        ).filter(
            QueueEntry.status.in_(['waiting', 'called', 'in_service'])
        ).all()
    }
    pending_service_ids = {
        p.service_id for p in PendingService.query.filter_by(
            customer_id=current_user.id
        ).all()
    }
    blocked_ids = active_service_ids | pending_service_ids

    valid_services = Service.query.filter(
        Service.id.in_([int(s) for s in service_ids]),
        Service.is_active.is_(True)
    ).all()

    if not valid_services:
        flash('Invalid service selection.', 'danger')
        return redirect(url_for('customer.dashboard'))

    # Preserve selection order; skip services already in the customer's queue
    service_map = {s.id: s for s in valid_services}
    ordered_services = [
        service_map[int(sid)] for sid in service_ids
        if int(sid) in service_map and int(sid) not in blocked_ids
    ]

    if not ordered_services:
        flash('You are already in the queue for the selected service(s).', 'warning')
        return redirect(url_for('customer.dashboard'))

    first_service = ordered_services[0]
    new_entry = None
    created_entries = []

    if active_service_ids:
        # Customer already has token(s) — create a separate token per new service
        for service in ordered_services:
            entry = create_queue_entry(current_user.id, service.id, priority_type)
            if entry:
                created_entries.append(entry)
        new_entry = created_entries[0] if created_entries else None
    else:
        new_entry = create_queue_entry(current_user.id, first_service.id, priority_type)
        if new_entry:
            created_entries.append(new_entry)
            for idx, service in enumerate(ordered_services[1:], start=1):
                db.session.add(PendingService(
                    customer_id=current_user.id,
                    service_id=service.id,
                    priority_type=priority_type,
                    sequence_order=idx,
                ))

    if not new_entry:
        if not is_bank_open():
            bank_status = get_bank_status_info()
            flash(bank_status['message'], 'warning')
        else:
            flash('Could not create token. Please try again.', 'danger')
        return redirect(url_for('customer.dashboard'))

    db.session.commit()
    for entry in created_entries:
        broadcast_queue_updates(service_id=entry.service_id)

    skipped = len(service_ids) - len(ordered_services)
    if len(created_entries) > 1:
        tokens = ', '.join(e.token_number for e in created_entries)
        msg = f'You joined the queue! Your tokens: {tokens}.'
    else:
        msg = f'You joined the queue! Your token is {new_entry.token_number}.'
        if len(ordered_services) > 1:
            remaining = ', '.join(s.name for s in ordered_services[1:])
            msg += f' Next up after this: {remaining}.'
    if skipped:
        msg += ' Service(s) already in your queue were skipped.'

    flash(msg, 'success')
    return redirect(url_for('customer.dashboard'))


@customer_bp.route('/cancel-token/<int:entry_id>', methods=['POST'])
@login_required
@role_required('customer')
def cancel_token(entry_id):
    entry = QueueEntry.query.filter_by(
        id=entry_id,
        customer_id=current_user.id
    ).first_or_404()

    success, message = cancel_queue_entry(entry)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('customer.dashboard'))


@customer_bp.route('/feedback/<int:entry_id>', methods=['POST'])
@login_required
@role_required('customer')
def submit_feedback(entry_id):
    entry = QueueEntry.query.filter_by(
        id=entry_id,
        customer_id=current_user.id,
        status='completed'
    ).first_or_404()

    if entry.feedback:
        flash('You already submitted feedback for this visit.', 'info')
        return redirect(url_for('customer.dashboard'))

    try:
        rating = int(request.form.get('rating', 0))
    except (TypeError, ValueError):
        rating = 0

    if rating < 1 or rating > 5:
        flash('Please select a rating between 1 and 5 stars.', 'warning')
        return redirect(url_for('customer.dashboard'))

    comment = (request.form.get('comment') or '').strip()[:500]

    feedback = Feedback(
        queue_entry_id=entry.id,
        customer_id=current_user.id,
        rating=rating,
        comment=comment or None,
    )
    db.session.add(feedback)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash('You already submitted feedback for this visit.', 'info')
        return redirect(url_for('customer.dashboard'))

    flash('Thank you for your feedback!', 'success')
    return redirect(url_for('customer.dashboard'))
