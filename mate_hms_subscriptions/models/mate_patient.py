from odoo import fields, models


class MatePatient(models.Model):
    _inherit = ['mate_hms.patient']

    package_ids = fields.One2many(
        'mate_hms.subscription.line', 'patient_id', string='Patient Packages'
    )

    subscriptions_ids = fields.One2many(
        'mate_hms.subscriptions', 'patient_id', string='Subscriptions'
    )
