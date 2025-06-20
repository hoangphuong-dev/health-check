# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

PRODUCT_PRODUCT = 'product.product'
HR_DEPARTMENT = 'hr.department'
HIS_PATIENT = 'his.patient'

MATE_HEALTH_CHECK_GROUP = "mate.health.check.group"
MATE_HEALTH_CHECK_PACKAGE = 'mate.health.check.package'

MATE_QUEUE_SERVICE_GROUP_ROUTE = "mate.queue.service.group.route"
MATE_QUEUE_SERVICE_ROUTE = "mate.queue.service.route"

IR_ACTIONS_CLIENT = "ir.actions.client"


class QueueService(models.Model):
    _description = _('Medical Service')
    _inherit = PRODUCT_PRODUCT

    code = fields.Char(string=_('Service Code'), required=True)
    sequence = fields.Integer(string=_('Sequence'), default=10)
    active = fields.Boolean(string=_('Active'), default=True)

    service_group_id = fields.Many2one(
        MATE_HEALTH_CHECK_GROUP,
        string=_('Service Group'),
        required=True,
        help=_("Service group that this service belongs to")
    )

    average_duration = fields.Float(string=_('Average Service Duration (minutes)'), default=10.0)
    duration_count = fields.Integer(string=_('Duration Count'), default=0)
    rooms_ids = fields.One2many(HR_DEPARTMENT, 'service_id', string=_('Serving Rooms'))

    available_rooms_count = fields.Integer(
        string=_('Available Rooms Count'),
        compute='_compute_coordination_display_info'
    )
    suggested_room_name = fields.Char(
        string=_('Suggested Room'),
        compute='_compute_coordination_display_info'
    )
    waiting_queue_count = fields.Integer(
        string=_('Waiting Queue Count'),
        compute='_compute_coordination_display_info'
    )
    estimated_wait_time = fields.Float(
        string=_('Estimated Wait Time'),
        compute='_compute_coordination_display_info'
    )

    _sql_constraints = [
        ('code_uniq', 'unique(code)', _('Service code must be unique!'))
    ]

    @api.depends('rooms_ids.state')
    def _compute_coordination_display_info(self):
        """Compute coordination display info for list view"""
        for service in self:
            # Tìm patient từ available_coordination_service_ids relationship
            patient = self.env[HIS_PATIENT].search([
                ('available_coordination_service_ids', 'in', service.id),
            ], limit=1)

            if patient:
                service_info = patient.get_service_coordination_info(service.id)

                if service_info.get('available', False):
                    service.available_rooms_count = len(service.rooms_ids.filtered(lambda r: r.state == 'open'))
                    service.suggested_room_name = service_info.get('recommended_room', '')
                    service.waiting_queue_count = service_info.get('queue_length', 0)
                    service.estimated_wait_time = service_info.get('estimated_wait', 0)
                else:
                    service.available_rooms_count = 0
                    service.suggested_room_name = _('No available rooms')
                    service.waiting_queue_count = 666666
                    service.estimated_wait_time = 0.0
            else:
                # Default values when no patient found
                open_rooms = service.rooms_ids.filtered(lambda r: r.state == 'open')
                service.available_rooms_count = len(open_rooms)
                service.suggested_room_name = open_rooms[0].name if open_rooms else _('None')
                service.waiting_queue_count = 999999
                service.estimated_wait_time = 0.0

    def _update_average_duration(self, duration):
        """
        Cập nhật thời gian trung bình của dịch vụ

        Tham số:
            duration (float): Thời gian thực tế của lần phục vụ mới (phút)
        """
        for service in self:
            current_avg = service.average_duration
            current_count = service.duration_count

            # Tính trung bình cộng theo công thức: ((avg_cũ * số_lượt_cũ) + giá_trị_mới) / (số_lượt_cũ + 1)
            new_count = current_count + 1
            new_avg = ((current_avg * current_count) + duration) / new_count

            service.write({
                'average_duration': new_avg,
                'duration_count': new_count
            })


class QueueServiceGroupRoute(models.Model):
    _name = MATE_QUEUE_SERVICE_GROUP_ROUTE
    _description = _('Service Group Route')

    name = fields.Char(string=_('Route Name'), compute='_compute_name', store=True)
    group_from_id = fields.Many2one(MATE_HEALTH_CHECK_GROUP, string=_('From Service Group'), required=True)
    group_to_id = fields.Many2one(MATE_HEALTH_CHECK_GROUP, string=_('To Service Group'), required=True)
    condition = fields.Text(string=_('Transfer Condition'))
    sequence = fields.Integer(string=_('Priority'), default=10)
    package_id = fields.Many2one(MATE_HEALTH_CHECK_PACKAGE, string=_('Specific Service Package'))

    @api.depends('group_from_id', 'group_to_id')
    def _compute_name(self):
        for route in self:
            if route.group_from_id and route.group_to_id:
                route.name = f"{route.group_from_id.name} → {route.group_to_id.name}"
            else:
                route.name = _("New Group Route")

    @api.model
    def create_or_update_route(self, from_group_id, to_group_id):
        """
        Tạo hoặc cập nhật tuyến đường khi kéo thả

        Args:
            from_group_id: ID của nhóm nguồn
            to_group_id: ID của nhóm đích

        Returns:
            dict: Thông tin về tuyến đường đã tạo hoặc cập nhật
        """
        # Kiểm tra xem tuyến đường này đã tồn tại chưa
        existing_route = self.search([
            ('group_from_id', '=', from_group_id),
            ('group_to_id', '=', to_group_id)
        ], limit=1)

        if existing_route:
            # Nếu đã tồn tại, cập nhật sequence (sắp xếp lại ưu tiên)
            existing_route.sequence = 10
            return {
                'type': IR_ACTIONS_CLIENT,
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Route has been updated'),
                    'sticky': False,
                    'type': 'success',
                }
            }
        else:
            # Kiểm tra xem có đang tạo vòng lặp không
            if self._check_route_loop(from_group_id, to_group_id):
                return {
                    'type': IR_ACTIONS_CLIENT,
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Warning'),
                        'message': _('Cannot create route because it will create a loop!'),
                        'sticky': True,
                        'type': 'warning',
                    }
                }

            # Tạo tuyến đường mới
            self.create({
                'group_from_id': from_group_id,
                'group_to_id': to_group_id,
                'sequence': 10,
            })

            return {
                'type': IR_ACTIONS_CLIENT,
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('New route has been created'),
                    'sticky': False,
                    'type': 'success',
                }
            }

    def _check_route_loop(self, from_group_id, to_group_id):
        """
        Kiểm tra xem việc tạo tuyến đường này có tạo vòng lặp không

        Args:
            from_group_id: ID của nhóm nguồn
            to_group_id: ID của nhóm đích

        Returns:
            bool: True nếu tạo vòng lặp, False nếu không
        """
        # Kiểm tra nếu đã có tuyến đường từ to_group quay lại from_group
        return bool(self.search([
            ('group_from_id', '=', to_group_id),
            ('group_to_id', '=', from_group_id)
        ], limit=1))


class QueueServiceRoute(models.Model):
    """
    Model này định nghĩa các tuyến đường (route) giữa các dịch vụ
    Ví dụ: Sau khi Đăng Ký -> đi tới Đo Dấu Hiệu Sinh Tồn -> đi tới Xét Nghiệm...
    """
    _name = MATE_QUEUE_SERVICE_ROUTE
    _description = _('Service Route')

    name = fields.Char(string=_('Route Name'), compute='_compute_name', store=True)
    service_from_id = fields.Many2one(PRODUCT_PRODUCT, string=_('From Service'), required=True)
    service_to_id = fields.Many2one(PRODUCT_PRODUCT, string=_('To Service'), required=True)
    condition = fields.Text(string=_('Transfer Condition'),
                            help=_("Python expression to determine whether this route should be used"))
    sequence = fields.Integer(string=_('Priority'), default=10,
                              help=_("Lower number has higher priority when multiple routes can be applied"))
    package_id = fields.Many2one(MATE_HEALTH_CHECK_PACKAGE, string=_('Specific Service Package'),
                                 help=_("If set, this route only applies to this service package"))

    @api.depends('service_from_id', 'service_to_id')
    def _compute_name(self):
        """Tạo tên tuyến đường từ tên các dịch vụ liên quan"""
        for route in self:
            if route.service_from_id and route.service_to_id:
                route.name = f"{route.service_from_id.name} → {route.service_to_id.name}"
            else:
                route.name = _("New Route")
