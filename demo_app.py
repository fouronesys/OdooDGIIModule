#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DateField, SelectField, BooleanField
from wtforms.validators import DataRequired, Length, NumberRange
from datetime import datetime, date, timedelta
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ncf-demo-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///ncf_demo.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

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
        
        ncf_number = f"{self.prefix}{self.current_number:08d}"
        self.current_number += 1
        
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

# Routes
@app.route('/')
def index():
    sequences = NCFSequence.query.filter_by(state='active').all()
    recent_assignments = NCFAssignment.query.order_by(NCFAssignment.assignment_date.desc()).limit(5).all()
    
    # Stats
    total_sequences = NCFSequence.query.filter_by(state='active').count()
    expiring_soon = sum(1 for seq in sequences if seq.is_expiring_soon)
    low_availability = sum(1 for seq in sequences if seq.is_low_availability)
    total_assignments = NCFAssignment.query.count()
    
    return render_template('dashboard.html', 
                         sequences=sequences, 
                         recent_assignments=recent_assignments,
                         stats={
                             'total_sequences': total_sequences,
                             'expiring_soon': expiring_soon,
                             'low_availability': low_availability,
                             'total_assignments': total_assignments
                         })

@app.route('/sequences')
def sequences():
    all_sequences = NCFSequence.query.order_by(NCFSequence.created_at.desc()).all()
    return render_template('sequences.html', sequences=all_sequences)

@app.route('/sequences/new', methods=['GET', 'POST'])
def new_sequence():
    form = NCFSequenceForm()
    
    if form.validate_on_submit():
        # Check for duplicate prefix + document type
        existing = NCFSequence.query.filter_by(
            prefix=form.prefix.data.upper(),
            document_type=form.document_type.data
        ).first()
        
        if existing:
            flash('A sequence with this prefix and document type already exists!', 'error')
        else:
            sequence = NCFSequence(
                prefix=form.prefix.data.upper(),
                document_type=form.document_type.data,
                start_number=form.start_number.data,
                end_number=form.end_number.data,
                current_number=form.start_number.data,
                start_date=form.start_date.data,
                expiry_date=form.expiry_date.data
            )
            db.session.add(sequence)
            db.session.commit()
            flash('NCF sequence created successfully!', 'success')
            return redirect(url_for('sequences'))
    
    return render_template('new_sequence.html', form=form)

@app.route('/invoices')
def invoices():
    all_invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
    return render_template('invoices.html', invoices=all_invoices)

@app.route('/invoices/new', methods=['GET', 'POST'])
def new_invoice():
    form = InvoiceForm()
    
    if form.validate_on_submit():
        invoice = Invoice(
            name=form.name.data,
            partner_name=form.partner_name.data,
            amount_total=form.amount_total.data,
            ncf_document_type=form.ncf_document_type.data
        )
        db.session.add(invoice)
        db.session.commit()
        flash('Invoice created successfully!', 'success')
        return redirect(url_for('invoices'))
    
    return render_template('new_invoice.html', form=form)

@app.route('/invoices/<int:invoice_id>/assign_ncf', methods=['POST'])
def assign_ncf(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    
    if invoice.ncf_assignment:
        return jsonify({'error': 'Invoice already has NCF assigned'}), 400
    
    # Find active sequence for document type
    sequence = NCFSequence.query.filter_by(
        document_type=invoice.ncf_document_type,
        state='active'
    ).first()
    
    if not sequence:
        return jsonify({'error': f'No active sequence found for {invoice.ncf_document_type}'}), 400
    
    try:
        ncf_number = sequence.get_next_ncf()
        
        assignment = NCFAssignment(
            ncf_number=ncf_number,
            sequence_id=sequence.id,
            invoice_name=invoice.name,
            partner_name=invoice.partner_name,
            invoice_amount=invoice.amount_total,
            invoice_state=invoice.state
        )
        
        db.session.add(assignment)
        invoice.ncf_assignment_id = assignment.id
        db.session.commit()
        
        return jsonify({
            'success': True,
            'ncf_number': ncf_number,
            'message': f'NCF {ncf_number} assigned successfully'
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@app.route('/assignments')
def assignments():
    all_assignments = NCFAssignment.query.order_by(NCFAssignment.assignment_date.desc()).all()
    return render_template('assignments.html', assignments=all_assignments)

@app.route('/api/sequences/stats')
def sequences_stats():
    sequences = NCFSequence.query.filter_by(state='active').all()
    stats = []
    
    for seq in sequences:
        stats.append({
            'id': seq.id,
            'prefix': seq.prefix,
            'document_type': seq.document_type,
            'percentage_used': seq.percentage_used,
            'days_to_expiry': seq.days_to_expiry,
            'available_numbers': seq.available_numbers,
            'is_expiring_soon': seq.is_expiring_soon,
            'is_low_availability': seq.is_low_availability
        })
    
    return jsonify(stats)

def create_sample_data():
    """Create sample data for demonstration"""
    # Check if data already exists
    if NCFSequence.query.first():
        return
    
    # Create sample sequences
    sequences = [
        NCFSequence(
            prefix='B02',
            document_type='invoice_consumer',
            start_number=1,
            end_number=1000,
            current_number=850,  # 85% used
            start_date=date(2025, 1, 1),
            expiry_date=date(2025, 12, 31),
            state='active'
        ),
        NCFSequence(
            prefix='E31',
            document_type='invoice',
            start_number=1,
            end_number=5000,
            current_number=125,
            start_date=date(2025, 1, 1),
            expiry_date=date(2025, 3, 31),  # Expiring soon
            state='active'
        ),
        NCFSequence(
            prefix='E43',
            document_type='credit_note',
            start_number=1,
            end_number=500,
            current_number=45,
            start_date=date(2025, 1, 1),
            expiry_date=date(2025, 12, 31),
            state='active'
        ),
    ]
    
    for seq in sequences:
        db.session.add(seq)
    
    db.session.commit()
    
    # Create sample invoices and assignments
    invoices_data = [
        ('INV-001', 'Comercial López S.R.L.', 125000, 'invoice'),
        ('INV-002', 'Juan Pérez', 45000, 'invoice_consumer'),
        ('INV-003', 'Empresa ABC S.A.', 350000, 'invoice'),
        ('INV-004', 'María González', 12500, 'invoice_consumer'),
        ('INV-005', 'Distribuidora XYZ', 89000, 'invoice'),
    ]
    
    for name, partner, amount, doc_type in invoices_data:
        invoice = Invoice(
            name=name,
            partner_name=partner,
            amount_total=amount,
            ncf_document_type=doc_type,
            state='posted'
        )
        db.session.add(invoice)
        db.session.commit()
        
        # Assign NCF
        sequence = NCFSequence.query.filter_by(document_type=doc_type, state='active').first()
        if sequence:
            try:
                ncf_number = sequence.get_next_ncf()
                assignment = NCFAssignment(
                    ncf_number=ncf_number,
                    sequence_id=sequence.id,
                    invoice_name=invoice.name,
                    partner_name=invoice.partner_name,
                    invoice_amount=invoice.amount_total,
                    invoice_state='posted'
                )
                db.session.add(assignment)
                invoice.ncf_assignment_id = assignment.id
                db.session.commit()
            except ValueError:
                pass

def initialize_database():
    with app.app_context():
        db.create_all()
        create_sample_data()

if __name__ == '__main__':
    initialize_database()
    app.run(host='0.0.0.0', port=5000, debug=True)