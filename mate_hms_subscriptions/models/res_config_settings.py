from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    service_generation_option = fields.Selection(
        selection=[
            ('appointment', 'Appointment'),
            ('invoice', 'Invoice'),
        ],
        string='Invoice Generation Option',
        help='Choose whether to generate consultation service at Appointment or Invoice stage',
        default='invoice',
        config_parameter='mate_hms_subscriptions.service_generation_option',
    )
    appointment_status = fields.Selection(
        selection=lambda self: self.env['mate_hms.appointment']._fields['state'].selection,
        string='Appointment Status to Trigger Service Generation',
        config_parameter='mate_hms_subscriptions.appointment_status',
    )
