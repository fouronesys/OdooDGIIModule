# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    # NCF Configuration
    ncf_enabled = fields.Boolean(
        string='Enable NCF Management',
        default=False,
        help='Enable NCF (Número de Comprobante Fiscal) management for this company'
    )
    
    dgii_rnc = fields.Char(
        string='RNC (DGII)',
        size=11,
        help='Registro Nacional de Contribuyentes - Tax ID number'
    )
    
    # Alert Thresholds
    ncf_expiry_alert_days = fields.Integer(
        string='NCF Expiry Alert Days',
        default=30,
        help='Number of days before expiry to show alerts'
    )
    
    ncf_low_availability_threshold = fields.Float(
        string='Low Availability Threshold (%)',
        default=90.0,
        help='Percentage threshold for low availability alerts'
    )
    
    # Notification Settings
    ncf_notification_enabled = fields.Boolean(
        string='Enable NCF Notifications',
        default=True,
        help='Enable automatic notifications for NCF alerts'
    )
    
    ncf_notification_user_ids = fields.Many2many(
        'res.users',
        string='NCF Notification Users',
        help='Users who will receive NCF notifications'
    )
    
    @api.constrains('dgii_rnc')
    def _check_dgii_rnc(self):
        for record in self:
            if record.dgii_rnc and not record.dgii_rnc.isdigit():
                raise ValidationError(_('RNC must contain only digits.'))
            if record.dgii_rnc and len(record.dgii_rnc) not in [9, 11]:
                raise ValidationError(_('RNC must be 9 or 11 digits long.'))
    
    @api.constrains('ncf_expiry_alert_days')
    def _check_expiry_alert_days(self):
        for record in self:
            if record.ncf_expiry_alert_days < 1:
                raise ValidationError(_('NCF expiry alert days must be greater than 0.'))
    
    @api.constrains('ncf_low_availability_threshold')
    def _check_low_availability_threshold(self):
        for record in self:
            if not (0 <= record.ncf_low_availability_threshold <= 100):
                raise ValidationError(_('Low availability threshold must be between 0 and 100.'))
    
    def get_ncf_statistics(self):
        """Get NCF statistics for this company."""
        self.ensure_one()
        
        NCFSequence = self.env['ncf.sequence']
        
        # Get all sequences for this company
        sequences = NCFSequence.search([('company_id', '=', self.id)])
        
        # Calculate statistics
        total_sequences = len(sequences)
        active_sequences = len(sequences.filtered(lambda s: s.state == 'active'))
        expiring_sequences = len(sequences.filtered(lambda s: s.is_expiring_soon))
        low_availability_sequences = len(sequences.filtered(lambda s: s.is_low_availability))
        
        return {
            'total_sequences': total_sequences,
            'active_sequences': active_sequences,
            'expiring_sequences': expiring_sequences,
            'low_availability_sequences': low_availability_sequences,
        }