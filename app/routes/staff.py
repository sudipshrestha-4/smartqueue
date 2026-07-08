from flask import Blueprint, render_template
from flask_login import login_required

from app.utils.decorators import role_required

staff_bp = Blueprint('staff', __name__)


@staff_bp.route('/dashboard')
@login_required
@role_required('staff')
def dashboard():
    return render_template('staff/dashboard.html')