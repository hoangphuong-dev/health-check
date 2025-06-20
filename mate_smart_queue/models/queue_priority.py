# -*- coding: utf-8 -*-
from odoo import models, fields

MATE_QUEUE_PRIORITY = "mate.queue.priority"


class QueuePriority(models.Model):
    _name = MATE_QUEUE_PRIORITY
    _description = 'Queue Priority Type'
    _order = 'priority_level desc'

    name = fields.Char(string='Priority Level Name', required=True)
    code = fields.Char(string='Priority Code', required=True)
    priority_level = fields.Integer(string='Priority Level', required=True,
                                    help="Higher number indicates higher priority")
    description = fields.Text(string='Description')
    color = fields.Integer(string='Color')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Priority code must be unique!'),
        ('priority_level_uniq', 'unique(priority_level)', 'Priority level must be unique!')
    ]
