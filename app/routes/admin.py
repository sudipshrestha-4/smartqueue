from datetime import datetime, date, timedelta, time as dt_time
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app.forms.auth_forms import StaffForm, AdminStaffPasswordForm
import csv
import io

from app.extensions import db
from app.utils.decorators import role_required
from app.utils.queue_logic import recalculate_all_service_durations, ACTIVE_STATUSES
from app.utils.token_generator import get_bank_settings, get_bank_status_info
from app.models.counter import Counter
from app.models.user import User
from app.models.service import Service
from app.models.queue_entry import QueueEntry
from app.models.feedback import Feedback
from app.models.audit_log import TokenResetLog

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/analytics/export')
@login_required
@role_required('admin')
def export_csv():
    days = request.args.get('days', 7, type=int)
    if days not in (7, 30, 90):
        days = 7
    start_date = date.today() - timedelta(days=days - 1)
    start_dt = datetime.combine(start_date, datetime.min.time())

    entries = QueueEntry.query.filter(QueueEntry.arrival_time >= start_dt).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Token', 'Service', 'Priority', 'Status', 'Arrival Time',
        'Service Start', 'Service Completion', 'Estimated Wait (min)',
        'Actual Wait (min)'
    ])
    for e in entries:
        writer.writerow([
            e.token_number,
            e.service.name if e.service else '',
            e.priority_type,
            e.status,
            e.arrival_time.strftime('%Y-%m-%d %H:%M') if e.arrival_time else '',
            e.service_start_time.strftime('%Y-%m-%d %H:%M') if e.service_start_time else '',
            e.service_completion_time.strftime('%Y-%m-%d %H:%M') if e.service_completion_time else '',
            e.deterministic_estimate if e.deterministic_estimate is not None else '',
            e.actual_wait_time if e.actual_wait_time is not None else '',
        ])

    csv_data = output.getvalue()
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=smartqueue_report_{days}days.csv'}
    )




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

    staff_form = StaffForm()
    staff_password_form = AdminStaffPasswordForm()

    feedback_total = Feedback.query.count()
    feedback_avg = db.session.query(db.func.avg(Feedback.rating)).scalar()
    feedback_avg = round(float(feedback_avg), 1) if feedback_avg is not None else None
    feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).limit(10).all()

    active_queue_count = QueueEntry.query.filter(
        QueueEntry.status.in_(ACTIVE_STATUSES)
    ).count()
    reset_logs = TokenResetLog.query.order_by(TokenResetLog.reset_at.desc()).limit(10).all()
    bank_settings = get_bank_settings()
    bank_status = get_bank_status_info(bank_settings)

    return render_template(
        'admin/dashboard.html',
        active_page='dashboard',
        counters=counters,
        staff_members=staff_members,
        services=services,
        stats=stats,
        staff_form=staff_form,
        staff_password_form=staff_password_form,
        feedbacks=feedbacks,
        feedback_total=feedback_total,
        feedback_avg=feedback_avg,
        active_queue_count=active_queue_count,
        reset_logs=reset_logs,
        bank_settings=bank_settings,
        bank_status=bank_status,
    )


@admin_bp.route('/feedback')
@login_required
@role_required('admin')
def feedback():
    feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).all()
    total_count = len(feedbacks)
    avg_rating = round(sum(f.rating for f in feedbacks) / total_count, 1) if total_count else None

    rating_counts = {i: 0 for i in range(1, 6)}
    for fb in feedbacks:
        rating_counts[fb.rating] = rating_counts.get(fb.rating, 0) + 1

    return render_template(
        'admin/feedback.html',
        active_page='feedback',
        feedbacks=feedbacks,
        total_count=total_count,
        avg_rating=avg_rating,
        rating_counts=rating_counts,
    )


@admin_bp.route('/staff/add', methods=['POST'])
@login_required
@role_required('admin')
def add_staff():
    form = StaffForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if existing_user:
            flash('An account with this email already exists.', 'warning')
            return redirect(url_for('admin.dashboard'))

        existing_phone = User.query.filter_by(phone=form.phone.data.strip()).first()
        if existing_phone:
            flash('An account with this phone number already exists.', 'warning')
            return redirect(url_for('admin.dashboard'))

        staff = User(
            name=form.name.data.strip(),
            email=form.email.data.lower().strip(),
            phone=form.phone.data.strip(),
            password_hash=generate_password_hash(form.password.data),
            role='staff',
            is_active=True
        )
        db.session.add(staff)
        db.session.commit()
        flash(f'Staff account created for {staff.name}.', 'success')
    else:
        for field_name, errors in form.errors.items():
            label = getattr(form, field_name).label.text
            for error in errors:
                flash(f'{label}: {error}', 'danger')

    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/staff/<int:staff_id>/remove', methods=['POST'])
@login_required
@role_required('admin')
def remove_staff(staff_id):
    staff = User.query.filter_by(id=staff_id, role='staff').first_or_404()
    name = staff.name
    db.session.delete(staff)
    db.session.commit()
    flash(f'Removed staff account for {name}.', 'info')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/staff/<int:staff_id>/change-password', methods=['POST'])
@login_required
@role_required('admin')
def change_staff_password(staff_id):
    staff = User.query.filter_by(id=staff_id, role='staff').first_or_404()
    form = AdminStaffPasswordForm()
    if form.validate_on_submit():
        staff.password_hash = generate_password_hash(form.password.data)
        db.session.commit()
        flash(f'Password updated for {staff.name}.', 'success')
    else:
        for field_name, errors in form.errors.items():
            label = getattr(form, field_name).label.text
            for error in errors:
                flash(f'{label}: {error}', 'danger')

    return redirect(url_for('admin.dashboard'))


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


@admin_bp.route('/analytics')
@login_required
@role_required('admin')
def analytics():
    days = request.args.get('days', 7, type=int)
    if days not in (7, 30, 90):
        days = 7
    start_date = date.today() - timedelta(days=days - 1)
    start_dt = datetime.combine(start_date, datetime.min.time())

    entries = QueueEntry.query.filter(QueueEntry.arrival_time >= start_dt).all()

    daily_map = {}
    for e in entries:
        key = e.arrival_time.date()
        daily_map[key] = daily_map.get(key, 0) + 1
    all_days = [start_date + timedelta(days=i) for i in range(days)]
    daily_labels = [d.strftime('%b %d') for d in all_days]
    daily_values = [daily_map.get(d, 0) for d in all_days]

    hourly_map = {}
    for e in entries:
        h = e.arrival_time.hour
        hourly_map[h] = hourly_map.get(h, 0) + 1
    hourly_labels = [f'{h}:00' for h in range(24)]
    hourly_values = [hourly_map.get(h, 0) for h in range(24)]

    dow_names = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    dow_map = {}
    for e in entries:
        idx = (e.arrival_time.weekday() + 1) % 7
        dow_map[idx] = dow_map.get(idx, 0) + 1
    dow_values = [dow_map.get(i, 0) for i in range(7)]

    priority_labels = ['normal', 'elderly', 'disabled', 'pregnant', 'emergency']
    priority_map = {}
    for e in entries:
        priority_map[e.priority_type] = priority_map.get(e.priority_type, 0) + 1
    priority_values = [priority_map.get(p, 0) for p in priority_labels]

    service_stats = []
    for service in Service.query.order_by(Service.name).all():
        service_entries = [e for e in entries if e.service_id == service.id]
        total = len(service_entries)
        completed = sum(1 for e in service_entries if e.status == 'completed')
        no_show = sum(1 for e in service_entries if e.status == 'no_show')

        actual_waits = [e.actual_wait_time for e in service_entries if e.actual_wait_time is not None]
        est_waits = [e.deterministic_estimate for e in service_entries if e.deterministic_estimate is not None]

        service_stats.append({
            'name': service.name,
            'total': total,
            'completed': completed,
            'no_show': no_show,
            'no_show_rate': round((no_show / total * 100), 1) if total else 0,
            'avg_actual_wait': round(sum(actual_waits) / len(actual_waits), 1) if actual_waits else None,
            'avg_estimated_wait': round(sum(est_waits) / len(est_waits), 1) if est_waits else None,
        })

    counter_stats = []
    for counter in Counter.query.order_by(Counter.counter_number).all():
        served = sum(
            1 for e in entries
            if e.counter_id == counter.id and e.status == 'completed'
        )
        counter_stats.append({
            'number': counter.counter_number,
            'service': counter.service.name if counter.service else 'Unassigned',
            'status': counter.status,
            'served': served,
        })

    total_entries = len(entries)
    total_completed = sum(1 for e in entries if e.status == 'completed')
    total_no_show = sum(1 for e in entries if e.status == 'no_show')
    all_actual_waits = [e.actual_wait_time for e in entries if e.actual_wait_time is not None]

    summary = {
        'total_entries': total_entries,
        'total_completed': total_completed,
        'total_no_show': total_no_show,
        'no_show_rate': round((total_no_show / total_entries * 100), 1) if total_entries else 0,
        'overall_avg_wait': round(sum(all_actual_waits) / len(all_actual_waits), 1) if all_actual_waits else None,
    }

    return render_template(
        'admin/analytics.html',
        active_page='analytics',
        days=days,
        daily_labels=daily_labels, daily_values=daily_values,
        hourly_labels=hourly_labels, hourly_values=hourly_values,
        dow_labels=dow_names, dow_values=dow_values,
        priority_labels=priority_labels, priority_values=priority_values,
        service_stats=service_stats,
        counter_stats=counter_stats,
        summary=summary
    )


@admin_bp.route('/recalculate-durations', methods=['POST'])
@login_required
@role_required('admin')
def recalculate_durations():
    recalculate_all_service_durations()
    flash('Service durations recalculated from historical data.', 'success')
    return redirect(url_for('admin.dashboard'))


def _parse_time_field(value, field_label):
    if not value:
        return None, f'{field_label} is required.'
    try:
        parts = value.split(':')
        if len(parts) < 2:
            raise ValueError
        hour = int(parts[0])
        minute = int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
        return dt_time(hour, minute), None
    except (TypeError, ValueError):
        return None, f'{field_label} must be a valid time.'


@admin_bp.route('/operating-hours', methods=['POST'])
@login_required
@role_required('admin')
def update_operating_hours():
    open_time, open_err = _parse_time_field(request.form.get('open_time'), 'Opening time')
    close_time, close_err = _parse_time_field(request.form.get('close_time'), 'Closing time')

    for err in (open_err, close_err):
        if err:
            flash(err, 'danger')
            return redirect(url_for('admin.dashboard'))

    if open_time == close_time:
        flash('Opening and closing times cannot be the same.', 'danger')
        return redirect(url_for('admin.dashboard'))

    settings = get_bank_settings()
    settings.open_time = open_time
    settings.close_time = close_time
    db.session.commit()
    flash('Operating hours updated.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/bank-status', methods=['POST'])
@login_required
@role_required('admin')
def set_bank_status():
    status = request.form.get('status', 'auto')
    if status not in ('auto', 'open', 'closed'):
        flash('Invalid bank status selection.', 'danger')
        return redirect(url_for('admin.dashboard'))

    settings = get_bank_settings()
    settings.manual_override = None if status == 'auto' else status
    db.session.commit()

    if status == 'auto':
        flash('Bank status set to automatic (follows operating hours).', 'info')
    elif status == 'open':
        flash('Bank manually opened. Customers can generate tokens regardless of schedule.', 'success')
    else:
        flash('Bank manually closed. Token generation is disabled until reopened.', 'warning')

    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/reset-token-counters', methods=['POST'])
@login_required
@role_required('admin')
def reset_token_counters():
    active_count = QueueEntry.query.filter(
        QueueEntry.status.in_(ACTIVE_STATUSES)
    ).count()

    if active_count > 0:
        flash(
            f'Cannot reset token counters: {active_count} queue '
            f'entr{"y is" if active_count == 1 else "ies are"} still '
            f'Waiting, Called, or Serving. Clear the active queue first.',
            'danger'
        )
        return redirect(url_for('admin.dashboard'))

    services = Service.query.with_for_update().all()
    for service in services:
        service.daily_token_counter = 0
        service.counter_reset_date = None

    log = TokenResetLog(
        admin_id=current_user.id,
        admin_name=current_user.name,
        reset_at=datetime.utcnow(),
        counters_reset=len(services)
    )
    db.session.add(log)
    db.session.commit()

    flash(
        f'Token counters reset for {len(services)} service(s). '
        f'Next token for each starts from 1.',
        'success'
    )
    return redirect(url_for('admin.dashboard'))