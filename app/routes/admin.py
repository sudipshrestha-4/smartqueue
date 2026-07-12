from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required

from app.extensions import db
from app.utils.decorators import role_required
from app.models.counter import Counter
from app.models.user import User
from app.models.service import Service
from app.models.queue_entry import QueueEntry

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/dashboard')
@login_required
@role_required('admin')
def dashboard():
    counters = Counter.query.order_by(Counter.counter_number.asc()).all()
    staff_members = User.query.filter_by(role='staff').order_by(User.name.asc()).all()
    services = Service.query.order_by(Service.name.asc()).all()

    today = date.today()

    waiting_count = QueueEntry.query.filter_by(status='waiting').count()
    in_service_count = QueueEntry.query.filter_by(status='in_service').count()
    completed_today = QueueEntry.query.filter(
        QueueEntry.status == 'completed',
        db.func.date(QueueEntry.arrival_time) == today
    ).count()
    no_show_today = QueueEntry.query.filter(
        QueueEntry.status == 'no_show',
        db.func.date(QueueEntry.arrival_time) == today
    ).count()
    active_counters_count = Counter.query.filter_by(status='active').count()

    stats = {
        'waiting_count': waiting_count,
        'in_service_count': in_service_count,
        'completed_today': completed_today,
        'no_show_today': no_show_today,
        'active_counters_count': active_counters_count,
        'total_counters': len(counters),
        'total_staff': len(staff_members),
    }

    return render_template(
        'admin/dashboard.html',
        counters=counters,
        staff_members=staff_members,
        services=services,
        stats=stats
    )


@admin_bp.route('/counters/add', methods=['POST'])
@login_required
@role_required('admin')
def add_counter():
    next_number = (db.session.query(db.func.max(Counter.counter_number)).scalar() or 0) + 1
    counter = Counter(counter_number=next_number, status='active')
    db.session.add(counter)
    db.session.commit()
    flash(f'Counter #{next_number} added.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/counters/<int:counter_id>/toggle', methods=['POST'])
@login_required
@role_required('admin')
def toggle_counter(counter_id):
    counter = Counter.query.get_or_404(counter_id)
    counter.status = 'inactive' if counter.status == 'active' else 'active'
    db.session.commit()
    flash(f'Counter #{counter.counter_number} is now {counter.status}.', 'info')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/counters/<int:counter_id>/assign-service', methods=['POST'])
@login_required
@role_required('admin')
def assign_service(counter_id):
    counter = Counter.query.get_or_404(counter_id)
    service_id = request.form.get('service_id')

    counter.service_id = int(service_id) if service_id else None
    db.session.commit()

    if service_id:
        flash(f'Counter #{counter.counter_number} now handles {counter.service.name}.', 'success')
    else:
        flash(f'Counter #{counter.counter_number} unassigned from any service.', 'info')

    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/staff/<int:staff_id>/assign-counter', methods=['POST'])
@login_required
@role_required('admin')
def assign_counter(staff_id):
    staff = User.query.filter_by(id=staff_id, role='staff').first_or_404()
    counter_id = request.form.get('counter_id')

    staff.assigned_counter_id = int(counter_id) if counter_id else None
    db.session.commit()

    if counter_id:
        flash(f'{staff.name} assigned to counter.', 'success')
    else:
        flash(f'{staff.name} unassigned from their counter.', 'info')

    return redirect(url_for('admin.dashboard'))