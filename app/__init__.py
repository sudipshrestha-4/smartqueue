from flask import Flask
from config import config
from app.extensions import db, login_manager, socketio, migrate


def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions with the app
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(
        app,
        async_mode=app.config['SOCKETIO_ASYNC_MODE'],
        cors_allowed_origins="*"
    )

    # Register Socket.IO event handlers
    from app import sockets  # noqa: F401

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))

    from app import models  # noqa: F401 - ensures models are registered

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.customer import customer_bp
    from app.routes.staff import staff_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(customer_bp, url_prefix='/customer')
    app.register_blueprint(staff_bp, url_prefix='/staff')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    _start_background_jobs(app)

    return app


def _start_background_jobs(app):
    from app.utils.queue_logic import broadcast_queue_updates
    from app.models.service import Service

    def periodic_recalculation():
        with app.app_context():
            while True:
                socketio.sleep(20)  # every 20 seconds
                try:
                    for service in Service.query.all():
                     broadcast_queue_updates(service_id=service.id, notify_staff=False)
   
                except Exception as exc:
                    print(f"[SmartQueue] periodic recalculation error: {exc}")

    socketio.start_background_task(periodic_recalculation)