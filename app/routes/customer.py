from flask import Blueprint, render_template
from flask_login import login_required

from app.utils.decorators import role_required

customer_bp = Blueprint('customer', __name__)


@customer_bp.route('/dashboard')
@login_required
@role_required('customer')
def dashboard():
    return render_template('customer/dashboard.html')