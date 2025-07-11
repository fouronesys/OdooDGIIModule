"""
Flask SQLAlchemy models for NCF Management System
"""

from app import db
from datetime import datetime, timedelta
from sqlalchemy import func

class Company(db.Model):
    """Company model for NCF management"""
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    rnc = db.Column(db.String(11), nullable=False)
    ncf_enabled = db.Column(db.Boolean, default=False)
    expiry_alert_days = db.Column(db.Integer, default=30)
    low_availability_threshold = db.Column(db.Float, default=90.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    ncf_sequences = db.relationship('NCFSequence', backref='company', lazy=True)
    invoices = db.relationship('Invoice', backref='company', lazy=True)
    
    def __repr__(self):
        return f'<Company {self.name}>'

class NCFSequence(db.Model):
    """NCF Sequence model for managing NCF number ranges"""
    __tablename__ = 'ncf_sequences'
    
    id = db.Column(db.Integer, primary_key=True)
    prefix = db.Column(db.String(3), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)
    current_number = db.Column(db.Integer, nullable=False, default=1)
    start_number = db.Column(db.Integer, nullable=False, default=1)
    end_number = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    state = db.Column(db.String(20), default='active')
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    assignments = db.relationship('NCFAssignment', backref='sequence', lazy=True)
    
    @property
    def display_name(self):
        """Display name for the sequence"""
        return f"{self.prefix} - {self.get_document_type_display()}"
    
    @property
    def available_numbers(self):
        """Calculate available numbers"""
        return self.end_number - self.current_number + 1
    
    @property
    def used_numbers(self):
        """Calculate used numbers"""
        return self.current_number - self.start_number
    
    @property
    def percentage_used(self):
        """Calculate percentage of sequence used"""
        total = self.end_number - self.start_number + 1
        used = self.used_numbers
        return (used / total) * 100 if total > 0 else 0
    
    @property
    def days_to_expiry(self):
        """Calculate days until expiry"""
        today = datetime.now().date()
        delta = self.expiry_date - today
        return delta.days
    
    @property
    def is_expiring_soon(self):
        """Check if sequence is expiring soon"""
        return self.days_to_expiry <= self.company.expiry_alert_days
    
    @property
    def is_low_availability(self):
        """Check if sequence has low availability"""
        return self.percentage_used >= self.company.low_availability_threshold
    
    def get_document_type_display(self):
        """Get display name for document type"""
        types = {
            'invoice': 'Factura de Crédito Fiscal',
            'invoice_consumer': 'Factura de Consumo',
            'debit_note': 'Nota de Débito',
            'credit_note': 'Nota de Crédito',
            'informal': 'Comprobante de Compras',
            'unique': 'Comprobante Único de Ingresos',
            'minor_expenses': 'Comprobante de Gastos Menores',
            'exterior': 'Comprobante de Operaciones Exteriores',
            'payments': 'Comprobante de Pagos',
        }
        return types.get(self.document_type, self.document_type)
    
    def get_next_ncf(self):
        """Get the next NCF number from this sequence"""
        if self.current_number > self.end_number:
            return None
        
        ncf_number = f"{self.prefix}{self.current_number:08d}"
        self.current_number += 1
        
        # Update state if depleted
        if self.current_number > self.end_number:
            self.state = 'depleted'
        
        db.session.commit()
        return ncf_number
    
    def __repr__(self):
        return f'<NCFSequence {self.display_name}>'

class Invoice(db.Model):
    """Invoice model"""
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), nullable=False)
    customer_name = db.Column(db.String(255), nullable=False)
    customer_vat = db.Column(db.String(15))
    invoice_date = db.Column(db.Date, nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='DOP')
    state = db.Column(db.String(20), default='draft')
    ncf_document_type = db.Column(db.String(50))
    requires_ncf = db.Column(db.Boolean, default=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    ncf_assignment = db.relationship('NCFAssignment', backref='invoice', uselist=False)
    
    @property
    def ncf_number(self):
        """Get NCF number if assigned"""
        return self.ncf_assignment.ncf_number if self.ncf_assignment else None
    
    def assign_ncf(self):
        """Assign NCF to this invoice"""
        if self.ncf_assignment or not self.requires_ncf:
            return False
        
        # Find appropriate sequence
        sequence = NCFSequence.query.filter_by(
            document_type=self.ncf_document_type,
            state='active',
            company_id=self.company_id
        ).filter(
            NCFSequence.current_number <= NCFSequence.end_number,
            NCFSequence.expiry_date >= datetime.now().date()
        ).first()
        
        if not sequence:
            return False
        
        # Get next NCF number
        ncf_number = sequence.get_next_ncf()
        if not ncf_number:
            return False
        
        # Create assignment
        assignment = NCFAssignment(
            ncf_number=ncf_number,
            sequence_id=sequence.id,
            invoice_id=self.id,
            assignment_date=datetime.utcnow()
        )
        db.session.add(assignment)
        db.session.commit()
        
        return True
    
    def __repr__(self):
        return f'<Invoice {self.invoice_number}>'

class NCFAssignment(db.Model):
    """NCF Assignment model for tracking NCF assignments to invoices"""
    __tablename__ = 'ncf_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    ncf_number = db.Column(db.String(11), nullable=False, unique=True)
    sequence_id = db.Column(db.Integer, db.ForeignKey('ncf_sequences.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    assignment_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    @property
    def prefix(self):
        """Get prefix from sequence"""
        return self.sequence.prefix
    
    @property
    def document_type(self):
        """Get document type from sequence"""
        return self.sequence.document_type
    
    def __repr__(self):
        return f'<NCFAssignment {self.ncf_number}>'