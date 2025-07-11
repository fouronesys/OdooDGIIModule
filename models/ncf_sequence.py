# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class NCFSequence(models.Model):
    _name = 'ncf.sequence'
    _description = 'NCF Sequence Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'prefix, document_type, start_date desc'
    _rec_name = 'display_name'

    # Basic Information
    prefix = fields.Char(
        string='NCF Prefix',
        required=True,
        size=3,
        help='3-character prefix for NCF numbers (e.g., B01, E31)',
        tracking=True
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
    ], string='Document Type', required=True, tracking=True)
    
    # Sequence Configuration
    current_number = fields.Integer(
        string='Current Number',
        required=True,
        default=1,
        help='Next NCF number to be assigned',
        tracking=True
    )
    
    start_number = fields.Integer(
        string='Start Number',
        required=True,
        default=1,
        help='First number in the sequence'
    )
    
    end_number = fields.Integer(
        string='End Number',
        required=True,
        help='Last number in the sequence'
    )
    
    # Date Management
    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.today,
        help='Date when this sequence becomes active'
    )
    
    expiry_date = fields.Date(
        string='Expiry Date',
        required=True,
        help='Date when this sequence expires'
    )
    
    # Status and Control
    state = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('expired', 'Expired'),
        ('depleted', 'Depleted'),
    ], string='State', default='active', tracking=True)
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    # Computed Fields
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    available_numbers = fields.Integer(
        string='Available Numbers',
        compute='_compute_statistics',
        store=True
    )
    
    used_numbers = fields.Integer(
        string='Used Numbers',
        compute='_compute_statistics',
        store=True
    )
    
    percentage_used = fields.Float(
        string='Percentage Used',
        compute='_compute_statistics',
        store=True
    )
    
    days_to_expiry = fields.Integer(
        string='Days to Expiry',
        compute='_compute_statistics',
        store=True
    )
    
    is_expiring_soon = fields.Boolean(
        string='Expiring Soon',
        compute='_compute_statistics',
        store=True
    )
    
    is_low_availability = fields.Boolean(
        string='Low Availability',
        compute='_compute_statistics',
        store=True
    )
    
    # Relationships
    assignment_ids = fields.One2many(
        'ncf.assignment',
        'sequence_id',
        string='NCF Assignments',
        readonly=True
    )
    
    @api.depends('prefix', 'document_type')
    def _compute_display_name(self):
        for record in self:
            doc_type_dict = dict(record._fields['document_type'].selection)
            doc_type_name = doc_type_dict.get(record.document_type, record.document_type)
            record.display_name = f"{record.prefix} - {doc_type_name}"
    
    @api.depends('current_number', 'start_number', 'end_number', 'expiry_date', 'state')
    def _compute_statistics(self):
        for record in self:
            total_numbers = record.end_number - record.start_number + 1
            used = max(0, record.current_number - record.start_number)
            available = max(0, record.end_number - record.current_number + 1)
            
            record.available_numbers = available
            record.used_numbers = used
            record.percentage_used = (used / total_numbers * 100) if total_numbers > 0 else 0
            
            # Days to expiry
            today = fields.Date.today()
            record.days_to_expiry = (record.expiry_date - today).days if record.expiry_date else 0
            
            # Alert conditions
            record.is_expiring_soon = (
                record.state == 'active' and 
                0 <= record.days_to_expiry <= 30
            )
            
            record.is_low_availability = (
                record.state == 'active' and 
                record.percentage_used >= 90
            )
    
    @api.constrains('prefix')
    def _check_prefix_format(self):
        for record in self:
            if not record.prefix or len(record.prefix) != 3:
                raise ValidationError(_('NCF prefix must be exactly 3 characters long.'))
            if not record.prefix.isalnum():
                raise ValidationError(_('NCF prefix must contain only alphanumeric characters.'))
    
    @api.constrains('start_number', 'end_number', 'current_number')
    def _check_number_sequence(self):
        for record in self:
            if record.start_number >= record.end_number:
                raise ValidationError(_('End number must be greater than start number.'))
            if record.current_number < record.start_number:
                raise ValidationError(_('Current number cannot be less than start number.'))
            if record.current_number > record.end_number + 1:
                raise ValidationError(_('Current number cannot exceed end number + 1.'))
    
    @api.constrains('start_date', 'expiry_date')
    def _check_date_sequence(self):
        for record in self:
            if record.start_date >= record.expiry_date:
                raise ValidationError(_('Expiry date must be after start date.'))
    
    @api.constrains('prefix', 'document_type', 'company_id')
    def _check_unique_sequence(self):
        for record in self:
            existing = self.search([
                ('prefix', '=', record.prefix),
                ('document_type', '=', record.document_type),
                ('company_id', '=', record.company_id.id),
                ('id', '!=', record.id),
                ('state', 'in', ['active', 'inactive'])
            ])
            if existing:
                raise ValidationError(_(
                    'A sequence with prefix "%s" and document type "%s" already exists for this company.'
                ) % (record.prefix, record.document_type))
    
    def action_reactivate(self):
        """Reactivate sequence if conditions are met."""
        for record in self:
            if record.state == 'expired' and record.expiry_date >= fields.Date.today():
                record.state = 'active'
                record.message_post(body=_('Sequence reactivated'))
            elif record.state == 'inactive':
                record.state = 'active'
                record.message_post(body=_('Sequence reactivated'))
            else:
                raise UserError(_('Cannot reactivate sequence in current state.'))
    
    def action_deactivate(self):
        """Deactivate sequence."""
        for record in self:
            if record.state == 'active':
                record.state = 'inactive'
                record.message_post(body=_('Sequence deactivated'))
            else:
                raise UserError(_('Can only deactivate active sequences.'))
    
    def action_ncf_assignment_from_sequence(self):
        """Open NCF assignments related to this sequence."""
        self.ensure_one()
        return {
            'name': _('NCF Assignments'),
            'type': 'ir.actions.act_window',
            'res_model': 'ncf.assignment',
            'view_mode': 'tree,form',
            'domain': [('sequence_id', '=', self.id)],
            'context': {'default_sequence_id': self.id},
        }
    
    def get_next_ncf(self):
        """Get the next NCF number from this sequence."""
        self.ensure_one()
        
        # Check if sequence is active
        if self.state != 'active':
            raise UserError(_('Sequence %s is not active.') % self.prefix)
        
        # Check expiry date
        if self.expiry_date < fields.Date.today():
            self.state = 'expired'
            raise UserError(_('Sequence %s has expired.') % self.prefix)
        
        # Check if sequence is depleted
        if self.current_number > self.end_number:
            self.state = 'depleted'
            raise UserError(_('Sequence %s has been depleted.') % self.prefix)
        
        # Generate NCF number
        ncf_number = f"{self.prefix}{self.current_number:08d}"
        
        # Update current number
        self.current_number += 1
        
        # Update state if depleted
        if self.current_number > self.end_number:
            self.state = 'depleted'
            self.message_post(body=_('Sequence has been depleted'))
        
        _logger.info(f"Generated NCF: {ncf_number} from sequence {self.prefix}")
        return ncf_number
    
    @api.model
    def check_expiring_sequences(self):
        """Cron job to check for expiring sequences."""
        expiring_sequences = self.search([
            ('state', '=', 'active'),
            ('expiry_date', '<=', fields.Date.today() + timedelta(days=30)),
            ('expiry_date', '>', fields.Date.today()),
        ])
        
        for sequence in expiring_sequences:
            sequence.message_post(
                body=_('Sequence expires in %d days') % sequence.days_to_expiry,
                message_type='notification'
            )
    
    @api.model
    def check_low_availability_sequences(self):
        """Cron job to check for sequences with low availability."""
        low_availability_sequences = self.search([
            ('state', '=', 'active'),
            ('percentage_used', '>=', 90),
        ])
        
        for sequence in low_availability_sequences:
            sequence.message_post(
                body=_('Sequence availability is low: %.1f%% used') % sequence.percentage_used,
                message_type='notification'
            )
    
    def name_get(self):
        """Custom name display."""
        result = []
        for record in self:
            name = f"{record.prefix} - {record.document_type}"
            result.append((record.id, name))
        return result