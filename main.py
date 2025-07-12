from app import app, db
from flask_models import *  # Import all models to ensure tables are created

# Initialize database tables
with app.app_context():
    db.create_all()
    
    # Initialize sample data if no companies exist
    from flask_models import Company
    if not Company.query.first():
        from app import init_sample_data
        init_sample_data()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)