from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime

from app.extensions import db, socketio
from app.utils.decorators import role_required
from app.utils.queue_logic import (
    broadcast_queue_updates, get_ordered_queue, get_next_customer,
    recalculate_avg_service_duration
)
from app.models.queue_entry import QueueEntry
from app.models.counter import Counter

staff_bp = Blueprint('staff', __name__)


@staff_bp.route('/dashboard')
@login_required
@role_required('staff')
def dashboard():
    counter = current_user.counter  # via assigned_counter_id relationship
    queue = get_ordered_queue()
    called_entry = QueueEntry.query.filter_by(
        counter_id=counter.id if counter else None, status='called'
    ).first()

    return render_template('staff/dashboard.html', queue=queue, counter=counter, called_entry=called_entry)


@staff_bp.route('/call-next', methods=['POST'])
@login_required
@role_required('staff')
def call_next():
    counter = current_user.counter
    if not counter:
        flash('You are not assigned to a counter. Contact an admin.', 'danger')
        return redirect(url_for('staff.dashboard'))

    next_entry = get_next_customer(counter.id)
    if not next_entry:
        flash('No customers waiting.', 'info')
        return redirect(url_for('staff.dashboard'))

    next_entry.status = 'called'
    next_entry.counter_id = counter.id
    next_entry.service_start_time = datetime.utcnow()
    db.session.commit()

    next_entry.calculate_actual_wait()
    db.session.commit()

    broadcast_queue_updates(service_id=next_entry.service_id)

    # Notify customer in real time
    socketio.emit('customer_called', {
        'token': next_entry.token_number,
        'counter': counter.counter_number
    }, room=f'customer_{next_entry.customer_id}')

    # Notify the public counter screen
    socketio.emit('counter_called', {
        'token': next_entry.token_number,
        'counter': counter.counter_number
    }, room='display_room')

    flash(f'Called token {next_entry.token_number}.', 'success')
    return redirect(url_for('staff.dashboard'))


@staff_bp.route('/complete-service/<int:entry_id>', methods=['POST'])
@login_required
@role_required('staff')
def complete_service(entry_id):
    entry = QueueEntry.query.get_or_404(entry_id)
    entry.status = 'completed'
    entry.service_completion_time = datetime.utcnow()
    db.session.commit()

    broadcast_queue_updates(service_id=entry.service_id)

    # Let the customer's page know their token is done so it can refresh
    # and offer to join that same service's queue again if they want.
    socketio.emit('service_completed', {
        'token': entry.token_number,
        'service_name': entry.service.name
    }, room=f'customer_{entry.customer_id}')

    socketio.emit('display_refresh', {}, room='display_room')

    flash(f'Token {entry.token_number} marked as completed.', 'success')
    return redirect(url_for('staff.dashboard'))


@staff_bp.route('/mark-no-show/<int:entry_id>', methods=['POST'])
@login_required
@role_required('staff')
def mark_no_show(entry_id):
    entry = QueueEntry.query.get_or_404(entry_id)
    entry.status = 'no_show'
    db.session.commit()
    recalculate_avg_service_duration(entry.service_id) 

    broadcast_queue_updates(service_id=entry.service_id)

    socketio.emit('service_completed', {
        'token': entry.token_number,
        'service_name': entry.service.name
    }, room=f'customer_{entry.customer_id}')

    socketio.emit('display_refresh', {}, room='display_room')

    flash(f'Token {entry.token_number} marked as no-show.', 'warning')
    return redirect(url_for('staff.dashboard'))