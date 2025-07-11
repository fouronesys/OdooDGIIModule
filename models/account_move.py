# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    # NCF Related Fields
    ncf_assignment_id = fields.Many2one(
        'ncf.assignment',
        string='NCF Assignment',
        readonly=True,
        copy=False
    )
    
    ncf_number = fields.Char(
        related='ncf_assignment_id.ncf_number',
        string='NCF Number',
        store=True,
        readonly=True
    )
    
    ncf_document_type = fields.Selection([
        ('invoice', 'Factura de Crédito Fiscal'),
        ('invoice_consumer', 'Factura de Consumo'),
        ('debit_note', 'Nota de Débito'),
        ('credit_note', 'Nota de Crédito'),
        ('informal', 'Comprobante de Compras'),
        ('unique', 'Comprobante Único de Ingresos'),
        ('minor_expenses', 'Comprobante de Gastos Menores'),
        ('exterior', 'Comprobante de Operaciones Exteriores'),
        ('payments', 'Comprobante de Pagos'),
    ], string='NCF Document Type', copy=False)
    
    requires_ncf = fields.Boolean(
        string='Requires NCF',
        compute='_compute_requires_ncf',
        store=True
    )
    
    @api.depends('company_id', 'move_type', 'partner_id')
    def _compute_requires_ncf(self):
        """Determine if this invoice requires NCF."""
        for move in self:
            # Only for Dominican companies and customer invoices/credit notes
            move.requires_ncf = (
                move.company_id.country_id.code == 'DO' and
                move.company_id.ncf_management_enabled and
                move.move_type in ['out_invoice', 'out_refund'] and
                move.partner_id
            )
    
    @api.onchange('ncf_document_type')
    def _onchange_ncf_document_type(self):
        """Clear NCF assignment when document type changes."""
        if self.ncf_assignment_id and self.ncf_document_type != self.ncf_assignment_id.document_type:
            self.ncf_assignment_id = False
    
    def action_assign_ncf(self):
        """Manually assign NCF to invoice."""
        self.ensure_one()
        
        if not self.requires_ncf:
            raise UserError(_('This invoice does not require NCF assignment.'))
        
        if self.ncf_assignment_id:
            raise UserError(_('This invoice already has an NCF assigned: %s') % self.ncf_number)
        
        if not self.ncf_document_type:
            raise UserError(_('Please select an NCF document type before assigning NCF.'))
        
        self._assign_ncf()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('NCF Assigned'),
                'message': _('NCF %s has been assigned to this invoice.') % self.ncf_number,
                'type': 'success',
            }
        }
    
    def _assign_ncf(self):
        """Internal method to assign NCF."""
        self.ensure_one()
        
        if not self.ncf_document_type:
            # Auto-determine document type based on move type
            if self.move_type == 'out_invoice':
                self.ncf_document_type = 'invoice'
            elif self.move_type == 'out_refund':
                self.ncf_document_type = 'credit_note'
        
        # Find active sequence for this document type
        sequence = self.env['ncf.sequence'].search([
            ('document_type', '=', self.ncf_document_type),
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'active'),
        ], limit=1, order='current_number')
        
        if not sequence:
            raise UserError(_(
                'No active NCF sequence found for document type "%s". '
                'Please configure NCF sequences in the NCF Management module.'
            ) % dict(self._fields['ncf_document_type'].selection)[self.ncf_document_type])
        
        # Get next NCF number
        try:
            ncf_number = sequence.get_next_ncf()
        except UserError as e:
            raise UserError(_(
                'Cannot assign NCF: %s\n\n'
                'Please contact your administrator to configure new NCF sequences.'
            ) % str(e))
        
        # Create NCF assignment
        assignment = self.env['ncf.assignment'].create({
            'ncf_number': ncf_number,
            'sequence_id': sequence.id,
            'invoice_id': self.id,
            'company_id': self.company_id.id,
        })
        
        self.ncf_assignment_id = assignment.id
    
    def action_post(self):
        """Override to auto-assign NCF on posting."""
        # Auto-assign NCF for invoices that require it
        for move in self:
            if move.requires_ncf and not move.ncf_assignment_id and move.state == 'draft':
                move._assign_ncf()
        
        return super().action_post()
    
    @api.constrains('state', 'requires_ncf', 'ncf_assignment_id')
    def _check_ncf_required(self):
        """Validate that posted invoices have NCF when required."""
        for move in self:
            if (move.state == 'posted' and 
                move.requires_ncf and 
                not move.ncf_assignment_id):
                raise ValidationError(_(
                    'Invoice %s requires NCF assignment before posting.'
                ) % move.name)
    
    def unlink(self):
        """Override to handle NCF assignment deletion."""
        # Store NCF assignments to delete
        ncf_assignments = self.mapped('ncf_assignment_id')
        
        result = super().unlink()
        
        # Delete orphaned NCF assignments
        if ncf_assignments:
            ncf_assignments.unlink()
        
        return result
    
    def action_view_ncf_assignment(self):
        """Open NCF assignment form."""
        self.ensure_one()
        
        if not self.ncf_assignment_id:
            raise UserError(_('This invoice does not have an NCF assignment.'))
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ncf.assignment',
            'res_id': self.ncf_assignment_id.id,
            'view_mode': 'form',
            'target': 'new',
        }
