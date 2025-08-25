from flask import Blueprint, request, jsonify, session
from datetime import datetime, date
from src.models.user import db
from src.models.staff import Staff
from src.models.meter_reading import MeterReading
import os
from werkzeug.utils import secure_filename

readings_bp = Blueprint('readings', __name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@readings_bp.route('/readings', methods=['GET'])
def get_readings():
    try:
        if 'staff_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        staff_id = session['staff_id']
        role = session['role']
        
        if role == 'reader':
            # Readers can only see their own readings
            readings = MeterReading.query.filter_by(staff_id=staff_id).order_by(MeterReading.reading_date.desc()).all()
        else:
            # Supervisors and engineers can see all readings
            readings = MeterReading.query.order_by(MeterReading.reading_date.desc()).all()
        
        return jsonify({
            'readings': [reading.to_dict() for reading in readings]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@readings_bp.route('/readings', methods=['POST'])
def create_reading():
    try:
        if 'staff_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        data = request.get_json()
        staff = Staff.query.get(session['staff_id'])
        
        if not staff:
            return jsonify({'error': 'Staff member not found'}), 404
        
        # Create new meter reading
        reading = MeterReading(
            staff_id=staff.id,
            staff_name=staff.name,
            staff_number=staff.staff_number,
            itin_coverage=data.get('itin_coverage', 0),
            target_coverage=data.get('target_coverage', 100),
            reading_date=datetime.strptime(data.get('reading_date'), '%Y-%m-%d').date(),
            closed_premise=data.get('closed_premise', 0),
            meter_not_on_site=data.get('meter_not_on_site', 0),
            suspected_misallocated=data.get('suspected_misallocated', 0),
            other_reason=data.get('other_reason', 0),
            comments=data.get('comments', '')
        )
        
        # Set status based on coverage
        if reading.itin_coverage >= reading.target_coverage:
            reading.status = 'complete'
        elif reading.itin_coverage >= 90:
            reading.status = 'pending'
        else:
            reading.status = 'delayed'
        
        db.session.add(reading)
        db.session.commit()
        
        return jsonify({
            'message': 'Reading submitted successfully',
            'reading': reading.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@readings_bp.route('/readings/<int:reading_id>', methods=['PUT'])
def update_reading():
    try:
        if 'staff_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        reading = MeterReading.query.get(reading_id)
        
        if not reading:
            return jsonify({'error': 'Reading not found'}), 404
        
        # Check permissions
        if session['role'] == 'reader' and reading.staff_id != session['staff_id']:
            return jsonify({'error': 'Permission denied'}), 403
        
        data = request.get_json()
        
        # Update fields
        if 'itin_coverage' in data:
            reading.itin_coverage = data['itin_coverage']
        if 'status' in data:
            reading.status = data['status']
        if 'comments' in data:
            reading.comments = data['comments']
        
        reading.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Reading updated successfully',
            'reading': reading.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@readings_bp.route('/readings/upload', methods=['POST'])
def upload_reading_file():
    try:
        if 'staff_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add timestamp to filename to avoid conflicts
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            filename = timestamp + filename
            
            # Create upload directory if it doesn't exist
            upload_path = os.path.join(os.path.dirname(__file__), '..', 'static', UPLOAD_FOLDER)
            os.makedirs(upload_path, exist_ok=True)
            
            file_path = os.path.join(upload_path, filename)
            file.save(file_path)
            
            return jsonify({
                'message': 'File uploaded successfully',
                'filename': filename,
                'file_path': f'/uploads/{filename}'
            }), 200
        
        return jsonify({'error': 'Invalid file type'}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@readings_bp.route('/readings/stats', methods=['GET'])
def get_reading_stats():
    try:
        if 'staff_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        staff_id = session['staff_id']
        role = session['role']
        
        if role == 'reader':
            # Stats for individual reader
            total_readings = MeterReading.query.filter_by(staff_id=staff_id).count()
            completed_readings = MeterReading.query.filter_by(staff_id=staff_id, status='complete').count()
            pending_readings = MeterReading.query.filter_by(staff_id=staff_id, status='pending').count()
            delayed_readings = MeterReading.query.filter_by(staff_id=staff_id, status='delayed').count()
            
            # Average coverage for current month
            current_month = date.today().replace(day=1)
            monthly_readings = MeterReading.query.filter(
                MeterReading.staff_id == staff_id,
                MeterReading.reading_date >= current_month
            ).all()
            
            avg_coverage = sum(r.itin_coverage for r in monthly_readings) / len(monthly_readings) if monthly_readings else 0
            
        else:
            # Stats for supervisors/engineers
            total_readings = MeterReading.query.count()
            completed_readings = MeterReading.query.filter_by(status='complete').count()
            pending_readings = MeterReading.query.filter_by(status='pending').count()
            delayed_readings = MeterReading.query.filter_by(status='delayed').count()
            
            # Average coverage across all staff
            all_readings = MeterReading.query.all()
            avg_coverage = sum(r.itin_coverage for r in all_readings) / len(all_readings) if all_readings else 0
        
        return jsonify({
            'total_readings': total_readings,
            'completed_readings': completed_readings,
            'pending_readings': pending_readings,
            'delayed_readings': delayed_readings,
            'average_coverage': round(avg_coverage, 2),
            'active_staff': Staff.query.filter_by(is_active=True).count()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

