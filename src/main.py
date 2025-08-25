import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.user import db
from src.models.staff import Staff
from src.models.meter_reading import MeterReading
from src.models.anomaly import Anomaly
from src.routes.user import user_bp
from src.routes.auth import auth_bp
from src.routes.readings import readings_bp
from src.routes.anomalies import anomalies_bp
from src.routes.reports import reports_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Enable CORS for all routes
CORS(app, supports_credentials=True)

# Register blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(readings_bp, url_prefix='/api')
app.register_blueprint(anomalies_bp, url_prefix='/api')
app.register_blueprint(reports_bp, url_prefix='/api')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Initialize database and create sample data
with app.app_context():
    db.create_all()
    
    # Create sample staff if none exist
    if Staff.query.count() == 0:
        sample_staff = [
            Staff(staff_number='001', name='Martin Mackenzie', pin='0001', role='reader', email='martin.mackenzie@kenyapower.co.ke'),
            Staff(staff_number='002', name='Arnold Chogo', pin='0002', role='reader', email='arnold.chogo@kenyapower.co.ke'),
            Staff(staff_number='003', name='Samwel Nyamori', pin='0003', role='reader', email='samwel.nyamori@kenyapower.co.ke'),
            Staff(staff_number='013', name='Godfrey Kopilo', pin='0013', role='supervisor', email='godfrey.kopilo@kenyapower.co.ke'),
            Staff(staff_number='014', name='Paul Odhiambo', pin='0014', role='supervisor', email='paul.odhiambo@kenyapower.co.ke'),
            Staff(staff_number='015', name='Cynthia Odhiambo', pin='0015', role='engineer', email='cynthia.odhiambo@kenyapower.co.ke'),
        ]
        
        for staff in sample_staff:
            staff.security_question = "What is your mother's maiden name?"
            staff.security_answer = "sample"
            db.session.add(staff)
        
        db.session.commit()

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
