# -*- coding: utf-8 -*-

from odoo import fields, models

PHYSICIAN_SPECIALTY = 'physician.specialty'


class MateHealthCheckSpecialty(models.Model):
    _name = PHYSICIAN_SPECIALTY
    _description = 'Health Check Specialty'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
