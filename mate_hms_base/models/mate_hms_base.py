from odoo import fields, models


class MatePatientTag(models.Model):
    _name = "mate_hms.patient.tag"
    _description = "HMS Patient Tag"

    def _get_default_color(self):
        return 1 + (self.env.uid % 11)

    name = fields.Char(string="Name")
    color = fields.Integer('Color', default=_get_default_color)


class MateTherapeuticEffect(models.Model):
    _name = "mate_hms.therapeutic.effect"
    _description = "HMS Therapeutic Effect"

    code = fields.Char(string="Code")
    name = fields.Char(string="Name", required=True)


class MateReligion(models.Model):
    _name = 'mate_hms.religion'
    _description = "HMS Religion"

    name = fields.Char(string="Name", required=True, translate=True)
    code = fields.Char(string='code')
    notes = fields.Char(string='Notes')

    _sql_constraints = [('name_uniq', 'UNIQUE(name)', 'Name must be unique!')]
