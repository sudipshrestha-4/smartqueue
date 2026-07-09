from flask_socketio import join_room
from flask_login import current_user
from app.extensions import socketio


@socketio.on('connect')
def handle_connect():
    """Automatically joins the right room the moment a user's browser connects."""
    if current_user.is_authenticated:
        if current_user.role == 'customer':
            join_room(f'customer_{current_user.id}')
        elif current_user.role in ('staff', 'admin'):
            join_room('staff_admin_room')


@socketio.on('disconnect')
def handle_disconnect():
    pass  # Flask-SocketIO cleans up room membership automatically