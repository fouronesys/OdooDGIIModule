# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    # NCF Management Configuration
    ncf_management_enabled = fields.Boolean(
        string='Enable NCF Management',
        default=False,
        help='Enable NCF (Número de Comprobante Fiscal) management for Dominican Republic compliance'
    )
    
    ncf_alert_days = fields.Integer(
        string='Alert Days Before Expiry',
        default=30,
        help='Number of days before NCF sequence expiry to show alerts'
    )
    
    ncf_alert_percentage = fields.Float(
        string='Alert Percentage for Low Availability',
        default=10.0,
        help='Percentage of remaining NCFs to trigger low availability alerts'
    )
    
    ncf_auto_assign = fields.Boolean(
        string='Auto-assign NCF on Invoice Posting',
        default=True,
        help='Automatically assign NCF when posting invoices'
    )
    
    # DGII Configuration
    dgii_rnc = fields.Char(
        string='RNC (DGII Registration Number)',
        help='Company RNC for DGII reporting'
    )
    
    dgii_name = fields.Char(
        string='DGII Registered Name',
        help='Company name as registered with DGII'
    )
    
    @api.onchange('country_id')
    def _onchange_country_id(self):
        """Auto-enable NCF management for Dominican companies."""
        if self.country_id and self.country_id.code == 'DO':
            self.ncf_management_enabled = True
        else:
            self.ncf_management_enabled = False
