"""
Flask routes for NCF Management System
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_models import Company, NCFSequence, Invoice, NCFAssignment
from app import db
from datetime import datetime, timedelta
from sqlalchemy import func, desc

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def dashboard():
    """Main dashboard showing NCF management overview"""
    company = Company.query.first()
    
    if not company:
        flash('No company configured. Please set up your company first.', 'warning')
        return redirect(url_for('main.setup'))
    
    # Statistics
    total_sequences = NCFSequence.query.filter_by(company_id=company.id).count()
    active_sequences = NCFSequence.query.filter_by(company_id=company.id, state='active').count()
    total_invoices = Invoice.query.filter_by(company_id=company.id).count()
    invoices_with_ncf = Invoice.query.filter_by(company_id=company.id).filter(Invoice.ncf_assignment.has()).count()
    
    # Expiring sequences
    expiring_sequences = NCFSequence.query.filter_by(
        company_id=company.id,
        state='active'
    ).filter(
        NCFSequence.expiry_date <= datetime.now().date() + timedelta(days=company.expiry_alert_days)
    ).all()
    
    # Low availability sequences
    low_availability_sequences = []
    for seq in NCFSequence.query.filter_by(company_id=company.id, state='active').all():
        if seq.percentage_used >= company.low_availability_threshold:
            low_availability_sequences.append(seq)
    
    # Recent assignments
    recent_assignments = NCFAssignment.query.join(Invoice).filter(
        Invoice.company_id == company.id
    ).order_by(desc(NCFAssignment.assignment_date)).limit(10).all()
    
    return render_template('dashboard.html', 
                         company=company,
                         total_sequences=total_sequences,
                         active_sequences=active_sequences,
                         total_invoices=total_invoices,
                         invoices_with_ncf=invoices_with_ncf,
                         expiring_sequences=expiring_sequences,
                         low_availability_sequences=low_availability_sequences,
                         recent_assignments=recent_assignments)

@main_bp.route('/sequences')
def sequences():
    """List all NCF sequences"""
    company = Company.query.first()
    if not company:
        return redirect(url_for('main.setup'))
    
    sequences = NCFSequence.query.filter_by(company_id=company.id).order_by(
        NCFSequence.prefix, NCFSequence.document_type
    ).all()
    
    return render_template('sequences.html', sequences=sequences, company=company)

@main_bp.route('/sequences/new', methods=['GET', 'POST'])
def new_sequence():
    """Create new NCF sequence"""
    company = Company.query.first()
    if not company:
        return redirect(url_for('main.setup'))
    
    if request.method == 'POST':
        try:
            sequence = NCFSequence(
                prefix=request.form['prefix'].upper(),
                document_type=request.form['document_type'],
                current_number=int(request.form['start_number']),
                start_number=int(request.form['start_number']),
                end_number=int(request.form['end_number']),
                start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d').date(),
                expiry_date=datetime.strptime(request.form['expiry_date'], '%Y-%m-%d').date(),
                state='active',
                company_id=company.id
            )
            db.session.add(sequence)
            db.session.commit()
            flash('NCF sequence created successfully!', 'success')
            return redirect(url_for('main.sequences'))
        except Exception as e:
            flash(f'Error creating sequence: {str(e)}', 'danger')
    
    document_types = [
        ('invoice', 'Factura de Crédito Fiscal'),
        ('invoice_consumer', 'Factura de Consumo'),
        ('debit_note', 'Nota de Débito'),
        ('credit_note', 'Nota de Crédito'),
        ('informal', 'Comprobante de Compras'),
        ('unique', 'Comprobante Único de Ingresos'),
        ('minor_expenses', 'Comprobante de Gastos Menores'),
        ('exterior', 'Comprobante de Operaciones Exteriores'),
        ('payments', 'Comprobante de Pagos'),
    ]
    
    return render_template('new_sequence.html', document_types=document_types)

@main_bp.route('/invoices')
def invoices():
    """List all invoices"""
    company = Company.query.first()
    if not company:
        return redirect(url_for('main.setup'))
    
    invoices = Invoice.query.filter_by(company_id=company.id).order_by(
        desc(Invoice.invoice_date)
    ).all()
    
    return render_template('invoices.html', invoices=invoices, company=company)

@main_bp.route('/invoices/new', methods=['GET', 'POST'])
def new_invoice():
    """Create new invoice"""
    company = Company.query.first()
    if not company:
        return redirect(url_for('main.setup'))
    
    if request.method == 'POST':
        try:
            invoice = Invoice(
                invoice_number=request.form['invoice_number'],
                customer_name=request.form['customer_name'],
                customer_vat=request.form.get('customer_vat', ''),
                invoice_date=datetime.strptime(request.form['invoice_date'], '%Y-%m-%d').date(),
                subtotal=float(request.form['subtotal']),
                tax_amount=float(request.form['tax_amount']),
                total_amount=float(request.form['total_amount']),
                currency=request.form.get('currency', 'DOP'),
                state='draft',
                ncf_document_type=request.form['ncf_document_type'],
                requires_ncf=bool(request.form.get('requires_ncf')),
                company_id=company.id
            )
            db.session.add(invoice)
            db.session.commit()
            flash('Invoice created successfully!', 'success')
            return redirect(url_for('main.invoices'))
        except Exception as e:
            flash(f'Error creating invoice: {str(e)}', 'danger')
    
    document_types = [
        ('invoice', 'Factura de Crédito Fiscal'),
        ('invoice_consumer', 'Factura de Consumo'),
        ('debit_note', 'Nota de Débito'),
        ('credit_note', 'Nota de Crédito'),
    ]
    
    return render_template('new_invoice.html', document_types=document_types)

@main_bp.route('/invoices/<int:invoice_id>/assign_ncf', methods=['POST'])
def assign_ncf(invoice_id):
    """Assign NCF to invoice"""
    invoice = Invoice.query.get_or_404(invoice_id)
    
    if invoice.assign_ncf():
        flash(f'NCF assigned successfully to invoice {invoice.invoice_number}!', 'success')
    else:
        flash('Error assigning NCF. No available sequence found.', 'danger')
    
    return redirect(url_for('main.invoices'))

@main_bp.route('/assignments')
def assignments():
    """List all NCF assignments"""
    company = Company.query.first()
    if not company:
        return redirect(url_for('main.setup'))
    
    assignments = NCFAssignment.query.join(Invoice).filter(
        Invoice.company_id == company.id
    ).order_by(desc(NCFAssignment.assignment_date)).all()
    
    return render_template('assignments.html', assignments=assignments, company=company)

@main_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    """Company setup"""
    company = Company.query.first()
    
    if request.method == 'POST':
        if company:
            company.name = request.form['name']
            company.rnc = request.form['rnc']
            company.ncf_enabled = bool(request.form.get('ncf_enabled'))
            company.expiry_alert_days = int(request.form['expiry_alert_days'])
            company.low_availability_threshold = float(request.form['low_availability_threshold'])
        else:
            company = Company(
                name=request.form['name'],
                rnc=request.form['rnc'],
                ncf_enabled=bool(request.form.get('ncf_enabled')),
                expiry_alert_days=int(request.form['expiry_alert_days']),
                low_availability_threshold=float(request.form['low_availability_threshold'])
            )
            db.session.add(company)
        
        db.session.commit()
        flash('Company settings saved successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('setup.html', company=company)

@main_bp.route('/api/sequences/<int:sequence_id>/stats')
def sequence_stats(sequence_id):
    """Get sequence statistics as JSON"""
    sequence = NCFSequence.query.get_or_404(sequence_id)
    
    return jsonify({
        'available_numbers': sequence.available_numbers,
        'used_numbers': sequence.used_numbers,
        'percentage_used': sequence.percentage_used,
        'days_to_expiry': sequence.days_to_expiry,
        'is_expiring_soon': sequence.is_expiring_soon,
        'is_low_availability': sequence.is_low_availability
    })

@main_bp.route('/api/dashboard/stats')
def dashboard_stats():
    """Get dashboard statistics as JSON"""
    company = Company.query.first()
    if not company:
        return jsonify({'error': 'No company configured'}), 400
    
    stats = {
        'total_sequences': NCFSequence.query.filter_by(company_id=company.id).count(),
        'active_sequences': NCFSequence.query.filter_by(company_id=company.id, state='active').count(),
        'total_invoices': Invoice.query.filter_by(company_id=company.id).count(),
        'invoices_with_ncf': Invoice.query.filter_by(company_id=company.id).filter(Invoice.ncf_assignment.has()).count(),
        'expiring_sequences': NCFSequence.query.filter_by(
            company_id=company.id,
            state='active'
        ).filter(
            NCFSequence.expiry_date <= datetime.now().date() + timedelta(days=company.expiry_alert_days)
        ).count()
    }
    
    return jsonify(stats)