from datetime import datetime
from app.extensions import db


class QueueEntry(db.Model):
    __tablename__ = 'queue_entries'

    id = db.Column(db.Integer, primary_key=True)
    token_number = db.Column(db.String(20), nullable=False, index=True)

    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    counter_id = db.Column(db.Integer, db.ForeignKey('counters.id'), nullable=True)

    # 'normal' | 'elderly' | 'disabled' | 'pregnant' | 'emergency'
    priority_type = db.Column(db.String(20), default='normal')

    # 'waiting' | 'called' | 'in_service' | 'completed' | 'cancelled' | 'no_show'
    status = db.Column(db.String(20), default='waiting')

    # --- Timestamps used for Waiting Time / Service Duration formulas ---
    arrival_time = db.Column(db.DateTime, default=datetime.utcnow)
    service_start_time = db.Column(db.DateTime, nullable=True)
    service_completion_time = db.Column(db.DateTime, nullable=True)

    # --- Wait-time estimates ---
    deterministic_estimate = db.Column(db.Float, nullable=True)  # minutes
    ml_predicted_wait = db.Column(db.Float, nullable=True)       # minutes
    actual_wait_time = db.Column(db.Float, nullable=True)        # minutes, filled once served

    def calculate_actual_wait(self):
        """Waiting Time = Service Start Time - Customer Arrival Time"""
        if self.service_start_time and self.arrival_time:
            delta = self.service_start_time - self.arrival_time
            self.actual_wait_time = round(delta.total_seconds() / 60, 2)
        return self.actual_wait_time

    def calculate_service_duration(self):
        """Service Duration = Service Completion Time - Service Start Time"""
        if self.service_completion_time and self.service_start_time:
            delta = self.service_completion_time - self.service_start_time
            return round(delta.total_seconds() / 60, 2)
        return None

    def __repr__(self):
        return f'<QueueEntry {self.token_number} - {self.status}>'