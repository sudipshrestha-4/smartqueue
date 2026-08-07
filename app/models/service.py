from app.extensions import db


class Service(db.Model):
    __tablename__ = 'services'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    # Used for deterministic estimation and as an ML feature later
    avg_service_duration = db.Column(db.Float, default=10.0)  # in minutes

    is_active = db.Column(db.Boolean, default=True)

    # Per-service daily token counter (resets automatically each business day)
    daily_token_counter = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    counter_reset_date = db.Column(db.Date, nullable=True)

    queue_entries = db.relationship('QueueEntry', backref='service', lazy='dynamic')

    def __repr__(self):
        return f'<Service {self.name}>'
