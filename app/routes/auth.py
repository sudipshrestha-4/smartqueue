from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db
from app.forms.auth_forms import LoginForm, RegisterForm
from app.models.user import User

auth_bp = Blueprint('auth', __name__)


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


def _dashboard_for(role):
    """Maps a user role to their dashboard endpoint."""
    mapping = {
        'customer': 'customer.dashboard',
        'staff': 'staff.dashboard',
        'admin': 'admin.dashboard'
    }
    return mapping.get(role, 'main.index')