from app.extensions import db


class Counter(db.Model):
    __tablename__ = 'counters'

    id = db.Column(db.Integer, primary_key=True)
    counter_number = db.Column(db.Integer, unique=True, nullable=False)

    # 'active' | 'inactive' | 'on_break'
    status = db.Column(db.String(20), default='active')

    staff = db.relationship('User', backref='counter', uselist=False,
                             foreign_keys='User.assigned_counter_id')
    queue_entries = db.relationship('QueueEntry', backref='counter', lazy='dynamic')

    def __repr__(self):
        return f'<Counter #{self.counter_number} ({self.status})>'