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
        # Security groups and access rights (must be loaded first)
        'security/security.xml',
        'security/ir.model.access.csv',
        
        # Default data (loaded early)
        'data/ncf_document_types.xml',
        
        # Views (core views first)
        'views/ncf_sequence_views.xml',
        'views/ncf_assignment_views.xml',
        'views/account_move_views.xml',
        'views/ncf_invoice_form.xml',
        'views/ncf_dashboard_views.xml',
        
        # Wizards
        'wizards/ncf_sequence_wizard_views.xml',
        
        # Reports (must be loaded before menu that references them)
        'reports/dgii_reports_views.xml',
        'reports/invoice_report_ncf_standalone.xml',
        
        # Menu views (loaded last to ensure all actions exist)
        'views/menu_views.xml',
        'views/dgii_reports_menu.xml',
    ],

    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}