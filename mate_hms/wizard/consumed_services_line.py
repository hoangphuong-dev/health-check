# -*- coding: utf-8 -*-
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class MateConsumedServicesLine(models.TransientModel):
    _name = 'mate_hms.consumed.services.line'
    _description = "Store Consumed Services After Upload Excel File"

    # - handle_consumed_services_id: ID wizard cha của bản ghi hiện tại.
    handle_consumed_services_id = fields.Many2one('mate_hms.handle.consumed.services', string='Appointment')
    code = fields.Char(string='Code')
    name = fields.Char(string='Name')
    quantity = fields.Integer(string='Quantity')
    unit_price = fields.Float(string='Unit Price')
    # - duplicated: Trường check trùng lặp code.
    duplicated = fields.Boolean(default=False)
