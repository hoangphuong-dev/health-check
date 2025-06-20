from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def mate_action_assign(self):
        self._action_assign()

    def mate_action_done(self):
        self.picked = True
        self._action_done()
