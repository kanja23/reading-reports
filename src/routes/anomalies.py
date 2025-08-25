from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta
from src.models.user import db
from src.models.staff import Staff
from src.models.anomaly import Anomaly
from src.models.meter_reading import MeterReading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

anomalies_bp = Blueprint('anomalies', __name__)

# Email configuration
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
EMAIL_USER = os.environ.get('EMAIL_USER', 'your-email@gmail.com')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', 'your-app-password')
ESCALATION_EMAIL = 'cynthia.odhiambo@kenyapower.co.ke'  # Commercial Engineer

def send_escalation_email(anomaly):
    """Send escalation email for anomalies over 4 days old"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = ESCALATION_EMAIL
        msg['Subject'] = f'ESCALATION: {anomaly.type} - {anomaly.location} (Day {anomaly.days_open})'
        
        body = f"""
        Dear Cynthia Odhiambo,
        
        An anomaly has been escalated due to being unresolved for {anomaly.days_open} days.
        
        ANOMALY DETAILS:
        - Type: {anomaly.type}
        - Location: {anomaly.location}
        - Priority: {anomaly.priority.upper()}
        - Reported by: {anomaly.reported_by_name}
        - Assigned to: {anomaly.assigned_to_name or 'Unassigned'}
        - Description: {anomaly.description}
        - Created: {anomaly.created_at.strftime('%Y-%m-%d %H:%M')}
        - Days Open: {anomaly.days_open}
        
        Please take immediate action to resolve this issue.
        
        Best regards,
        Reading Reports.io System
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_USER, ESCALATION_EMAIL, text)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Failed to send escalation email: {str(e)}")
        return False

@anomalies_bp.route('/anomalies', methods=['GET'])
def get_anomalies():
    try:
        if 'staff_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        staff_id = session['staff_id']
        role = session['role']
        
        if role == 'reader':
            # Readers can only see their own reported anomalies
            anomalies = Anomaly.query.filter_by(reported_by_id=staff_id).order_by(Anomaly.created_at.desc()).all()
        else:
            # Supervisors and engineers can see all anomalies
            anomalies = Anomaly.query.order_by(Anomaly.created_at.desc()).all()
        
        # Update days_open for all anomalies
        for anomaly in anomalies:
            anomaly.days_open = anomaly.calculate_days_open()
        
        db.session.commit()
        
        return jsonify({
            'anomalies': [anomaly.to_dict() for anomaly in anomalies]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@anomalies_bp.route('/anomalies', methods=['POST'])
def create_anomaly():
    try:
        if 'staff_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        data = request.get_json()
        staff = Staff.query.get(session['staff_id'])
        
        if not staff:
            return jsonify({'error': 'Staff member not found'}), 404
        
        # Create new anomaly
        anomaly = Anomaly(
            type=data.get('type'),
            location=data.get('location'),
            description=data.get('description'),
            priority=data.get('priority', 'medium'),
            reported_by_id=staff.id,
            reported_by_name=staff.name,
            meter_reading_id=data.get('meter_reading_id')
        )
        
        # Auto-assign based on type
        if data.get('assigned_to_id'):
            assigned_staff = Staff.query.get(data.get('assigned_to_id'))
            if assigned_staff:
                anomaly.assigned_to_id = assigned_staff.id
                anomaly.assigned_to_name = assigned_staff.name
                anomaly.status = 'pending'
        
        db.session.add(anomaly)
        db.session.commit()
        
        return jsonify({
            'message': 'Anomaly reported successfully',
            'anomaly': anomaly.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@anomalies_bp.route('/anomalies/<int:anomaly_id>', methods=['PUT'])
def update_anomaly():
    try:
        if 'staff_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        anomaly = Anomaly.query.get(anomaly_id)
        
        if not anomaly:
            return jsonify({'error': 'Anomaly not found'}), 404
        
        # Check permissions
        role = session['role']
        staff_id = session['staff_id']
        
        if role == 'reader' and anomaly.reported_by_id != staff_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        data = request.get_json()
        
        # Update fields
        if 'status' in data:
            anomaly.status = data['status']
            if data['status'] == 'resolved':
                anomaly.resolved_at = datetime.utcnow()
        
        if 'assigned_to_id' in data and role in ['supervisor', 'engineer']:
            assigned_staff = Staff.query.get(data['assigned_to_id'])
            if assigned_staff:
                anomaly.assigned_to_id = assigned_staff.id
                anomaly.assigned_to_name = assigned_staff.name
        
        if 'priority' in data and role in ['supervisor', 'engineer']:
            anomaly.priority = data['priority']
        
        if 'description' in data:
            anomaly.description = data['description']
        
        anomaly.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Anomaly updated successfully',
            'anomaly': anomaly.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@anomalies_bp.route('/anomalies/escalate', methods=['POST'])
def check_escalations():
    """Check for anomalies that need escalation and send emails"""
    try:
        if 'staff_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        # Only supervisors and engineers can trigger escalation checks
        if session['role'] not in ['supervisor', 'engineer']:
            return jsonify({'error': 'Permission denied'}), 403
        
        # Find anomalies that should be escalated
        anomalies_to_escalate = Anomaly.query.filter(
            Anomaly.status != 'resolved',
            Anomaly.escalation_sent == False
        ).all()
        
        escalated_count = 0
        
        for anomaly in anomalies_to_escalate:
            anomaly.days_open = anomaly.calculate_days_open()
            
            if anomaly.should_escalate():
                # Send escalation email
                if send_escalation_email(anomaly):
                    anomaly.escalation_sent = True
                    anomaly.escalated_at = datetime.utcnow()
                    anomaly.escalation_email_sent_at = datetime.utcnow()
                    anomaly.status = 'escalated'
                    escalated_count += 1
        
        db.session.commit()
        
        return jsonify({
            'message': f'Escalation check completed. {escalated_count} anomalies escalated.',
            'escalated_count': escalated_count
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@anomalies_bp.route('/anomalies/stats', methods=['GET'])
def get_anomaly_stats():
    try:
        if 'staff_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        staff_id = session['staff_id']
        role = session['role']
        
        if role == 'reader':
            # Stats for individual reader
            total_anomalies = Anomaly.query.filter_by(reported_by_id=staff_id).count()
            pending_anomalies = Anomaly.query.filter_by(reported_by_id=staff_id, status='pending').count()
            resolved_anomalies = Anomaly.query.filter_by(reported_by_id=staff_id, status='resolved').count()
            escalated_anomalies = Anomaly.query.filter_by(reported_by_id=staff_id, status='escalated').count()
        else:
            # Stats for supervisors/engineers
            total_anomalies = Anomaly.query.count()
            pending_anomalies = Anomaly.query.filter_by(status='pending').count()
            resolved_anomalies = Anomaly.query.filter_by(status='resolved').count()
            escalated_anomalies = Anomaly.query.filter_by(status='escalated').count()
        
        # Count anomalies by type
        anomaly_types = db.session.query(
            Anomaly.type, 
            db.func.count(Anomaly.id)
        ).group_by(Anomaly.type).all()
        
        return jsonify({
            'total_anomalies': total_anomalies,
            'pending_anomalies': pending_anomalies,
            'resolved_anomalies': resolved_anomalies,
            'escalated_anomalies': escalated_anomalies,
            'anomaly_types': [{'type': t[0], 'count': t[1]} for t in anomaly_types]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@anomalies_bp.route('/anomalies/types', methods=['GET'])
def get_anomaly_types():
    """Get predefined anomaly types"""
    types = [
        'Faulty meters',
        'Power theft',
        'Rebilling issues',
        'Debits',
        'Misallocated accounts',
        'Meters replaced with prepaid',
        'Other anomaly'
    ]
    
    return jsonify({'types': types}), 200

