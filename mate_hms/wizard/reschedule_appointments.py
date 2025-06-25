from odoo import models, fields


class MateRescheduleAppointments(models.TransientModel):
    _name = 'mate.reschedule.appointments'
    _description = "Reschedule Appointments"

    mate_reschedule_time = fields.Float(string="Reschedule Selected Appointments by (Hours)", required=True)

    def mate_reschedule_appointments(self):
        appointments = self.env['mate_hms.appointment'].search([('id', 'in', self.env.context.get('active_ids'))])
        # Mate: do it in method only to use that method for notifications.
        appointments.mate_reschedule_appointments(self.mate_reschedule_time)
