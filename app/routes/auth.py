import os
import secrets
from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from app.extensions import db
from app.forms.auth_forms import (
    LoginForm, RegisterForm, ForgotPasswordForm,
    ResetPasswordForm, ChangePasswordForm, EditProfileForm
)
from app.models.user import User

auth_bp = Blueprint('auth', __name__)

ALLOWED_PHOTO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}


def _dashboard_for(role):
    mapping = {
        'customer': 'customer.dashboard',
        'staff': 'staff.dashboard',
        'admin': 'admin.dashboard'
    }
    return mapping.get(role, 'main.index')


def _portal_base(role):
    mapping = {
        'admin': 'admin/base.html',
        'staff': 'staff/base.html',
        'customer': 'customer/base.html',
    }
    return mapping.get(role, 'base.html')


def _role_label(role):
    mapping = {
        'admin': 'Administrator',
        'staff': 'Staff Member',
        'customer': 'Customer',
    }
    return mapping.get(role, role.title())


def _profile_context(user):
    """Shared template context for profile pages."""
    from app.models.queue_entry import QueueEntry

    ctx = {
        'user': user,
        'active_page': 'profile',
        'base_template': _portal_base(user.role),
        'dashboard_url': url_for(_dashboard_for(user.role)),
        'role_label': _role_label(user.role),
    }

    if user.role == 'customer':
        ctx['total_visits'] = QueueEntry.query.filter_by(customer_id=user.id).count()
        ctx['completed_visits'] = QueueEntry.query.filter_by(
            customer_id=user.id, status='completed'
        ).count()
    elif user.role == 'staff':
        ctx['counter'] = user.counter

    return ctx


def _allowed_photo(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_PHOTO_EXTENSIONS


def _profile_upload_dir():
    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'profiles')
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(_dashboard_for(current_user.role)))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()

        if user and check_password_hash(user.password_hash, form.password.data):
            if not user.is_active:
                flash('This account has been deactivated. Contact an admin.', 'danger')
                return redirect(url_for('auth.login'))

            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user)
            flash(f'Welcome back, {user.name}!', 'success')

            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for(_dashboard_for(user.role)))

        flash('Invalid email or password.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for(_dashboard_for(current_user.role)))

    form = RegisterForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if existing_user:
            flash('An account with this email already exists.', 'warning')
            return redirect(url_for('auth.register'))

        existing_phone = User.query.filter_by(phone=form.phone.data.strip()).first()
        if existing_phone:
            flash('An account with this phone number already exists.', 'warning')
            return redirect(url_for('auth.register'))

        new_user = User(
            name=form.name.data.strip(),
            email=form.email.data.lower().strip(),
            phone=form.phone.data.strip(),
            password_hash=generate_password_hash(form.password.data),
            role='customer',
            is_active=True
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully. Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for(_dashboard_for(current_user.role)))

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = User.query.filter_by(email=email).first()

        if not user:
            flash('No account found with that email address.', 'danger')
            return redirect(url_for('auth.forgot_password'))

        if not user.is_active:
            flash('This account has been deactivated. Contact an admin.', 'danger')
            return redirect(url_for('auth.forgot_password'))

        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        db.session.commit()

        reset_url = url_for('auth.reset_password', token=token, _external=True)
        flash(f'Password reset link generated. Use this link within 1 hour: {reset_url}', 'info')

    return render_template('auth/forgot_password.html', form=form)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for(_dashboard_for(current_user.role)))

    user = User.query.filter_by(reset_token=token).first()
    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
        flash('Invalid or expired reset link. Please request a new one.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.password_hash = generate_password_hash(form.password.data)
        user.reset_token = None
        user.reset_token_expires = None
        db.session.commit()
        flash('Your password has been reset. Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', form=form, token=token)


@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html', **_profile_context(current_user))


@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(obj=current_user)

    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        existing = User.query.filter(User.email == email, User.id != current_user.id).first()
        if existing:
            flash('That email is already in use by another account.', 'warning')
            return redirect(url_for('auth.edit_profile'))

        phone = form.phone.data.strip()
        existing_phone = User.query.filter(User.phone == phone, User.id != current_user.id).first()
        if existing_phone:
            flash('That phone number is already in use by another account.', 'warning')
            return redirect(url_for('auth.edit_profile'))

        current_user.name = form.name.data.strip()
        current_user.email = email
        current_user.phone = phone

        photo = request.files.get('profile_photo')
        if photo and photo.filename:
            if not _allowed_photo(photo.filename):
                flash('Profile photo must be PNG, JPG, JPEG, or WEBP.', 'warning')
                return redirect(url_for('auth.edit_profile'))

            filename = secure_filename(f'user_{current_user.id}_{photo.filename}')
            photo.save(os.path.join(_profile_upload_dir(), filename))
            current_user.profile_photo = filename

        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('auth.profile'))

    return render_template(
        'auth/edit_profile.html',
        form=form,
        **_profile_context(current_user),
    )


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not check_password_hash(current_user.password_hash, form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('auth.change_password'))

        current_user.password_hash = generate_password_hash(form.new_password.data)
        db.session.commit()
        flash('Password changed successfully.', 'success')
        return redirect(url_for('auth.profile'))

    return render_template(
        'auth/change_password.html',
        form=form,
        **_profile_context(current_user),
    )
