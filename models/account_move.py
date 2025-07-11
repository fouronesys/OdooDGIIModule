# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # NCF Fields
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
    
    @api.depends('move_type', 'company_id', 'partner_id')
    def _compute_requires_ncf(self):
        """Determine if this invoice requires NCF."""
        for move in self:
            move.requires_ncf = (
                move.move_type in ['out_invoice', 'out_refund'] and
                move.company_id.ncf_enabled and
                move.partner_id and
                move.partner_id.country_id.code == 'DO'
            )
    
    @api.onchange('ncf_document_type')
    def _onchange_ncf_document_type(self):
        """Clear NCF assignment when document type changes."""
        if self.ncf_document_type and self.ncf_assignment_id:
            # Check if document type matches sequence
            if self.ncf_assignment_id.document_type != self.ncf_document_type:
                self.ncf_assignment_id = False
                return {
                    'warning': {
                        'title': _('NCF Assignment Cleared'),
                        'message': _('The NCF assignment has been cleared because the document type changed.')
                    }
                }
    
    def action_assign_ncf(self):
        """Manually assign NCF to invoice."""
        for move in self:
            if not move.requires_ncf:
                raise UserError(_('This invoice does not require NCF assignment.'))
            
            if move.ncf_assignment_id:
                raise UserError(_('This invoice already has an NCF assignment.'))
            
            if not move.ncf_document_type:
                raise UserError(_('Please select an NCF document type first.'))
            
            move._assign_ncf()
    
    def _assign_ncf(self):
        """Internal method to assign NCF."""
        self.ensure_one()
        
        # Find active sequence for the document type
        NCFSequence = self.env['ncf.sequence']
        sequence = NCFSequence.search([
            ('document_type', '=', self.ncf_document_type),
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'active'),
        ], limit=1)
        
        if not sequence:
            raise UserError(_(
                'No active NCF sequence found for document type "%s".'
            ) % dict(self._fields['ncf_document_type'].selection)[self.ncf_document_type])
        
        try:
            # Get next NCF number
            ncf_number = sequence.get_next_ncf()
            
            # Create NCF assignment
            NCFAssignment = self.env['ncf.assignment']
            assignment = NCFAssignment.create({
                'ncf_number': ncf_number,
                'sequence_id': sequence.id,
                'invoice_id': self.id,
                'company_id': self.company_id.id,
            })
            
            # Link assignment to invoice
            self.ncf_assignment_id = assignment.id
            
            # Log the assignment
            self.message_post(
                body=_('NCF %s assigned from sequence %s') % (ncf_number, sequence.prefix),
                message_type='notification'
            )
            
            _logger.info(f"NCF {ncf_number} assigned to invoice {self.name}")
            
        except Exception as e:
            _logger.error(f"Error assigning NCF to invoice {self.name}: {str(e)}")
            raise UserError(_('Error assigning NCF: %s') % str(e))
    
    def action_post(self):
        """Override to auto-assign NCF on posting."""
        # First, call the parent method
        result = super(AccountMove, self).action_post()
        
        # Then handle NCF assignment for invoices that require it
        for move in self:
            if move.requires_ncf and not move.ncf_assignment_id:
                if move.ncf_document_type:
                    try:
                        move._assign_ncf()
                    except Exception as e:
                        _logger.warning(f"Could not auto-assign NCF to invoice {move.name}: {str(e)}")
                        # Don't prevent posting if NCF assignment fails
                        # User can manually assign later
                        move.message_post(
                            body=_('Could not auto-assign NCF: %s. Please assign manually.') % str(e),
                            message_type='notification'
                        )
        
        return result
    
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
        # Delete related NCF assignments first
        ncf_assignments = self.mapped('ncf_assignment_id')
        if ncf_assignments:
            ncf_assignments.unlink()
        
        return super(AccountMove, self).unlink()
    
    def action_view_ncf_assignment(self):
        """Open NCF assignment form."""
        self.ensure_one()
        if not self.ncf_assignment_id:
            raise UserError(_('This invoice does not have an NCF assignment.'))
        
        return {
            'name': _('NCF Assignment'),
            'type': 'ir.actions.act_window',
            'res_model': 'ncf.assignment',
            'view_mode': 'form',
            'res_id': self.ncf_assignment_id.id,
            'target': 'new',
        }