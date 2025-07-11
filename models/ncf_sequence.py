# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class NCFSequence(models.Model):
    _name = 'ncf.sequence'
    _description = 'NCF Sequence Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'prefix, current_number'
    _rec_name = 'display_name'

    # Basic Information
    prefix = fields.Char(
        string='NCF Prefix',
        required=True,
        size=3,
        help='3-character NCF prefix (e.g., B02, E31)',
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
    ], string='Document Type', required=True)
    
    # Sequence Information
    current_number = fields.Integer(
        string='Current Number',
        default=1,
        help='Next number to be assigned'
    )
    
    start_number = fields.Integer(
        string='Start Number',
        default=1,
        required=True
    )
    
    end_number = fields.Integer(
        string='End Number',
        required=True,
        help='Last available number in this sequence'
    )
    
    # Date Management
    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.context_today
    )
    
    expiry_date = fields.Date(
        string='Expiry Date',
        required=True,
        help='Date when this NCF sequence expires'
    )
    
    # Status and Control
    state = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('depleted', 'Depleted'),
        ('inactive', 'Inactive'),
    ], string='Status', default='active', required=True, tracking=True)
    
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
        compute='_compute_available_numbers',
        store=True
    )
    
    used_numbers = fields.Integer(
        string='Used Numbers',
        compute='_compute_used_numbers',
        store=True
    )
    
    percentage_used = fields.Float(
        string='Percentage Used',
        compute='_compute_percentage_used',
        store=True
    )
    
    days_to_expiry = fields.Integer(
        string='Days to Expiry',
        compute='_compute_days_to_expiry',
        store=True
    )
    
    is_expiring_soon = fields.Boolean(
        string='Expiring Soon',
        compute='_compute_alerts',
        store=True
    )
    
    is_low_availability = fields.Boolean(
        string='Low Availability',
        compute='_compute_alerts',
        store=True
    )
    
    # Relations
    assignment_ids = fields.One2many(
        'ncf.assignment',
        'sequence_id',
        string='NCF Assignments'
    )
    
    @api.depends('prefix', 'document_type', 'current_number', 'end_number')
    def _compute_display_name(self):
        """Compute display name for the sequence."""
        for record in self:
            doc_type_name = dict(record._fields['document_type'].selection).get(record.document_type, '')
            record.display_name = f"{record.prefix} - {doc_type_name} ({record.current_number:08d}-{record.end_number:08d})"
    
    @api.depends('current_number', 'end_number')
    def _compute_available_numbers(self):
        """Compute available numbers in the sequence."""
        for record in self:
            record.available_numbers = max(0, record.end_number - record.current_number + 1)
    
    @api.depends('current_number', 'start_number')
    def _compute_used_numbers(self):
        """Compute used numbers in the sequence."""
        for record in self:
            record.used_numbers = max(0, record.current_number - record.start_number)
    
    @api.depends('used_numbers', 'end_number', 'start_number')
    def _compute_percentage_used(self):
        """Compute percentage of sequence used."""
        for record in self:
            total_numbers = record.end_number - record.start_number + 1
            if total_numbers > 0:
                record.percentage_used = (record.used_numbers / total_numbers) * 100
            else:
                record.percentage_used = 0
    
    @api.depends('expiry_date')
    def _compute_days_to_expiry(self):
        """Compute days until expiry."""
        for record in self:
            if record.expiry_date:
                today = fields.Date.context_today(record)
                delta = record.expiry_date - today
                record.days_to_expiry = delta.days
            else:
                record.days_to_expiry = 0
    
    @api.depends('days_to_expiry', 'percentage_used', 'company_id.ncf_alert_days', 'company_id.ncf_alert_percentage')
    def _compute_alerts(self):
        """Compute alert flags."""
        for record in self:
            alert_days = record.company_id.ncf_alert_days or 30
            alert_percentage = record.company_id.ncf_alert_percentage or 10
            
            # Check if expiring soon
            record.is_expiring_soon = (
                record.state == 'active' and 
                record.days_to_expiry <= alert_days and 
                record.days_to_expiry >= 0
            )
            
            # Check if low availability
            remaining_percentage = 100 - record.percentage_used
            record.is_low_availability = (
                record.state == 'active' and 
                remaining_percentage <= alert_percentage
            )
    
    @api.constrains('prefix')
    def _check_prefix(self):
        """Validate NCF prefix format."""
        for record in self:
            if not record.prefix or len(record.prefix) != 3:
                raise ValidationError(_('NCF prefix must be exactly 3 characters long.'))
            
            if not record.prefix.isalnum():
                raise ValidationError(_('NCF prefix must contain only alphanumeric characters.'))
    
    @api.constrains('start_number', 'end_number', 'current_number')
    def _check_numbers(self):
        """Validate number ranges."""
        for record in self:
            if record.start_number <= 0:
                raise ValidationError(_('Start number must be greater than 0.'))
            
            if record.end_number <= record.start_number:
                raise ValidationError(_('End number must be greater than start number.'))
            
            if record.current_number < record.start_number:
                raise ValidationError(_('Current number cannot be less than start number.'))
            
            if record.current_number > record.end_number:
                raise ValidationError(_('Current number cannot exceed end number.'))
    
    @api.constrains('start_date', 'expiry_date')
    def _check_dates(self):
        """Validate date ranges."""
        for record in self:
            if record.expiry_date <= record.start_date:
                raise ValidationError(_('Expiry date must be after start date.'))
    
    @api.constrains('prefix', 'document_type', 'company_id')
    def _check_unique_prefix_type(self):
        """Ensure unique prefix-document_type combination per company."""
        for record in self:
            existing = self.search([
                ('prefix', '=', record.prefix),
                ('document_type', '=', record.document_type),
                ('company_id', '=', record.company_id.id),
                ('state', 'in', ['active', 'inactive']),
                ('id', '!=', record.id),
            ])
            if existing:
                raise ValidationError(_(
                    'A sequence with prefix "%s" and document type "%s" already exists for this company.'
                ) % (record.prefix, dict(record._fields['document_type'].selection)[record.document_type]))
    
    def get_next_ncf(self):
        """Get the next available NCF number."""
        self.ensure_one()
        
        # Check if sequence is available
        if self.state != 'active':
            raise UserError(_('NCF sequence %s is not active.') % self.prefix)
        
        # Check expiry
        if self.expiry_date < fields.Date.context_today(self):
            self.state = 'expired'
            raise UserError(_('NCF sequence %s has expired.') % self.prefix)
        
        # Check availability
        if self.current_number > self.end_number:
            self.state = 'depleted'
            raise UserError(_('NCF sequence %s has been depleted.') % self.prefix)
        
        # Generate NCF
        ncf_number = f"{self.prefix}{self.current_number:08d}"
        
        # Increment current number
        self.current_number += 1
        
        # Check if depleted after increment
        if self.current_number > self.end_number:
            self.state = 'depleted'
        
        return ncf_number
    
    @api.model
    def update_sequence_states(self):
        """Cron job to update sequence states."""
        today = fields.Date.context_today(self)
        
        # Mark expired sequences
        expired_sequences = self.search([
            ('state', '=', 'active'),
            ('expiry_date', '<', today),
        ])
        expired_sequences.write({'state': 'expired'})
        
        # Send alerts for expiring and low availability sequences
        self._send_alerts()
        
        _logger.info('Updated %d NCF sequences to expired state', len(expired_sequences))
    
    def _send_alerts(self):
        """Send alerts for expiring and low availability sequences."""
        # Get sequences needing alerts
        alert_sequences = self.search([
            ('state', '=', 'active'),
            '|',
            ('is_expiring_soon', '=', True),
            ('is_low_availability', '=', True),
        ])
        
        for sequence in alert_sequences:
            sequence._send_sequence_alert()
    
    def _send_sequence_alert(self):
        """Send alert email for this sequence."""
        self.ensure_one()
        
        # Get users to notify (accounting managers and administrators)
        users_to_notify = self.env['res.users'].search([
            ('groups_id', 'in', [
                self.env.ref('account.group_account_manager').id,
                self.env.ref('base.group_system').id,
            ]),
            ('company_id', '=', self.company_id.id),
        ])
        
        if not users_to_notify:
            return
        
        # Prepare email content
        subject = _('NCF Alert: %s') % self.display_name
        
        if self.is_expiring_soon and self.is_low_availability:
            alert_type = _('expiring soon AND low availability')
        elif self.is_expiring_soon:
            alert_type = _('expiring soon')
        else:
            alert_type = _('low availability')
        
        body = _("""
        <p>Alert for NCF sequence: <strong>%s</strong></p>
        <p>Alert type: <strong>%s</strong></p>
        <ul>
            <li>Current number: %s</li>
            <li>Available numbers: %s</li>
            <li>Days to expiry: %s</li>
            <li>Percentage used: %.1f%%</li>
        </ul>
        <p>Please take action to avoid interruption in invoice processing.</p>
        """) % (
            self.display_name,
            alert_type,
            f"{self.current_number:08d}",
            self.available_numbers,
            self.days_to_expiry,
            self.percentage_used
        )
        
        # Send email to each user
        for user in users_to_notify:
            mail_values = {
                'subject': subject,
                'body_html': body,
                'email_to': user.email,
                'email_from': self.env.company.email or 'noreply@example.com',
                'auto_delete': True,
            }
            mail = self.env['mail.mail'].create(mail_values)
            mail.send()
    
    def action_reactivate(self):
        """Reactivate an inactive sequence."""
        for record in self:
            if record.state == 'inactive':
                record.state = 'active'
    
    def action_deactivate(self):
        """Deactivate an active sequence."""
        for record in self:
            if record.state == 'active':
                record.state = 'inactive'
