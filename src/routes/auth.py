from flask import Blueprint, request, jsonify, session
from datetime import datetime
from src.models.user import db
from src.models.staff import Staff

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        staff_number = data.get('staff_number')
        pin = data.get('pin')
        
        if not staff_number or not pin:
            return jsonify({'error': 'Staff number and PIN are required'}), 400
        
        # Find staff member
        staff = Staff.query.filter_by(staff_number=staff_number).first()
        
        if not staff or not staff.check_pin(pin):
            return jsonify({'error': 'Invalid staff number or PIN'}), 401
        
        if not staff.is_active:
            return jsonify({'error': 'Account is deactivated'}), 401
        
        # Update last login
        staff.last_login = datetime.utcnow()
        db.session.commit()
        
        # Store in session
        session['staff_id'] = staff.id
        session['staff_number'] = staff.staff_number
        session['role'] = staff.role
        
        return jsonify({
            'message': 'Login successful',
            'staff': staff.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    try:
        session.clear()
        return jsonify({'message': 'Logout successful'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/reset-pin', methods=['POST'])
def reset_pin():
    try:
        data = request.get_json()
        staff_number = data.get('staff_number')
        security_answer = data.get('security_answer')
        new_pin = data.get('new_pin')
        
        if not staff_number or not security_answer or not new_pin:
            return jsonify({'error': 'All fields are required'}), 400
        
        staff = Staff.query.filter_by(staff_number=staff_number).first()
        
        if not staff:
            return jsonify({'error': 'Staff member not found'}), 404
        
        if staff.security_answer != security_answer:
            return jsonify({'error': 'Incorrect security answer'}), 401
        
        staff.set_pin(new_pin)
        db.session.commit()
        
        return jsonify({'message': 'PIN reset successful'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/change-pin', methods=['POST'])
def change_pin():
    try:
        if 'staff_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        data = request.get_json()
        current_pin = data.get('current_pin')
        new_pin = data.get('new_pin')
        
        if not current_pin or not new_pin:
            return jsonify({'error': 'Current PIN and new PIN are required'}), 400
        
        staff = Staff.query.get(session['staff_id'])
        
        if not staff.check_pin(current_pin):
            return jsonify({'error': 'Current PIN is incorrect'}), 401
        
        staff.set_pin(new_pin)
        db.session.commit()
        
        return jsonify({'message': 'PIN changed successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/profile', methods=['GET'])
def get_profile():
    try:
        if 'staff_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        staff = Staff.query.get(session['staff_id'])
        
        if not staff:
            return jsonify({'error': 'Staff member not found'}), 404
        
        return jsonify({'staff': staff.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

