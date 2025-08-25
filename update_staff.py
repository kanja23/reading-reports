#!/usr/bin/env python3
"""
Script to update staff database with new staff members
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.models.user import db
from src.models.staff import Staff
from src.main import app

def update_staff_database():
    with app.app_context():
        # Clear existing staff
        Staff.query.delete()
        
        # Add new staff members with their numbers
        staff_members = [
            {'staff_number': '85891', 'name': 'User', 'role': 'reader'},
            {'staff_number': '80909', 'name': 'Omweri', 'role': 'reader'},
            {'staff_number': '86002', 'name': 'Samwel', 'role': 'reader'},
            {'staff_number': '53050', 'name': 'Mackenzie', 'role': 'supervisor'},
            {'staff_number': '85915', 'name': 'Moenga', 'role': 'reader'},
        ]
        
        for member in staff_members:
            # PIN is automatically calculated as first 4 digits of staff number
            staff = Staff(
                staff_number=member['staff_number'],
                name=member['name'],
                role=member['role'],
                pin=member['staff_number'][:4],  # Store for compatibility, but check_pin uses calculated value
                is_active=True
            )
            db.session.add(staff)
            print(f"Added: {member['name']} ({member['staff_number']}) - PIN: {member['staff_number'][:4]}")
        
        db.session.commit()
        print("Staff database updated successfully!")

if __name__ == '__main__':
    update_staff_database()

