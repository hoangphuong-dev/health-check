from odoo import fields, models


class ResCountry(models.Model):
    _inherit = "res.country"

    gov_code_label = fields.Char(string='Government Identity Label', default="Government Identity")
