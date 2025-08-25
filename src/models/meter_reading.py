from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.user import db

class MeterReading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    staff_name = db.Column(db.String(100), nullable=False)
    staff_number = db.Column(db.String(20), nullable=False)
    itin_coverage = db.Column(db.Float, nullable=False)
    target_coverage = db.Column(db.Float, default=100.0)
    status = db.Column(db.String(20), default='pending')  # pending, complete, delayed, escalated
    reading_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Coverage reasons
    closed_premise = db.Column(db.Integer, default=0)
    meter_not_on_site = db.Column(db.Integer, default=0)
    suspected_misallocated = db.Column(db.Integer, default=0)
    other_reason = db.Column(db.Integer, default=0)
    comments = db.Column(db.Text, nullable=True)
    
    # File uploads
    excel_file_path = db.Column(db.String(255), nullable=True)
    
    # Relationship
    staff = db.relationship('Staff', backref=db.backref('meter_readings', lazy=True))

    def __repr__(self):
        return f'<MeterReading {self.staff_name} - {self.reading_date}>'

    def to_dict(self):
        return {
            'id': self.id,
            'staff_id': self.staff_id,
            'staff_name': self.staff_name,
            'staff_number': self.staff_number,
            'itin_coverage': self.itin_coverage,
            'target_coverage': self.target_coverage,
            'status': self.status,
            'reading_date': self.reading_date.isoformat() if self.reading_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'closed_premise': self.closed_premise,
            'meter_not_on_site': self.meter_not_on_site,
            'suspected_misallocated': self.suspected_misallocated,
            'other_reason': self.other_reason,
            'comments': self.comments,
            'excel_file_path': self.excel_file_path,
            'anomalies': len(self.anomalies) if hasattr(self, 'anomalies') else 0
        }

