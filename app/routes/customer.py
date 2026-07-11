from flask import Blueprint, render_template, redirect, url_for, flash, request
from sqlalchemy.exc import IntegrityError
from flask_login import login_required, current_user
from datetime import datetime

from app.extensions import db
from app.utils.decorators import role_required
from app.utils.queue_logic import broadcast_queue_updates, calculate_deterministic_estimate
from app.utils.token_generator import generate_token_number
from app.utils.qr_generator import generate_qr_code
from app.models.service import Service
from app.models.queue_entry import QueueEntry

customer_bp = Blueprint('customer', __name__)


@customer_bp.route('/dashboard')
@login_required
@role_required('customer')
def dashboard():
    # All active tokens this customer currently holds, across any service
    active_entries = QueueEntry.query.filter_by(
        customer_id=current_user.id
    ).filter(
        QueueEntry.status.in_(['waiting', 'called', 'in_service'])
    ).order_by(QueueEntry.arrival_time.asc()).all()

    for entry in active_entries:
        if entry.deterministic_estimate is None:
            entry.deterministic_estimate = calculate_deterministic_estimate(entry)

    db.session.commit()

    # A QR code per active entry, keyed by entry id
    qr_codes = {
        entry.id: generate_qr_code(entry.token_number)
        for entry in active_entries
    }

    # Only offer services the customer hasn't already joined
    already_joined_service_ids = {entry.service_id for entry in active_entries}
    services = Service.query.filter_by(is_active=True).all()
    available_services = [s for s in services if s.id not in already_joined_service_ids]

    return render_template(
        'customer/dashboard.html',
        available_services=available_services,
        active_entries=active_entries,
        qr_codes=qr_codes
    )


@customer_bp.route('/token-details/<int:entry_id>')
@login_required
@role_required('customer')
def token_details(entry_id):
    entry = QueueEntry.query.filter_by(
        id=entry_id,
        customer_id=current_user.id
    ).first_or_404()

    if entry.deterministic_estimate is None:
        entry.deterministic_estimate = calculate_deterministic_estimate(entry)
        db.session.commit()

    qr_code_base64 = generate_qr_code(entry.token_number)
    return render_template(
        'customer/token_details.html',
        entry=entry,
        qr_code_base64=qr_code_base64
    )


VALID_PRIORITIES = {'normal', 'elderly', 'disabled', 'pregnant', 'emergency'}


@customer_bp.route('/join-queue', methods=['POST'])
@login_required
@role_required('customer')
def join_queue():
    service_id = request.form.get('service_id')
    priority_type = request.form.get('priority_type', 'normal')

    if not service_id:
        flash('Please select a service.', 'warning')
        return redirect(url_for('customer.dashboard'))

    if priority_type not in VALID_PRIORITIES:
        priority_type = 'normal'

    # Prevent joining the SAME service twice while already active in it.
    # (Customers may hold active tokens for multiple different services.)
    existing = QueueEntry.query.filter_by(
        customer_id=current_user.id,
        service_id=service_id
    ).filter(
        QueueEntry.status.in_(['waiting', 'called', 'in_service'])
    ).first()

    if existing:
        flash('You already have an active token for that service.', 'info')
        return redirect(url_for('customer.dashboard'))

    prefix = 'E' if priority_type == 'emergency' else ('P' if priority_type != 'normal' else 'N')
    token_number = generate_token_number(prefix=prefix)

    new_entry = QueueEntry(
        token_number=token_number,
        customer_id=current_user.id,
        service_id=service_id,
        priority_type=priority_type,
        status='waiting',
        arrival_time=datetime.utcnow()
    )
    db.session.add(new_entry)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash('That was a close call - please try joining again.', 'warning')
        return redirect(url_for('customer.dashboard'))

    new_entry.deterministic_estimate = calculate_deterministic_estimate(new_entry)
    db.session.commit()

    broadcast_queue_updates(service_id=new_entry.service_id)

    flash(f'You joined the queue! Your token is {token_number}.', 'success')
    return redirect(url_for('customer.dashboard'))