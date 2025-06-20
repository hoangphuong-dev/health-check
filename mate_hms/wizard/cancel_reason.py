from odoo import models, api, fields


class MateCancelReasonWiz(models.TransientModel):
    _name = 'mate_hms.cancel.reason.wiz'
    _description = "Cancellation Reason"

    cancel_reason_id = fields.Many2one('mate_hms.cancel.reason', string='Cancellation Reason', required=True)
    cancel_reason = fields.Text(string="Reason", required=True)

    @api.onchange('cancel_reason_id')
    def onchnage_reason(self):
        if self.cancel_reason_id:
            self.cancel_reason = self.cancel_reason_id.name

    def cancel_appointment(self):
        appointment = self.env['mate_hms.appointment'].search([('id', '=', self.env.context.get('active_id'))])
        appointment.cancel_reason = self.cancel_reason
        appointment.cancel_reason_id = self.cancel_reason_id.id
        appointment.appointment_cancel()
        return True
