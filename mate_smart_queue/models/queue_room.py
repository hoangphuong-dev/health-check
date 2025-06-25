# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

HR_DEPARTMENT = 'hr.department'
MATE_QUEUE_TOKEN = "mate.queue.token"
PRODUCT_PRODUCT = 'product.product'
MATE_QUEUE_COORDINATION_LOG = 'mate.queue.coordination.log'
IR_ACTIONS_WINDOW = "ir.actions.act_window"


class QueueRoom(models.Model):
    _description = _('Service Room')
    _inherit = HR_DEPARTMENT

    code = fields.Char(string=_('Room Code'), required=True)
    service_id = fields.Many2one(PRODUCT_PRODUCT, string=_('Service'), required=True)
    capacity = fields.Integer(string=_('Capacity'), default=1,
                              help=_("Number of patients that can be served simultaneously"))
    current_queue = fields.One2many(MATE_QUEUE_TOKEN, 'room_id', string=_('Current Queue'),
                                    domain=[('state', '=', 'waiting')])
    queue_length = fields.Integer(string=_('Queue Length'), compute='_compute_queue_length')
    estimated_wait_time = fields.Float(string=_('Estimated Wait Time (minutes)'), compute='_compute_wait_time')
    active = fields.Boolean(string=_('Active'), default=True)
    state = fields.Selection([
        ('open', _('Open')),
        ('closed', _('Closed')),
        ('maintenance', _('Maintenance'))
    ], string=_('Status'), default='open')
    color = fields.Integer(string=_('Color'), default=0)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', _('Room code must be unique!'))
    ]

    @api.depends('current_queue')
    def _compute_queue_length(self):
        """Tính toán độ dài hàng đợi hiện tại"""
        for room in self:
            room.queue_length = len(room.current_queue)

    @api.depends('queue_length', 'service_id.average_duration')
    def _compute_wait_time(self):
        """Tính toán thời gian chờ ước tính cho bệnh nhân mới"""
        for room in self:
            avg_duration = room.service_id.average_duration
            # Công thức: Số người đợi * Thời gian trung bình / Công suất phòng
            room.estimated_wait_time = room.queue_length * avg_duration / room.capacity

    def action_open_room(self):
        """Mở phòng cho phục vụ"""
        for room in self:
            room.state = 'open'

    def action_close_room(self):
        """Đóng phòng"""
        for room in self:
            room.state = 'closed'

            # Thông báo cho nhân viên về việc đóng phòng
            self.env['mail.message'].create({
                'model': HR_DEPARTMENT,
                'res_id': room.id,
                'message_type': 'notification',
                'body': _("Room %s has been closed. Please reassign patients if needed.") % room.name
            })

    def action_maintenance(self):
        """Đặt phòng vào trạng thái bảo trì"""
        for room in self:
            room.state = 'maintenance'

    def action_view_tokens(self):
        """Xem tất cả token cho phòng này"""
        self.ensure_one()

        # Check context để xác định view mode
        view_mode = self.env.context.get('coordination_mode', False)

        if view_mode:
            # Coordination mode - use specific kanban view
            return {
                'name': _('Token Coordination - %s') % self.name,
                'type': IR_ACTIONS_WINDOW,
                'res_model': 'mate.queue.token',
                'view_mode': 'kanban',
                'view_id': self.env.ref('mate_smart_queue.view_queue_token_coordination_kanban').id,
                'domain': [('room_id', '=', self.id), ('state', '=', 'waiting')],  # Chỉ lấy token waiting
                'context': {
                    'default_room_id': self.id,
                    'default_state': 'waiting',
                    'group_by': 'room_id',
                    'search_default_state': 'waiting'  # Thêm filter mặc định
                }
            }
        else:
            # Normal mode
            return {
                'name': _('Token - %s') % self.name,
                'view_mode': 'list,form',
                'res_model': 'mate.queue.token',
                'domain': [('room_id', '=', self.id)],
                'type': IR_ACTIONS_WINDOW,
                'context': {'default_room_id': self.id}
            }

    def action_view_coordination_history(self):
        """Xem lịch sử điều phối của phòng"""
        self.ensure_one()
        return {
            'name': 'Lịch sử điều phối - %s' % self.name,
            'type': IR_ACTIONS_WINDOW,
            'res_model': MATE_QUEUE_COORDINATION_LOG,
            'view_mode': 'list,form',
            'views': [[False, 'list'], [False, 'form']],
            'domain': [
                '|',
                ('from_room_id', '=', self.id),
                ('to_room_id', '=', self.id)
            ],
            'context': dict(self.env.context,
                            default_room_id=self.id,
                            search_default_room_filter=1,
                            search_default_today=1),
            'target': 'current',
        }
