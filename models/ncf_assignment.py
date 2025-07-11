# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class NCFAssignment(models.Model):
    _name = 'ncf.assignment'
    _description = 'NCF Assignment to Invoices'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'assignment_date desc, ncf_number desc'
    _rec_name = 'ncf_number'

    # Core Fields
    ncf_number = fields.Char(
        string='NCF Number',
        required=True,
        size=11,
        help='Complete NCF number (prefix + 8 digits)',
        tracking=True
    )
    
    sequence_id = fields.Many2one(
        'ncf.sequence',
        string='NCF Sequence',
        required=True,
        ondelete='restrict'
    )
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        required=True,
        ondelete='cascade',
        domain=[('move_type', 'in', ['out_invoice', 'out_refund'])]
    )
    
    assignment_date = fields.Datetime(
        string='Assignment Date',
        default=fields.Datetime.now,
        required=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    # Related Fields for easier access
    prefix = fields.Char(
        related='sequence_id.prefix',
        string='Prefix',
        store=True
    )
    
    document_type = fields.Selection(
        related='sequence_id.document_type',
        string='Document Type',
        store=True
    )
    
    invoice_state = fields.Selection(
        related='invoice_id.state',
        string='Invoice State',
        store=True
    )
    
    invoice_amount = fields.Monetary(
        related='invoice_id.amount_total',
        string='Invoice Amount',
        store=True
    )
    
    currency_id = fields.Many2one(
        related='invoice_id.currency_id',
        string='Currency'
    )
    
    partner_id = fields.Many2one(
        related='invoice_id.partner_id',
        string='Customer',
        store=True
    )
    
    @api.constrains('ncf_number')
    def _check_ncf_format(self):
        """Validate NCF number format."""
        for record in self:
            if not record.ncf_number or len(record.ncf_number) != 11:
                raise ValidationError(_('NCF number must be exactly 11 characters long.'))
            
            # Check if first 3 characters are letters/numbers (prefix)
            prefix = record.ncf_number[:3]
            if not prefix.isalnum():
                raise ValidationError(_('NCF prefix must contain only alphanumeric characters.'))
            
            # Check if last 8 characters are digits
            number_part = record.ncf_number[3:]
            if not number_part.isdigit():
                raise ValidationError(_('NCF number part must contain only digits.'))
    
    @api.constrains('ncf_number', 'company_id')
    def _check_unique_ncf(self):
        """Ensure NCF numbers are unique per company."""
        for record in self:
            existing = self.search([
                ('ncf_number', '=', record.ncf_number),
                ('company_id', '=', record.company_id.id),
                ('id', '!=', record.id),
            ])
            if existing:
                raise ValidationError(_(
                    'NCF number "%s" has already been assigned to invoice %s.'
                ) % (record.ncf_number, existing.invoice_id.name))
    
    @api.constrains('invoice_id')
    def _check_unique_invoice(self):
        """Ensure each invoice has only one NCF assignment."""
        for record in self:
            existing = self.search([
                ('invoice_id', '=', record.invoice_id.id),
                ('id', '!=', record.id),
            ])
            if existing:
                raise ValidationError(_(
                    'Invoice %s already has an NCF assigned: %s'
                ) % (record.invoice_id.name, existing.ncf_number))
    
    def name_get(self):
        """Custom name display."""
        result = []
        for record in self:
            name = f"{record.ncf_number} - {record.invoice_id.name}"
            result.append((record.id, name))
        return result
    
    @api.model
    def get_dgii_report_data(self, date_from, date_to, report_type='606'):
        """Get data for DGII reports."""
        domain = [
            ('assignment_date', '>=', date_from),
            ('assignment_date', '<=', date_to),
            ('invoice_state', 'in', ['posted']),
        ]
        
        if report_type == '606':  # Sales report
            domain.append(('invoice_id.move_type', '=', 'out_invoice'))
        elif report_type == '607':  # Purchase report (if needed for validation)
            domain.append(('invoice_id.move_type', '=', 'in_invoice'))
        
        assignments = self.search(domain, order='assignment_date, ncf_number')
        
        report_data = []
        for assignment in assignments:
            invoice = assignment.invoice_id
            
            # Calculate tax amounts
            tax_amount = sum(line.tax_line_id.amount for line in invoice.line_ids if line.tax_line_id)
            
            data = {
                'ncf_number': assignment.ncf_number,
                'document_type': assignment.document_type,
                'invoice_date': invoice.invoice_date,
                'invoice_number': invoice.name,
                'partner_name': invoice.partner_id.name,
                'partner_vat': invoice.partner_id.vat or '',
                'subtotal': invoice.amount_untaxed,
                'tax_amount': tax_amount,
                'total_amount': invoice.amount_total,
                'currency': invoice.currency_id.name,
            }
            report_data.append(data)
        
        return report_data
