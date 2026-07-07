from flask import Blueprint, render_template

staff_bp = Blueprint('staff', __name__)


@staff_bp.route('/dashboard')
def dashboard():
    return render_template('staff/dashboard.html')