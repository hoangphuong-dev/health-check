from odoo import models, fields


class MatePainLevel(models.TransientModel):
    _name = 'mate.pain.level'
    _description = "Pain Level Diagram"

    name = fields.Char()
