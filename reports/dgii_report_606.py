# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
import base64
import csv
import io
import xlsxwriter


class DGIIReport606(models.TransientModel):
    _name = 'dgii.report.606'
    _description = 'DGII Report 606 - Sales'

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
        'dgii.report.606.line',
        'report_id',
        string='Report Lines'
    )
    
    # Export Fields
    export_format = fields.Selection([
        ('txt', 'TXT File (DGII Format)'),
        ('xlsx', 'Excel File (XLSX)'),
        ('csv', 'CSV File'),
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
        """Generate the DGII 606 report."""
        self.ensure_one()
        
        # Clear existing lines
        self.line_ids.unlink()
        
        # Get NCF assignments in date range
        assignments = self.env['ncf.assignment'].search([
            ('assignment_date', '>=', self.date_from),
            ('assignment_date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
            ('invoice_state', '=', 'posted'),
            ('invoice_id.move_type', 'in', ['out_invoice', 'out_refund']),
        ], order='assignment_date, ncf_number')
        
        # Create report lines
        line_vals = []
        for assignment in assignments:
            invoice = assignment.invoice_id
            
            # Calculate amounts
            subtotal = invoice.amount_untaxed
            tax_amount = invoice.amount_tax
            total_amount = invoice.amount_total
            
            # Determine document type code for DGII
            doc_type_code = self._get_dgii_doc_type_code(assignment.document_type)
            
            line_vals.append({
                'report_id': self.id,
                'ncf_number': assignment.ncf_number,
                'document_type_code': doc_type_code,
                'invoice_date': invoice.invoice_date,
                'invoice_id': invoice.id,
                'partner_name': invoice.partner_id.name,
                'partner_vat': invoice.partner_id.vat or '',
                'subtotal': subtotal,
                'tax_amount': tax_amount,
                'total_amount': total_amount,
                'currency_code': invoice.currency_id.name,
            })
        
        if line_vals:
            self.env['dgii.report.606.line'].create(line_vals)
        
        # Return to form view
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'dgii.report.606',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def _get_dgii_doc_type_code(self, document_type):
        """Get DGII document type code."""
        mapping = {
            'invoice': '31',
            'invoice_consumer': '02',
            'credit_note': '43',
            'debit_note': '44',
            'informal': '11',
            'unique': '12',
            'minor_expenses': '13',
            'exterior': '14',
            'payments': '15',
        }
        return mapping.get(document_type, '31')
    
    def action_export_report(self):
        """Export report to file."""
        self.ensure_one()
        
        if not self.line_ids:
            raise ValidationError(_('Please generate the report first.'))
        
        if self.export_format == 'csv':
            content, filename = self._export_csv()
        elif self.export_format == 'xlsx':
            content, filename = self._export_xlsx()
        else:  # txt
            content, filename = self._export_txt()
        
        self.write({
            'export_file': base64.b64encode(content),
            'export_filename': filename,
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=dgii.report.606&id={self.id}&field=export_file&download=true&filename={filename}',
            'target': 'self',
        }
    
    def _export_csv(self):
        """Export to CSV format."""
        output = io.StringIO()
        writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        
        # Header
        writer.writerow([
            'NCF',
            'Tipo Doc',
            'Fecha',
            'Cliente',
            'RNC/Cedula',
            'Subtotal',
            'Impuesto',
            'Total',
            'Moneda'
        ])
        
        # Data rows
        for line in self.line_ids:
            writer.writerow([
                line.ncf_number,
                line.document_type_code,
                line.invoice_date.strftime('%d/%m/%Y'),
                line.partner_name,
                line.partner_vat,
                f"{line.subtotal:.2f}",
                f"{line.tax_amount:.2f}",
                f"{line.total_amount:.2f}",
                line.currency_code,
            ])
        
        content = output.getvalue().encode('utf-8')
        filename = f'DGII_606_{self.date_from.strftime("%Y%m")}_{self.company_id.dgii_rnc or "SIN_RNC"}.csv'
        
        return content, filename
    
    def _export_txt(self):
        """Export to TXT format (DGII standard)."""
        lines = []
        
        for line in self.line_ids:
            # Format according to DGII specifications
            # Fields: RNC|Tipo|NCF|Fecha|Cliente|RNC_Cliente|Subtotal|Impuesto|Total
            dgii_line = "|".join([
                self.company_id.dgii_rnc or "",
                line.document_type_code,
                line.ncf_number,
                line.invoice_date.strftime('%d/%m/%Y'),
                line.partner_name.replace("|", " "),
                line.partner_vat or "",
                f"{line.subtotal:.2f}",
                f"{line.tax_amount:.2f}",
                f"{line.total_amount:.2f}",
            ])
            lines.append(dgii_line)
        
        content = "\n".join(lines).encode('utf-8')
        filename = f'DGII_606_{self.date_from.strftime("%Y%m")}_{self.company_id.dgii_rnc or "SIN_RNC"}.txt'
        
        return content, filename
    
    def _export_xlsx(self):
        """Export to Excel format."""
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Reporte 606')
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9EDF7',
            'font_color': '#31708F',
            'border': 1
        })
        
        money_format = workbook.add_format({
            'num_format': '#,##0.00',
            'border': 1
        })
        
        text_format = workbook.add_format({
            'border': 1
        })
        
        date_format = workbook.add_format({
            'num_format': 'dd/mm/yyyy',
            'border': 1
        })
        
        # Headers
        headers = [
            'NCF',
            'Tipo Documento',
            'Fecha Factura',
            'Cliente',
            'RNC/Cédula',
            'Subtotal',
            'Impuesto',
            'Total',
            'Moneda'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Data rows
        for row, line in enumerate(self.line_ids, 1):
            worksheet.write(row, 0, line.ncf_number, text_format)
            worksheet.write(row, 1, line.document_type_code, text_format)
            worksheet.write(row, 2, line.invoice_date, date_format)
            worksheet.write(row, 3, line.partner_name, text_format)
            worksheet.write(row, 4, line.partner_vat, text_format)
            worksheet.write(row, 5, line.subtotal, money_format)
            worksheet.write(row, 6, line.tax_amount, money_format)
            worksheet.write(row, 7, line.total_amount, money_format)
            worksheet.write(row, 8, line.currency_code, text_format)
        
        # Auto-adjust column widths
        for col in range(len(headers)):
            worksheet.set_column(col, col, 15)
        
        # Add totals row
        total_row = len(self.line_ids) + 2
        worksheet.write(total_row, 4, 'TOTALES:', header_format)
        worksheet.write(total_row, 5, f'=SUM(F2:F{len(self.line_ids)+1})', money_format)
        worksheet.write(total_row, 6, f'=SUM(G2:G{len(self.line_ids)+1})', money_format)
        worksheet.write(total_row, 7, f'=SUM(H2:H{len(self.line_ids)+1})', money_format)
        
        workbook.close()
        content = output.getvalue()
        filename = f'DGII_606_{self.date_from.strftime("%Y%m")}_{self.company_id.dgii_rnc or "SIN_RNC"}.xlsx'
        
        return content, filename


class DGIIReport606Line(models.TransientModel):
    _name = 'dgii.report.606.line'
    _description = 'DGII Report 606 Line'
    _order = 'invoice_date, ncf_number'

    report_id = fields.Many2one(
        'dgii.report.606',
        string='Report',
        required=True,
        ondelete='cascade'
    )
    
    ncf_number = fields.Char(
        string='NCF Number',
        required=True
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
        string='Customer Name',
        required=True
    )
    
    partner_vat = fields.Char(
        string='Customer VAT'
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
