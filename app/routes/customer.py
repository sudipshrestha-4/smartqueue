from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime

from app.extensions import db
from app.utils.decorators import role_required
from app.utils.token_generator import generate_token_number
from app.utils.qr_generator import generate_qr_code
from app.models.service import Service
from app.models.queue_entry import QueueEntry

customer_bp = Blueprint('customer', __name__)


@customer_bp.route('/dashboard')
@login_required
@role_required('customer')
def dashboard():
    services = Service.query.filter_by(is_active=True).all()

    # Show the customer's active (not yet completed) queue entry, if any
    active_entry = QueueEntry.query.filter_by(
        customer_id=current_user.id
    ).filter(
        QueueEntry.status.in_(['waiting', 'called', 'in_service'])
    ).first()

    qr_code_base64 = None
    if active_entry:
        qr_code_base64 = generate_qr_code(active_entry.token_number)

    return render_template(
        'customer/dashboard.html',
        services=services,
        active_entry=active_entry,
        qr_code_base64=qr_code_base64
    )


@customer_bp.route('/join-queue', methods=['POST'])
@login_required
@role_required('customer')
def join_queue():
    service_id = request.form.get('service_id')

    if not service_id:
        flash('Please select a service.', 'warning')
        return redirect(url_for('customer.dashboard'))

    # Prevent joining twice while already in an active queue entry
    existing = QueueEntry.query.filter_by(
        customer_id=current_user.id
    ).filter(
        QueueEntry.status.in_(['waiting', 'called', 'in_service'])
    ).first()

    if existing:
        flash('You already have an active token in the queue.', 'info')
        return redirect(url_for('customer.dashboard'))

    token_number = generate_token_number()

    new_entry = QueueEntry(
        token_number=token_number,
        customer_id=current_user.id,
        service_id=service_id,
        priority_type='normal',
        status='waiting',
        arrival_time=datetime.utcnow()
    )
    db.session.add(new_entry)
    db.session.commit()

    flash(f'You joined the queue! Your token is {token_number}.', 'success')
    return redirect(url_for('customer.dashboard'))