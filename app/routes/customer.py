from flask import Blueprint, render_template

customer_bp = Blueprint('customer', __name__)


@customer_bp.route('/dashboard')
def dashboard():
    return render_template('customer/dashboard.html')