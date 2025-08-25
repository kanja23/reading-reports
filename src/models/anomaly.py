from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.user import db

class Anomaly(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)  # faulty_meters, power_theft, rebilling_issues, etc.
    location = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    status = db.Column(db.String(20), default='new')  # new, pending, in_progress, escalated, resolved
    
    # Staff information
    reported_by_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    reported_by_name = db.Column(db.String(100), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=True)
    assigned_to_name = db.Column(db.String(100), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    escalated_at = db.Column(db.DateTime, nullable=True)
    
    # Escalation tracking
    days_open = db.Column(db.Integer, default=0)
    escalation_sent = db.Column(db.Boolean, default=False)
    escalation_email_sent_at = db.Column(db.DateTime, nullable=True)
    
    # Related meter reading
    meter_reading_id = db.Column(db.Integer, db.ForeignKey('meter_reading.id'), nullable=True)
    
    # Relationships
    reported_by = db.relationship('Staff', foreign_keys=[reported_by_id], backref=db.backref('reported_anomalies', lazy=True))
    assigned_to = db.relationship('Staff', foreign_keys=[assigned_to_id], backref=db.backref('assigned_anomalies', lazy=True))
    meter_reading = db.relationship('MeterReading', backref=db.backref('anomalies', lazy=True))

    def __repr__(self):
        return f'<Anomaly {self.type} - {self.location}>'

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'location': self.location,
            'description': self.description,
            'priority': self.priority,
            'status': self.status,
            'reported_by_id': self.reported_by_id,
            'reported_by_name': self.reported_by_name,
            'assigned_to_id': self.assigned_to_id,
            'assigned_to_name': self.assigned_to_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'escalated_at': self.escalated_at.isoformat() if self.escalated_at else None,
            'days_open': self.days_open,
            'escalation_sent': self.escalation_sent,
            'escalation_email_sent_at': self.escalation_email_sent_at.isoformat() if self.escalation_email_sent_at else None,
            'meter_reading_id': self.meter_reading_id
        }

    def calculate_days_open(self):
        """Calculate how many days the anomaly has been open"""
        if self.resolved_at:
            return (self.resolved_at - self.created_at).days
        else:
            return (datetime.utcnow() - self.created_at).days

    def should_escalate(self):
        """Check if anomaly should be escalated (4+ days old and not escalated)"""
        return self.calculate_days_open() >= 4 and not self.escalation_sent and self.status != 'resolved'

