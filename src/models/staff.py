from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.user import db

class Staff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    staff_number = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    pin = db.Column(db.String(10), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='reader')  # reader, supervisor, engineer
    email = db.Column(db.String(120), nullable=True)
    security_question = db.Column(db.String(200), nullable=True)
    security_answer = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<Staff {self.staff_number}: {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'staff_number': self.staff_number,
            'name': self.name,
            'role': self.role,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active
        }

    def check_pin(self, pin):
        # PIN should be the first 4 digits of the staff number
        expected_pin = self.staff_number[:4]
        return pin == expected_pin

    def set_pin(self, pin):
        # For this system, PIN is automatically the first 4 digits of staff number
        # This method is kept for compatibility but doesn't change the PIN
        pass

    @property
    def calculated_pin(self):
        """Returns the calculated PIN (first 4 digits of staff number)"""
        return self.staff_number[:4]

