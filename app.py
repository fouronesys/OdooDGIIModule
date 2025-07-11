"""
Flask application factory for NCF Management System
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

# Initialize extensions
db = SQLAlchemy()
csrf = CSRFProtect()

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database configuration
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        # Fallback to SQLite for development
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ncf_management.db'
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)
    
    # Register blueprints
    from routes import main_bp
    app.register_blueprint(main_bp)
    
    # Create tables
    with app.app_context():
        db.create_all()
        
        # Initialize sample data if needed
        from flask_models import Company, NCFSequence, Invoice, NCFAssignment
        if not Company.query.first():
            init_sample_data()
    
    return app

def init_sample_data():
    """Initialize sample data for demonstration"""
    from flask_models import Company, NCFSequence, Invoice, NCFAssignment
    from datetime import datetime, timedelta
    
    # Create sample company
    company = Company(
        name='Empresa Ejemplo SRL',
        rnc='123456789',
        ncf_enabled=True,
        expiry_alert_days=30,
        low_availability_threshold=90.0
    )
    db.session.add(company)
    db.session.commit()
    
    # Create sample NCF sequences
    sequences = [
        {
            'prefix': 'B01',
            'document_type': 'invoice',
            'current_number': 1,
            'start_number': 1,
            'end_number': 1000,
            'start_date': datetime.now().date(),
            'expiry_date': datetime.now().date() + timedelta(days=365),
            'state': 'active'
        },
        {
            'prefix': 'B02',
            'document_type': 'invoice_consumer',
            'current_number': 1,
            'start_number': 1,
            'end_number': 500,
            'start_date': datetime.now().date(),
            'expiry_date': datetime.now().date() + timedelta(days=365),
            'state': 'active'
        },
        {
            'prefix': 'B04',
            'document_type': 'credit_note',
            'current_number': 1,
            'start_number': 1,
            'end_number': 100,
            'start_date': datetime.now().date(),
            'expiry_date': datetime.now().date() + timedelta(days=365),
            'state': 'active'
        }
    ]
    
    for seq_data in sequences:
        seq = NCFSequence(
            prefix=seq_data['prefix'],
            document_type=seq_data['document_type'],
            current_number=seq_data['current_number'],
            start_number=seq_data['start_number'],
            end_number=seq_data['end_number'],
            start_date=seq_data['start_date'],
            expiry_date=seq_data['expiry_date'],
            state=seq_data['state'],
            company_id=company.id
        )
        db.session.add(seq)
    
    db.session.commit()
    
    # Create sample invoices
    invoices = [
        {
            'invoice_number': 'INV-001',
            'customer_name': 'Juan Pérez',
            'customer_vat': '12345678901',
            'invoice_date': datetime.now().date(),
            'subtotal': 1000.00,
            'tax_amount': 180.00,
            'total_amount': 1180.00,
            'currency': 'DOP',
            'state': 'draft',
            'ncf_document_type': 'invoice',
            'requires_ncf': True
        },
        {
            'invoice_number': 'INV-002',
            'customer_name': 'María González',
            'customer_vat': '98765432109',
            'invoice_date': datetime.now().date(),
            'subtotal': 500.00,
            'tax_amount': 90.00,
            'total_amount': 590.00,
            'currency': 'DOP',
            'state': 'draft',
            'ncf_document_type': 'invoice_consumer',
            'requires_ncf': True
        }
    ]
    
    for inv_data in invoices:
        invoice = Invoice(
            invoice_number=inv_data['invoice_number'],
            customer_name=inv_data['customer_name'],
            customer_vat=inv_data['customer_vat'],
            invoice_date=inv_data['invoice_date'],
            subtotal=inv_data['subtotal'],
            tax_amount=inv_data['tax_amount'],
            total_amount=inv_data['total_amount'],
            currency=inv_data['currency'],
            state=inv_data['state'],
            ncf_document_type=inv_data['ncf_document_type'],
            requires_ncf=inv_data['requires_ncf'],
            company_id=company.id
        )
        db.session.add(invoice)
    
    db.session.commit()
    print("Sample data initialized successfully!")