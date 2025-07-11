from app import db
from datetime import datetime, date
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DateField, SelectField, BooleanField
from wtforms.validators import DataRequired, Length, NumberRange


# Models (simplified from Odoo models)
class NCFSequence(db.Model):
    __tablename__ = 'ncf_sequence'
    
    id = db.Column(db.Integer, primary_key=True)
    prefix = db.Column(db.String(3), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)
    current_number = db.Column(db.Integer, default=1)
    start_number = db.Column(db.Integer, default=1)
    end_number = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    state = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    assignments = db.relationship('NCFAssignment', backref='sequence', lazy=True)
    
    @property
    def available_numbers(self):
        return max(0, self.end_number - self.current_number + 1)
    
    @property
    def used_numbers(self):
        return max(0, self.current_number - self.start_number)
    
    @property
    def percentage_used(self):
        total = self.end_number - self.start_number + 1
        return (self.used_numbers / total) * 100 if total > 0 else 0
    
    @property
    def days_to_expiry(self):
        return (self.expiry_date - date.today()).days
    
    @property
    def is_expiring_soon(self):
        return self.state == 'active' and 0 <= self.days_to_expiry <= 30
    
    @property
    def is_low_availability(self):
        return self.state == 'active' and self.percentage_used >= 90
    
    def get_next_ncf(self):
        if self.state != 'active':
            raise ValueError(f'Sequence {self.prefix} is not active')
        
        if self.expiry_date < date.today():
            self.state = 'expired'
            db.session.commit()
            raise ValueError(f'Sequence {self.prefix} has expired')
        
        if self.current_number > self.end_number:
            self.state = 'depleted'
            db.session.commit()
            raise ValueError(f'Sequence {self.prefix} has been depleted')
        
        # Generate the complete NCF number
        ncf_number = f"{self.prefix}{self.current_number:08d}"
        
        # Increment current number
        self.current_number += 1
        
        # Update state if sequence is about to be depleted
        if self.current_number > self.end_number:
            self.state = 'depleted'
        
        db.session.commit()
        return ncf_number


class NCFAssignment(db.Model):
    __tablename__ = 'ncf_assignment'
    
    id = db.Column(db.Integer, primary_key=True)
    ncf_number = db.Column(db.String(11), nullable=False, unique=True)
    sequence_id = db.Column(db.Integer, db.ForeignKey('ncf_sequence.id'), nullable=False)
    invoice_name = db.Column(db.String(100), nullable=False)
    partner_name = db.Column(db.String(200), nullable=False)
    invoice_amount = db.Column(db.Float, default=0.0)
    assignment_date = db.Column(db.DateTime, default=datetime.utcnow)
    invoice_state = db.Column(db.String(20), default='draft')


class Invoice(db.Model):
    __tablename__ = 'invoice'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    partner_name = db.Column(db.String(200), nullable=False)
    amount_total = db.Column(db.Float, default=0.0)
    ncf_document_type = db.Column(db.String(50))
    state = db.Column(db.String(20), default='draft')
    invoice_date = db.Column(db.Date, default=date.today)
    ncf_assignment_id = db.Column(db.Integer, db.ForeignKey('ncf_assignment.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    ncf_assignment = db.relationship('NCFAssignment', backref='invoice', uselist=False)


# Forms
class NCFSequenceForm(FlaskForm):
    prefix = StringField('NCF Prefix', validators=[DataRequired(), Length(min=3, max=3)])
    document_type = SelectField('Document Type', choices=[
        ('invoice', 'Factura de Crédito Fiscal'),
        ('invoice_consumer', 'Factura de Consumo'),
        ('credit_note', 'Nota de Crédito'),
        ('debit_note', 'Nota de Débito'),
    ], validators=[DataRequired()])
    start_number = IntegerField('Start Number', validators=[DataRequired(), NumberRange(min=1)])
    end_number = IntegerField('End Number', validators=[DataRequired(), NumberRange(min=1)])
    start_date = DateField('Start Date', validators=[DataRequired()])
    expiry_date = DateField('Expiry Date', validators=[DataRequired()])


class InvoiceForm(FlaskForm):
    name = StringField('Invoice Number', validators=[DataRequired()])
    partner_name = StringField('Customer Name', validators=[DataRequired()])
    amount_total = IntegerField('Amount', validators=[DataRequired(), NumberRange(min=1)])
    ncf_document_type = SelectField('NCF Document Type', choices=[
        ('invoice', 'Factura de Crédito Fiscal'),
        ('invoice_consumer', 'Factura de Consumo'),
        ('credit_note', 'Nota de Crédito'),
        ('debit_note', 'Nota de Débito'),
    ], validators=[DataRequired()])