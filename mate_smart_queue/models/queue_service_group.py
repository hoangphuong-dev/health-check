from odoo import models, fields, _

IR_ACTIONS_ACT_WINDOWN = "ir.actions.act_window"
MATE_QUEUE_SERVICE_GROUP_ROUTE = "mate.queue.service.group.route"
PRODUCT_PRODUCT = 'product.product'
MATE_HEALTH_CHECK_GROUP = "mate.health.check.group"


class QueueServiceGroup(models.Model):
    _description = _('Medical Service Group')  # Nhóm Dịch Vụ Y Tế
    _inherit = MATE_HEALTH_CHECK_GROUP
    _order = 'sequence'

    code = fields.Char(string=_('Group Code'), required=True)
    sequence = fields.Integer(string=_('Sequence'), default=10)
    service_ids = fields.Many2many(PRODUCT_PRODUCT, string=_('Services in Group'))
    is_required = fields.Boolean(string=_('Required'), default=True,
                                 help=_(
                                     "If checked, all services in the group must be completed. Otherwise, completing one service may be enough to move to the next group."))
    completion_policy = fields.Selection([
        ('all', _('Complete All')),
        ('any', _('Complete Any')),
    ], string=_('Completion Policy'), default='all')
    active = fields.Boolean(string=_('Active'), default=True)
    color = fields.Integer(string=_('Color'), default=0)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', _('Group code must be unique!'))
    ]
