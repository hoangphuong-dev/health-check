from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

MATE_HMS_APPOINTMENT = 'mate_hms.appointment'


class MateHandleConsumedServices(models.TransientModel):
    _inherit = 'mate_hms.handle.consumed.services'

    patient_id = fields.Many2one('mate_hms.patient', string='Patient')
    package_id = fields.Many2one('mate_hms.package', string='Package')
    physician_id = fields.Many2one('mate_hms.physician', string='Physician')
    custom_package_domain = fields.Char(string='Custom Package')
    visit_number = fields.Char(string='Visit Number')
    attachment_id = fields.Many2one('ir.attachment', string='Attachment')

    @api.onchange('patient_id')
    def _onchange_patient_id(self):
        if self.patient_id:
            # Lấy các gói package mà patient_id đã đăng ký từ subscriptions_ids
            package_ids = self.patient_id.subscriptions_ids.filtered(lambda x: x._check_validate()).mapped('package_id').ids
            self.custom_package_domain = [('id', 'in', package_ids)]
        else:
            self.custom_package_domain = []

    def _get_appointment(self):
        """
        Get the appointment from the context.
        """
        appointment = self.appointment_id
        if self.package_id:
            appointment = self.env[MATE_HMS_APPOINTMENT].create({
                'patient_id': self.patient_id.id,
                'physician_id': self.physician_id.id,
                'date': self.date,
                'date_to': self.date_to,
                'state': 'to_invoice',
                'consultation_type': 'followup',
            })
        return appointment

    def save_services_appointments(self):
        appointment = super(MateHandleConsumedServices, self).save_services_appointments()
        appointment.visit_number = self.visit_number
        appointment.attachment_id = self.env['ir.attachment'].create({
            'name': self.excel_file_name,
            'datas': self.excel_file,
            'res_model': MATE_HMS_APPOINTMENT,
        })
        if self.package_id:
            subscription = self.env['mate_hms.subscriptions'].search([
                ('patient_id', '=', self.patient_id.id),
                ('package_id', '=', self.package_id.id),
            ], limit=1)
            for consumable in appointment.consumable_line_ids:
                if consumable.product_id.id in self.package_id.order_line.product_id.ids:
                    consumable.subscription_id = subscription.id
            appointment.consultation_done()
            return {
                'type': 'ir.actions.act_window',
                'res_model': MATE_HMS_APPOINTMENT,
                'view_mode': 'form',
                'res_id': appointment.id,
                'target': 'current',
            }
        return appointment
