from odoo import api, models, fields

PHY_WRITABLE_FIELDS = [
    'physician_id',
    'mate_signature',
    'mate_medical_license',
    'mate_appointment_duration',
]


class User(models.Model):
    _inherit = ['res.users']

    physician_id = fields.Many2one('mate_hms.physician', string="Company Physician", compute='_compute_company_physician', search='_search_company_physician', store=False)
    mate_signature = fields.Binary(related='physician_id.signature', string="Mate Signature", readonly=False, related_sudo=False)
    mate_medical_license = fields.Char(related='physician_id.medical_license', string="Mate Medical License,", readonly=False, related_sudo=False)
    mate_appointment_duration = fields.Float(related="physician_id.appointment_duration", string="Mate Appointment Duration", readonly=False, related_sudo=False)

    @api.depends('physician_ids')
    @api.depends_context('company')
    def _compute_company_physician(self):
        physician_per_user = {
            physician.user_id: physician
            for physician in self.env['mate_hms.physician'].search([('user_id', 'in', self.ids), ('company_id', '=', self.env.company.id)])
        }
        for user in self:
            user.physician_id = physician_per_user.get(user)

    def _search_company_physician(self, operator, value):
        return [('physician_ids', operator, value)]

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + PHY_WRITABLE_FIELDS

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + PHY_WRITABLE_FIELDS
