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
        string='Número NCF',
        store=True,
        readonly=True,
        help='Número de Comprobante Fiscal asignado a esta factura'
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
    ], string='Tipo de NCF', copy=False, 
       help='Tipo de Número de Comprobante Fiscal según DGII')
    
    requires_ncf = fields.Boolean(
        string='Requiere NCF',
        compute='_compute_requires_ncf',
        store=True,
        help='Indica si esta factura requiere un Número de Comprobante Fiscal'
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
        """Auto-assign NCF when document type is selected."""
        if self.ncf_document_type:
            # Clear existing assignment if document type doesn't match
            if self.ncf_assignment_id and self.ncf_assignment_id.document_type != self.ncf_document_type:
                self.ncf_assignment_id = False
            
            # Auto-assign NCF if requirements are met
            if (self.requires_ncf and not self.ncf_assignment_id and 
                self.state == 'draft' and self.company_id and self.partner_id):
                try:
                    self._assign_ncf_onchange()
                    return {
                        'warning': {
                            'title': _('NCF Asignado'),
                            'message': _('NCF %s asignado automáticamente para tipo "%s"') % (
                                self.ncf_number,
                                dict(self._fields['ncf_document_type'].selection)[self.ncf_document_type]
                            )
                        }
                    }
                except Exception as e:
                    return {
                        'warning': {
                            'title': _('No se pudo asignar NCF'),
                            'message': _('Error: %s. Use el botón "Asignar NCF" después de guardar.') % str(e)
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
    
    def _assign_ncf_onchange(self):
        """Internal method to assign NCF during onchange (less strict validation)."""
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
        
        # Get next NCF number (but don't update sequence yet - wait for save)
        next_number = sequence.current_number
        if next_number > sequence.end_number:
            raise UserError(_('NCF sequence %s has been exhausted.') % sequence.prefix)
        
        # Format NCF number (prefix + 8-digit number)
        ncf_number = f"{sequence.prefix}{str(next_number).zfill(8)}"
        
        # For onchange, we'll simulate the assignment without actually creating records
        # The real assignment will happen when the record is saved
        self.ncf_number = ncf_number
        
        _logger.info(f"NCF {ncf_number} prepared for assignment to invoice {self.name or 'new'} via onchange")
    
    @api.model
    def create(self, vals):
        """Override create to handle NCF assignment."""
        # Create the record first
        record = super(AccountMove, self).create(vals)
        
        # Handle NCF assignment if needed
        if (record.requires_ncf and record.ncf_document_type and 
            not record.ncf_assignment_id and record.state == 'draft'):
            try:
                record._assign_ncf()
            except Exception as e:
                _logger.warning(f"Could not auto-assign NCF during creation: {str(e)}")
        
        return record
    
    def write(self, vals):
        """Override write to handle NCF assignment."""
        result = super(AccountMove, self).write(vals)
        
        # Handle NCF assignment if document type changed
        if 'ncf_document_type' in vals:
            for record in self:
                if (record.requires_ncf and record.ncf_document_type and 
                    not record.ncf_assignment_id and record.state == 'draft'):
                    try:
                        record._assign_ncf()
                    except Exception as e:
                        _logger.warning(f"Could not auto-assign NCF during write: {str(e)}")
        
        return result
    
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