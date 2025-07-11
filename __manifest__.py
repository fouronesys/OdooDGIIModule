# -*- coding: utf-8 -*-
{
    'name': 'NCF Management for Dominican Republic',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'NCF (Número de Comprobante Fiscal) management for Dominican Republic DGII compliance',
    'description': """
NCF Management Module for Dominican Republic
============================================

This module provides comprehensive NCF (Número de Comprobante Fiscal) management
for Dominican Republic businesses to ensure DGII compliance.

Features:
---------
* Automatic sequential NCF number assignment
* NCF prefix and sequence management
* Expiration date tracking with alerts
* Integration with invoice creation process
* DGII reports (606/607)
* Dashboard with NCF status and alerts
* Strict validation and access controls

Requirements:
-------------
* Odoo 17.0+
* Dominican Republic localization
    """,
    'author': 'NCF Management Team',
    'website': 'https://www.example.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'mail',
        'web',
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/ncf_document_types.xml',
        
        # Views
        'views/ncf_sequence_views.xml',
        'views/ncf_assignment_views.xml',
        'views/account_move_views.xml',
        'views/ncf_dashboard_views.xml',
        'views/menu_views.xml',
        
        # Wizards
        'wizards/ncf_sequence_wizard_views.xml',
        
        # Reports
        'reports/dgii_reports_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'post_init_hook': '_post_init_hook',
}

def _post_init_hook(cr, registry):
    """Post-installation hook to set up default NCF sequences."""
    from odoo import api, SUPERUSER_ID
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Set up default company NCF configuration
    companies = env['res.company'].search([])
    for company in companies:
        if not company.country_id or company.country_id.code != 'DO':
            continue
            
        # Enable NCF management for Dominican companies
        company.write({
            'ncf_management_enabled': True,
            'ncf_alert_days': 30,
            'ncf_alert_percentage': 10,
        })
