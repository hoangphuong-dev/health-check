from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import timedelta


class ProcedureGroupLine(models.Model):
    _name = "procedure.group.line"
    _description = "Procedure Group Line"
    _order = 'sequence'

    sequence = fields.Integer("Sequence", default=10)
    group_id = fields.Many2one('procedure.group', ondelete='restrict', string='Procedure Group')
    product_id = fields.Many2one('product.product', string='Procedure', ondelete='restrict', required=True)
    days_to_add = fields.Integer('Days to add', help="Days to add for next date")
    procedure_time = fields.Float(related='product_id.procedure_time', string='Procedure Time', readonly=True)
    price_unit = fields.Float(related='product_id.list_price', string='Price', readonly=True)


class ProcedureGroup(models.Model):
    _name = "procedure.group"
    _description = "Procedure Group"

    name = fields.Char(string='Group Name', required=True)
    line_ids = fields.One2many('procedure.group.line', 'group_id', string='Group lines')


class MatePatientProcedure(models.Model):
    _name = "mate_hms.patient.procedure"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'mate_hms.mixin', 'mate_hms.document.mixin']
    _description = "Patient Procedure"
    _order = "id desc"

    @api.depends('date', 'date_stop')
    def mate_get_duration(self):
        for rec in self:
            duration = 0.0
            if rec.date and rec.date_stop:
                diff = rec.date_stop - rec.date
                duration = (diff.days * 24) + (diff.seconds / 3600)
            rec.duration = duration

    def _mate_get_attachemnts(self):
        attachments = super(MatePatientProcedure, self)._mate_get_attachemnts()
        attachments += self.appointment_ids.mapped('attachment_ids')
        return attachments

    name = fields.Char(string="Name", tracking=1)
    patient_id = fields.Many2one('mate_hms.patient', string='Patient', required=True, tracking=1)
    product_id = fields.Many2one('product.product', string='Procedure', change_default=True, ondelete='restrict', required=True)
    price_unit = fields.Float("Price")
    invoice_id = fields.Many2one('account.move', string='Invoice', copy=False)
    physician_id = fields.Many2one('mate_hms.physician', ondelete='restrict', string='Physician', index=True)
    state = fields.Selection([('scheduled', 'Scheduled'), ('running', 'Running'), ('done', 'Done'), ('cancel', 'Canceled')], string='Status', default='scheduled', tracking=1)
    company_id = fields.Many2one('res.company', ondelete='restrict', string='Hospital', default=lambda self: self.env.company)
    date = fields.Datetime("Date")
    date_stop = fields.Datetime("End Date")
    duration = fields.Float('Duration', compute="mate_get_duration", store=True)

    diseas_id = fields.Many2one('mate_hms.diseases', 'Disease')
    description = fields.Text(string="Description")
    treatment_id = fields.Many2one('hms.treatment', 'Treatment')
    appointment_ids = fields.Many2many('mate_hms.appointment', 'mate_appointment_procedure_rel', 'appointment_id', 'procedure_id', 'Appointments')
    department_id = fields.Many2one('hr.department', ondelete='restrict', domain=[('patient_department', '=', True)], string='Department', tracking=1)
    department_type = fields.Selection(related='department_id.department_type', string="Appointment Department", store=True)

    consumable_line_ids = fields.One2many('mate_hms.consumable.line', 'procedure_id', string='Consumable Line', copy=False)
    mate_kit_id = fields.Many2one('mate_hms.product.kit', string='Kit')
    mate_kit_qty = fields.Integer("Kit Qty", default=1)
    invoice_exempt = fields.Boolean(string='Invoice Exempt')

    @api.model
    def default_get(self, fields):
        res = super(MatePatientProcedure, self).default_get(fields)
        if self._context.get('mate_department_type'):
            department = self.env['hr.department'].search([('department_type', '=', self._context.get('mate_department_type'))], limit=1)
            if department:
                res['department_id'] = department.id
        return res

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            self.price_unit = self.product_id.list_price

    @api.onchange('product_id', 'date')
    def onchange_date_and_product(self):
        if self.product_id and self.product_id.procedure_time and self.date:
            self.date_stop = self.date + timedelta(hours=self.product_id.procedure_time)

    def action_running(self):
        self.state = 'running'

    def action_schedule(self):
        self.state = 'scheduled'

    def action_done(self):
        if self.consumable_line_ids:
            self.consume_procedure_material()
        self.state = 'done'

    def action_cancel(self):
        self.state = 'cancel'

    def unlink(self):
        for rec in self:
            if rec.state not in ['scheduled', 'cancel']:
                raise UserError(_('Record can be deleted only in Canceled/Scheduled state.'))
        return super(MatePatientProcedure, self).unlink()

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            values['name'] = self.env['ir.sequence'].next_by_code('mate_hms.patient.procedure') or 'New Procedure'
        return super().create(vals_list)

    def get_procedure_invoice_data(self):
        product_data = [{
            'name': _("Patient Procedure Charges"),
        }]
        for rec in self:
            # Pass price if it is updated else pass 0
            # so if 0 is passed it will apply pricelist value properly.
            procedure_data = {'product_id': rec.product_id}
            if rec.price_unit != rec.product_id.list_price:
                procedure_data['price_unit'] = rec.price_unit
            product_data.append(procedure_data)

            # Line for procedure Consumables
            for consumable in rec.consumable_line_ids:
                product_data.append({
                    'product_id': consumable.product_id,
                    'quantity': consumable.qty,
                    'lot_id': consumable.lot_id and consumable.lot_id.id or False,
                })
        return product_data

    def action_create_invoice(self):
        product_data = self.get_procedure_invoice_data()

        inv_data = {
            'physician_id': self.physician_id and self.physician_id.id or False,
            'hospital_invoice_type': 'procedure',
        }
        mate_context = {'commission_partner_ids': self.physician_id.partner_id.id}
        invoice = self.with_context(mate_context).mate_hms_create_invoice(partner=self.patient_id.partner_id, patient=self.patient_id, product_data=product_data, inv_data=inv_data)
        self.invoice_id = invoice.id
        self.invoice_id.procedure_id = self.id

    def mate_get_consume_locations(self):
        if not self.company_id.procedure_usage_location_id:
            raise UserError(_('Please define a procedure location where the consumables will be used.'))
        if not self.company_id.procedure_stock_location_id:
            raise UserError(_('Please define a procedure location from where the consumables will be taken.'))

        dest_location_id = self.company_id.procedure_usage_location_id.id
        source_location_id = self.company_id.procedure_stock_location_id.id
        return source_location_id, dest_location_id

    def _consume_kit_product(self, line, source_location_id, dest_location_id):
        """Consume kit product materials and return move ids"""
        move_ids = []
        for kit_line in line.product_id.mate_kit_line_ids:
            if kit_line.product_id.tracking != 'none':
                raise UserError("In Consumable lines Kit product with component having lot/serial tracking is not allowed.")

            move = self.consume_material(
                source_location_id,
                dest_location_id,
                {'product': kit_line.product_id, 'qty': kit_line.product_qty * line.qty}
            )
            move.procedure_id = self.id
            move_ids.append(move.id)

        # Set move_id on line also to avoid duplication
        line.move_id = move.id  # Last move
        line.move_ids = [(6, 0, move_ids)]
        return move_ids

    def _consume_single_product(self, line, source_location_id, dest_location_id):
        """Consume single product material and return the move"""
        move = self.consume_material(source_location_id, dest_location_id, {'product': line.product_id, 'qty': line.qty, 'lot_id': line.lot_id and line.lot_id.id or False})
        move.procedure_id = self.id
        line.move_id = move.id
        return move

    def consume_procedure_material(self):
        """Consume all procedure materials"""
        for rec in self:
            source_location_id, dest_location_id = rec.mate_get_consume_locations()
            lines_to_process = rec.consumable_line_ids.filtered(lambda s: not s.move_id)

            for line in lines_to_process:
                if line.product_id.is_kit_product:
                    rec._consume_kit_product(line, source_location_id, dest_location_id)
                else:
                    rec._consume_single_product(line, source_location_id, dest_location_id)

    def view_invoice(self):
        invoices = self.mapped('invoice_id')
        action = self.mate_hms_action_view_invoice(invoices)
        return action

    def action_show_details(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("mate_hms.action_mate_patient_procedure")
        action['context'] = {'default_patient_id': self.patient_id.id}
        action['res_id'] = self.id
        action['views'] = [(self.env.ref('mate_hms.view_mate_patient_procedure_form').id, 'form')]
        action['target'] = 'new'
        return action

    def get_mate_kit_lines(self):
        if not self.mate_kit_id:
            raise UserError("Please Select Kit first.")

        lines = []
        for line in self.mate_kit_id.mate_kit_line_ids:
            lines.append((0, 0, {
                'product_id': line.product_id.id,
                'product_uom_id': line.product_id.uom_id.id,
                'qty': line.product_qty * self.mate_kit_qty,
            }))
        self.consumable_line_ids = lines

    # method to create get invocie data and set passed invocie id.
    def mate_hms_common_invoice_procedure_data(self, invoice_id=False):
        data = []
        if self.ids:
            data = self.get_procedure_invoice_data()
            if invoice_id:
                self.invoice_id = invoice_id.id
        return data


class StockMove(models.Model):
    _inherit = "stock.move"

    procedure_id = fields.Many2one('mate_hms.patient.procedure', ondelete="cascade", string="Procedure")
