# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class NCFSequenceWizard(models.TransientModel):
    _name = 'ncf.sequence.wizard'
    _description = 'NCF Sequence Creation Wizard'

    # Basic Information
    prefix = fields.Char(
        string='NCF Prefix',
        required=True,
        size=3,
        help='3-character NCF prefix (e.g., B02, E31)'
    )
    
    document_type = fields.Selection([
        ('invoice', 'Factura de Crédito Fiscal'),
        ('invoice_consumer', 'Factura de Consumo'),
        ('debit_note', 'Nota de Débito'),
        ('credit_note', 'Nota de Crédito'),
        ('informal', 'Comprobante de Compras'),
        ('unique', 'Comprobante Único de Ingresos'),
        ('minor_expenses', 'Comprobante de Gastos Menores'),
        ('exterior', 'Comprobante de Operaciones Exteriores'),
        ('payments', 'Comprobante de Pagos'),
    ], string='Document Type', required=True)
    
    # Range Configuration
    start_number = fields.Integer(
        string='Start Number',
        default=1,
        required=True,
        help='First number in the sequence'
    )
    
    end_number = fields.Integer(
        string='End Number',
        required=True,
        help='Last number in the sequence'
    )
    
    quantity = fields.Integer(
        string='Quantity',
        help='Number of NCFs in this sequence (auto-calculated)'
    )
    
    # Date Configuration
    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.context_today
    )
    
    expiry_date = fields.Date(
        string='Expiry Date',
        required=True
    )
    
    # Advanced Options
    auto_activate = fields.Boolean(
        string='Activate Immediately',
        default=True,
        help='Activate this sequence immediately upon creation'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    @api.onchange('start_number', 'end_number')
    def _onchange_numbers(self):
        """Calculate quantity when numbers change."""
        if self.start_number and self.end_number and self.end_number >= self.start_number:
            self.quantity = self.end_number - self.start_number + 1
        else:
            self.quantity = 0
    
    @api.onchange('document_type')
    def _onchange_document_type(self):
        """Suggest default prefix based on document type."""
        prefix_mapping = {
            'invoice': 'E31',
            'invoice_consumer': 'B02',
            'credit_note': 'E43',
            'debit_note': 'E44',
            'informal': 'B11',
            'unique': 'B12',
            'minor_expenses': 'B13',
            'exterior': 'B14',
            'payments': 'B15',
        }
        
        if self.document_type and self.document_type in prefix_mapping:
            self.prefix = prefix_mapping[self.document_type]
    
    @api.onchange('start_date')
    def _onchange_start_date(self):
        """Auto-set expiry date to end of year."""
        if self.start_date:
            year = self.start_date.year
            self.expiry_date = datetime(year, 12, 31).date()
    
    @api.constrains('prefix')
    def _check_prefix(self):
        """Validate NCF prefix format."""
        for wizard in self:
            if not wizard.prefix or len(wizard.prefix) != 3:
                raise ValidationError(_('NCF prefix must be exactly 3 characters long.'))
            
            if not wizard.prefix.isalnum():
                raise ValidationError(_('NCF prefix must contain only alphanumeric characters.'))
    
    @api.constrains('start_number', 'end_number')
    def _check_numbers(self):
        """Validate number ranges."""
        for wizard in self:
            if wizard.start_number <= 0:
                raise ValidationError(_('Start number must be greater than 0.'))
            
            if wizard.end_number <= wizard.start_number:
                raise ValidationError(_('End number must be greater than start number.'))
            
            if wizard.end_number > 99999999:
                raise ValidationError(_('End number cannot exceed 99999999 (8 digits).'))
    
    @api.constrains('start_date', 'expiry_date')
    def _check_dates(self):
        """Validate date ranges."""
        for wizard in self:
            if wizard.expiry_date <= wizard.start_date:
                raise ValidationError(_('Expiry date must be after start date.'))
            
            if wizard.start_date < fields.Date.context_today(wizard):
                raise ValidationError(_('Start date cannot be in the past.'))
    
    def _check_existing_sequence(self):
        """Check if a sequence with same prefix and document type exists."""
        self.ensure_one()
        
        existing = self.env['ncf.sequence'].search([
            ('prefix', '=', self.prefix),
            ('document_type', '=', self.document_type),
            ('company_id', '=', self.company_id.id),
            ('state', 'in', ['active', 'inactive']),
        ])
        
        if existing:
            raise ValidationError(_(
                'A sequence with prefix "%s" and document type "%s" already exists for this company: %s'
            ) % (self.prefix, dict(self._fields['document_type'].selection)[self.document_type], existing.display_name))
    
    def action_create_sequence(self):
        """Create the NCF sequence."""
        self.ensure_one()
        
        # Validate no conflicts
        self._check_existing_sequence()
        
        # Create the sequence
        sequence_vals = {
            'prefix': self.prefix,
            'document_type': self.document_type,
            'start_number': self.start_number,
            'end_number': self.end_number,
            'current_number': self.start_number,
            'start_date': self.start_date,
            'expiry_date': self.expiry_date,
            'state': 'active' if self.auto_activate else 'inactive',
            'company_id': self.company_id.id,
        }
        
        sequence = self.env['ncf.sequence'].create(sequence_vals)
        
        # Return action to view the created sequence
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ncf.sequence',
            'res_id': sequence.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_message': _('NCF sequence created successfully with %d numbers available.') % self.quantity
            }
        }
    
    def action_preview_sequence(self):
        """Preview the sequence configuration."""
        self.ensure_one()
        
        preview_info = {
            'prefix': self.prefix,
            'document_type_name': dict(self._fields['document_type'].selection)[self.document_type],
            'first_ncf': f"{self.prefix}{self.start_number:08d}",
            'last_ncf': f"{self.prefix}{self.end_number:08d}",
            'quantity': self.quantity,
            'validity_period': f"{self.start_date} to {self.expiry_date}",
        }
        
        message = _("""
        Sequence Preview:
        
        • Prefix: %(prefix)s
        • Document Type: %(document_type_name)s
        • First NCF: %(first_ncf)s
        • Last NCF: %(last_ncf)s
        • Total Quantity: %(quantity)d NCFs
        • Validity: %(validity_period)s
        """) % preview_info
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sequence Preview'),
                'message': message,
                'type': 'info',
                'sticky': True,
            }
        }
