from flask import Blueprint, request, jsonify, session, send_file
from datetime import datetime, date, timedelta
from src.models.user import db
from src.models.staff import Staff
from src.models.meter_reading import MeterReading
from src.models.anomaly import Anomaly
import os
from io import BytesIO
import tempfile
import csv

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports/generate', methods=['POST'])
def generate_report():
    try:
        if 'staff_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        data = request.get_json()
        report_type = data.get('report_type')  # daily, weekly, monthly, yearly
        format_type = data.get('format', 'csv')  # csv format only for now
        from_date = data.get('from_date')
        to_date = data.get('to_date')
        
        if not report_type:
            return jsonify({'error': 'Report type is required'}), 400
        
        # Parse dates
        if from_date:
            from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
        if to_date:
            to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
        
        # Set default date ranges based on report type
        if not from_date or not to_date:
            today = date.today()
            if report_type == 'daily':
                from_date = to_date = today
            elif report_type == 'weekly':
                from_date = today - timedelta(days=7)
                to_date = today
            elif report_type == 'monthly':
                from_date = today.replace(day=1)
                to_date = today
            elif report_type == 'yearly':
                from_date = today.replace(month=1, day=1)
                to_date = today
        
        # Get data based on user role
        role = session['role']
        staff_id = session['staff_id']
        
        if role == 'reader':
            # Individual reader report
            readings = MeterReading.query.filter(
                MeterReading.staff_id == staff_id,
                MeterReading.reading_date >= from_date,
                MeterReading.reading_date <= to_date
            ).all()
            
            anomalies = Anomaly.query.filter(
                Anomaly.reported_by_id == staff_id,
                Anomaly.created_at >= datetime.combine(from_date, datetime.min.time()),
                Anomaly.created_at <= datetime.combine(to_date, datetime.max.time())
            ).all()
        else:
            # Team report for supervisors/engineers
            readings = MeterReading.query.filter(
                MeterReading.reading_date >= from_date,
                MeterReading.reading_date <= to_date
            ).all()
            
            anomalies = Anomaly.query.filter(
                Anomaly.created_at >= datetime.combine(from_date, datetime.min.time()),
                Anomaly.created_at <= datetime.combine(to_date, datetime.max.time())
            ).all()
        
        return generate_csv_report(readings, anomalies, report_type, from_date, to_date)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def generate_csv_report(readings, anomalies, report_type, from_date, to_date):
    """Generate CSV report"""
    try:
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w', newline='')
        
        writer = csv.writer(temp_file)
        
        # Write readings data
        writer.writerow(['=== METER READINGS ==='])
        writer.writerow(['Staff Number', 'Staff Name', 'Reading Date', 'ITIN Coverage (%)', 
                        'Target Coverage (%)', 'Status', 'Closed Premise', 'Meter Not on Site',
                        'Suspected Misallocated', 'Other Reason', 'Comments', 'Created At'])
        
        for reading in readings:
            writer.writerow([
                reading.staff_number,
                reading.staff_name,
                reading.reading_date,
                reading.itin_coverage,
                reading.target_coverage,
                reading.status,
                reading.closed_premise,
                reading.meter_not_on_site,
                reading.suspected_misallocated,
                reading.other_reason,
                reading.comments,
                reading.created_at
            ])
        
        # Write anomalies data
        writer.writerow([])
        writer.writerow(['=== ANOMALIES ==='])
        writer.writerow(['Type', 'Location', 'Description', 'Priority', 'Status', 
                        'Reported By', 'Assigned To', 'Days Open', 'Created At', 
                        'Resolved At', 'Escalated'])
        
        for anomaly in anomalies:
            writer.writerow([
                anomaly.type,
                anomaly.location,
                anomaly.description,
                anomaly.priority,
                anomaly.status,
                anomaly.reported_by_name,
                anomaly.assigned_to_name or 'Unassigned',
                anomaly.days_open,
                anomaly.created_at,
                anomaly.resolved_at,
                'Yes' if anomaly.escalation_sent else 'No'
            ])
        
        # Write summary
        writer.writerow([])
        writer.writerow(['=== SUMMARY ==='])
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Total Readings', len(readings)])
        writer.writerow(['Completed Readings', len([r for r in readings if r.status == 'complete'])])
        writer.writerow(['Pending Readings', len([r for r in readings if r.status == 'pending'])])
        writer.writerow(['Delayed Readings', len([r for r in readings if r.status == 'delayed'])])
        avg_coverage = round(sum(r.itin_coverage for r in readings) / len(readings), 2) if readings else 0
        writer.writerow(['Average Coverage (%)', avg_coverage])
        writer.writerow(['Total Anomalies', len(anomalies)])
        writer.writerow(['Resolved Anomalies', len([a for a in anomalies if a.status == 'resolved'])])
        writer.writerow(['Escalated Anomalies', len([a for a in anomalies if a.escalation_sent])])
        
        temp_file.close()
        
        # Generate filename
        filename = f"reading_reports_{report_type}_{from_date}_{to_date}.csv"
        
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name=filename,
            mimetype='text/csv'
        )
        
    except Exception as e:
        # Clean up temp file if error occurs
        if 'temp_file' in locals():
            os.unlink(temp_file.name)
        raise e

@reports_bp.route('/reports/dashboard-stats', methods=['GET'])
def get_dashboard_stats():
    try:
        if 'staff_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        role = session['role']
        staff_id = session['staff_id']
        
        # Get current month data
        today = date.today()
        current_month = today.replace(day=1)
        
        if role == 'reader':
            # Individual stats
            monthly_readings = MeterReading.query.filter(
                MeterReading.staff_id == staff_id,
                MeterReading.reading_date >= current_month
            ).all()
            
            monthly_anomalies = Anomaly.query.filter(
                Anomaly.reported_by_id == staff_id,
                Anomaly.created_at >= datetime.combine(current_month, datetime.min.time())
            ).all()
            
            avg_coverage = sum(r.itin_coverage for r in monthly_readings) / len(monthly_readings) if monthly_readings else 0
            active_staff = 1  # Just the current user
            
        else:
            # Team stats
            monthly_readings = MeterReading.query.filter(
                MeterReading.reading_date >= current_month
            ).all()
            
            monthly_anomalies = Anomaly.query.filter(
                Anomaly.created_at >= datetime.combine(current_month, datetime.min.time())
            ).all()
            
            avg_coverage = sum(r.itin_coverage for r in monthly_readings) / len(monthly_readings) if monthly_readings else 0
            active_staff = Staff.query.filter_by(is_active=True).count()
        
        pending_anomalies = len([a for a in monthly_anomalies if a.status in ['new', 'pending']])
        escalated_issues = len([a for a in monthly_anomalies if a.escalation_sent])
        
        return jsonify({
            'itin_coverage': round(avg_coverage, 1),
            'active_readers': active_staff,
            'pending_anomalies': pending_anomalies,
            'escalated_issues': escalated_issues,
            'total_readings_today': len([r for r in monthly_readings if r.reading_date == today]),
            'completed_itins': len([r for r in monthly_readings if r.status == 'complete']),
            'pending_reviews': len([r for r in monthly_readings if r.status == 'pending'])
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

