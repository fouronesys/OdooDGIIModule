from flask import render_template, request, flash, redirect, url_for, jsonify
from app import app, db
from flask_models import NCFSequence, NCFAssignment, Invoice, NCFSequenceForm, InvoiceForm
from datetime import date, timedelta
import logging

# Enable logging for debugging
logging.basicConfig(level=logging.DEBUG)

@app.route('/')
def index():
    # Dashboard statistics
    total_sequences = NCFSequence.query.count()
    active_sequences = NCFSequence.query.filter_by(state='active').count()
    expiring_soon = NCFSequence.query.filter_by(state='active').filter(
        NCFSequence.expiry_date <= date.today() + timedelta(days=30)
    ).count()
    
    total_invoices = Invoice.query.count()
    total_assignments = NCFAssignment.query.count()
    
    # Recent activity
    recent_assignments = NCFAssignment.query.order_by(
        NCFAssignment.assignment_date.desc()
    ).limit(5).all()
    
    # Alert sequences
    alert_sequences = NCFSequence.query.filter_by(state='active').all()
    alerts = []
    for seq in alert_sequences:
        if seq.is_expiring_soon:
            alerts.append({
                'type': 'expiring',
                'message': f'Sequence {seq.prefix} expires in {seq.days_to_expiry} days',
                'sequence': seq
            })
        if seq.is_low_availability:
            alerts.append({
                'type': 'low_stock',
                'message': f'Sequence {seq.prefix} is {seq.percentage_used:.1f}% used',
                'sequence': seq
            })
    
    # Create stats object for template
    stats = {
        'total_sequences': total_sequences,
        'active_sequences': active_sequences,
        'expiring_soon': expiring_soon,
        'low_availability': sum(1 for seq in alert_sequences if seq.is_low_availability),
        'total_invoices': total_invoices,
        'total_assignments': total_assignments
    }
    
    return render_template('dashboard.html', 
                         stats=stats,
                         recent_assignments=recent_assignments,
                         alerts=alerts)

@app.route('/sequences')
def sequences():
    all_sequences = NCFSequence.query.order_by(NCFSequence.created_at.desc()).all()
    return render_template('sequences.html', sequences=all_sequences)

@app.route('/sequences/new', methods=['GET', 'POST'])
def new_sequence():
    form = NCFSequenceForm()
    
    if form.validate_on_submit():
        # Check if sequence already exists
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

# Initialize sample data when the app starts
with app.app_context():
    create_sample_data()