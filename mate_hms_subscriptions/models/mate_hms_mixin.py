from odoo import models
import logging

_logger = logging.getLogger(__name__)


class MateHmsMixin(models.AbstractModel):
    _inherit = ['mate_hms.mixin']
    _description = "HMS Mixin"

    def mate_prepare_invocie_data(self, partner, patient, product_data, inv_data):
        """
        Override hàm mate_prepare_invocie_data để thêm thông tin về package usage vào invoice.
        """
        res = super(MateHmsMixin, self).mate_prepare_invocie_data(partner, patient, product_data, inv_data)

        return res
