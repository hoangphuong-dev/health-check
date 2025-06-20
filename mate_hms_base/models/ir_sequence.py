from odoo import fields, models


class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    mate_auto_create = fields.Boolean('Auto Create On Company Creation', default=False, help="Auto Create new sequecte for new company.", copy=False)
