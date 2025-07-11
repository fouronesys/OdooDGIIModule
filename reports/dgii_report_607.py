# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import base64
import csv
import io


class DGIIReport607(models.TransientModel):
    _name = 'dgii.report.607'
    _description = 'DGII Report 607 - Purchases'

    # Report Parameters
    date_from = fields.Date(
        string='From Date',
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1)
    )
    
    date_to = fields.Date(
        string='To Date',
        required=True,
        default=fields.Date.context_today
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    # Report Content
    line_ids = fields.One2many(
        'dgii.report.607.line',
        'report_id',
        string='Report Lines'
    )
    
    # Export Fields
    export_format = fields.Selection([
        ('csv', 'CSV File'),
        ('txt', 'TXT File'),
    ], string='Export Format', default='txt')
    
    export_file = fields.Binary(
        string='Export File',
        readonly=True
    )
    
    export_filename = fields.Char(
        string='Export Filename',
        readonly=True
    )
    
    # Statistics
    total_records = fields.Integer(
        string='Total Records',
        compute='_compute_statistics'
    )
    
    total_amount = fields.Monetary(
        string='Total Amount',
        compute='_compute_statistics'
    )
    
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Currency'
    )
    
    @api.depends('line_ids')
    def _compute_statistics(self):
        """Compute report statistics."""
        for report in self:
            report.total_records = len(report.line_ids)
            report.total_amount = sum(line.total_amount for line in report.line_ids)
    
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Validate date range."""
        for report in self:
            if report.date_to < report.date_from:
                raise ValidationError(_('End date must be after start date.'))
    
    def action_generate_report(self):
        """Generate the DGII 607 report."""
        self.ensure_one()
        
        # Clear existing lines
        self.line_ids.unlink()
        
        # Get vendor bills in date range
        bills = self.env['account.move'].search([
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'posted'),
            ('move_type', 'in', ['in_invoice', 'in_refund']),
        ], order='invoice_date, name')
        
        # Create report lines
        line_vals = []
        for bill in bills:
            # Get supplier NCF from reference or specific field
            supplier_ncf = bill.ref or ''
            
            # Validate NCF format
            ncf_valid = self._validate_supplier_ncf(supplier_ncf)
            
            # Calculate amounts
            subtotal = bill.amount_untaxed
            tax_amount = bill.amount_tax
            total_amount = bill.amount_total
            
            # Determine document type
            doc_type = 'invoice' if bill.move_type == 'in_invoice' else 'credit_note'
            doc_type_code = self._get_dgii_doc_type_code(doc_type)
            
            line_vals.append({
                'report_id': self.id,
                'supplier_ncf': supplier_ncf,
                'ncf_valid': ncf_valid,
                'document_type_code': doc_type_code,
                'invoice_date': bill.invoice_date,
                'invoice_id': bill.id,
                'partner_name': bill.partner_id.name,
                'partner_vat': bill.partner_id.vat or '',
                'subtotal': subtotal,
                'tax_amount': tax_amount,
                'total_amount': total_amount,
                'currency_code': bill.currency_id.name,
            })
        
        if line_vals:
            self.env['dgii.report.607.line'].create(line_vals)
        
        # Return to form view
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'dgii.report.607',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def _validate_supplier_ncf(self, ncf):
        """Validate supplier NCF format."""
        if not ncf:
            return False
        
        # Remove spaces and convert to uppercase
        ncf = ncf.replace(' ', '').upper()
        
        # Check length (should be 11 characters)
        if len(ncf) != 11:
            return False
        
        # Check format: 3 letters/numbers + 8 digits
        prefix = ncf[:3]
        number = ncf[3:]
        
        if not prefix.isalnum() or not number.isdigit():
            return False
        
        return True
    
    def _get_dgii_doc_type_code(self, document_type):
        """Get DGII document type code for purchases."""
        mapping = {
            'invoice': '01',  # Purchase invoice
            'credit_note': '03',  # Purchase credit note
            'debit_note': '02',  # Purchase debit note
        }
        return mapping.get(document_type, '01')
    
    def action_export_report(self):
        """Export report to file."""
        self.ensure_one()
        
        if not self.line_ids:
            raise ValidationError(_('Please generate the report first.'))
        
        if self.export_format == 'csv':
            content, filename = self._export_csv()
        else:  # txt
            content, filename = self._export_txt()
        
        self.write({
            'export_file': base64.b64encode(content),
            'export_filename': filename,
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=dgii.report.607&id={self.id}&field=export_file&download=true&filename={filename}',
            'target': 'self',
        }
    
    def _export_csv(self):
        """Export to CSV format."""
        output = io.StringIO()
        writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        
        # Header
        writer.writerow([
            'NCF Proveedor',
            'Tipo Doc',
            'Fecha',
            'Proveedor',
            'RNC/Cedula',
            'Subtotal',
            'Impuesto',
            'Total',
            'Moneda',
            'NCF Válido'
        ])
        
        # Data rows
        for line in self.line_ids:
            writer.writerow([
                line.supplier_ncf,
                line.document_type_code,
                line.invoice_date.strftime('%d/%m/%Y'),
                line.partner_name,
                line.partner_vat,
                f"{line.subtotal:.2f}",
                f"{line.tax_amount:.2f}",
                f"{line.total_amount:.2f}",
                line.currency_code,
                'Sí' if line.ncf_valid else 'No',
            ])
        
        content = output.getvalue().encode('utf-8')
        filename = f'DGII_607_{self.date_from.strftime("%Y%m")}_{self.company_id.dgii_rnc or "SIN_RNC"}.csv'
        
        return content, filename
    
    def _export_txt(self):
        """Export to TXT format (DGII standard)."""
        lines = []
        
        for line in self.line_ids:
            # Format according to DGII specifications
            record = (
                f"{line.supplier_ncf:<11}"
                f"{line.document_type_code:<2}"
                f"{line.invoice_date.strftime('%d%m%Y'):<8}"
                f"{line.partner_vat:<11}"
                f"{line.partner_name[:50]:<50}"
                f"{int(line.subtotal * 100):>12}"
                f"{int(line.tax_amount * 100):>12}"
                f"{int(line.total_amount * 100):>12}"
            )
            lines.append(record)
        
        content = '\n'.join(lines).encode('utf-8')
        filename = f'607{self.date_from.strftime("%Y%m")}{self.company_id.dgii_rnc or "00000000000"}.txt'
        
        return content, filename


class DGIIReport607Line(models.TransientModel):
    _name = 'dgii.report.607.line'
    _description = 'DGII Report 607 Line'
    _order = 'invoice_date, supplier_ncf'

    report_id = fields.Many2one(
        'dgii.report.607',
        string='Report',
        required=True,
        ondelete='cascade'
    )
    
    supplier_ncf = fields.Char(
        string='Supplier NCF',
        required=True
    )
    
    ncf_valid = fields.Boolean(
        string='NCF Valid',
        default=False
    )
    
    document_type_code = fields.Char(
        string='Document Type Code',
        required=True
    )
    
    invoice_date = fields.Date(
        string='Invoice Date',
        required=True
    )
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        required=True
    )
    
    partner_name = fields.Char(
        string='Supplier Name',
        required=True
    )
    
    partner_vat = fields.Char(
        string='Supplier VAT'
    )
    
    subtotal = fields.Monetary(
        string='Subtotal',
        required=True
    )
    
    tax_amount = fields.Monetary(
        string='Tax Amount',
        required=True
    )
    
    total_amount = fields.Monetary(
        string='Total Amount',
        required=True
    )
    
    currency_code = fields.Char(
        string='Currency Code',
        required=True
    )
    
    currency_id = fields.Many2one(
        related='report_id.currency_id',
        string='Currency'
    )
