# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import date
import logging
from odoo.exceptions import UserError

HIS_PATIENT = 'his.patient'
HR_DEPARTMENT = 'hr.department'
PRODUCT_PRODUCT = 'product.product'

MATE_HEALTH_CHECK_PACKAGE = 'mate.health.check.package'
MATE_HEALTH_CHECK_GROUP = "mate.health.check.group"

MATE_QUEUE_TOKEN = 'mate.queue.token'
MATE_QUEUE_COORDINATION_LOG = 'mate.queue.coordination.log'
MATE_QUEUE_ROOM_SELECTION_WIRARD = 'mate.queue.room.selection.wizard'

NOT_WAITING_SERVICE = _("No service waiting")
TEXT_NOTIFICATION = _("Notification")
IR_ACTIONS_CLIENT = "ir.actions.client"
IR_ACTIONS_WINDOW = "ir.actions.act_window"

# Các loại điều phối
COORDINATION_SERVICE_CHANGE = 'service_change'
COORDINATION_ROOM_CHANGE = 'room_change'
COORDINATION_POSITION_CHANGE = 'position_change'

class MateQueuePatient(models.Model):
    _description = 'Mate Queue Patient'
    _inherit = HIS_PATIENT

    # Các trường cơ bản
    patient_id_number = fields.Char(string='Patient ID', help=_("Patient ID Number"))
    date_of_birth = fields.Date(string='Date of Birth')
    age = fields.Integer(string='Age', compute='_compute_age', store=True)
    gender = fields.Selection([
        ('male', _('Male')),
        ('female', _('Female')),
        ('other', _('Other'))
    ], string='Gender')

    # Phân loại bệnh nhân
    patient_category = fields.Selection([
        ('vvip', 'VVIP'),
        ('vip', 'VIP'),
        ('normal', _('Normal Customer')),
        ('child', _('Child')),
        ('pregnant', _('Pregnant')),
        ('elderly', _('Elderly')),
        ('nccvcm', 'NCCVCM'),
    ], string='Patient Category', default='normal')

    # Tình trạng bệnh nhân
    is_pregnant = fields.Boolean(string='Is Pregnant', default=False)
    is_disabled = fields.Boolean(string='Is Disabled', default=False)
    has_urgent_condition = fields.Boolean(string='Has Urgent Condition', default=False)
    is_vip = fields.Boolean(string='Is VIP', default=False)
    doctor_assigned_priority = fields.Boolean(string='Doctor Assigned Priority', default=False)

    # Các trường quản lý hàng đợi
    queue_package_id = fields.Many2one(MATE_HEALTH_CHECK_PACKAGE, string='Health Check Package')
    queue_history_ids = fields.One2many(MATE_QUEUE_TOKEN, 'patient_id', string='Queue History')
    queue_history_count = fields.Integer(string='Token Count', compute='_compute_queue_history_count')
    current_service_group_id = fields.Many2one(MATE_HEALTH_CHECK_GROUP, string='Current Service Group')

    # Theo dõi dịch vụ
    completed_service_ids = fields.Many2many(
        PRODUCT_PRODUCT,
        'mate_patient_completed_service_rel',
        'patient_id',
        'service_id',
        string='Completed Services'
    )

    available_coordination_service_ids = fields.Many2many(
        PRODUCT_PRODUCT,
        'mate_patient_available_coordination_service_rel',
        'patient_id',
        'service_id',
        string='Available Coordination Services',
        compute='_compute_available_coordination_services'
    )

    # Thông tin dịch vụ hiện tại
    current_waiting_token_id = fields.Many2one(
        MATE_QUEUE_TOKEN,
        string='Current Waiting Token',
        compute='_compute_current_service_info',
        store=False
    )

    # Các trường dịch vụ tiếp theo
    next_service_name = fields.Char(
        string='Next Service Name',
        compute='_compute_current_service_info'
    )
    next_service_room = fields.Char(
        string='Room',
        compute='_compute_current_service_info'
    )
    next_service_position = fields.Integer(
        string='Position',
        compute='_compute_current_service_info'
    )
    next_service_queue_count = fields.Integer(
        string='Queue Count',
        compute='_compute_current_service_info'
    )
    next_service_wait_time = fields.Float(
        string='Wait Time',
        compute='_compute_current_service_info'
    )
    next_service_token_name = fields.Char(
        string='Token Code',
        compute='_compute_current_service_info'
    )

    group_1_progress = fields.Char(
        string='Sinh tồn',
        compute='_compute_service_groups_progress',
        store=False
    )
    group_1_completed = fields.Boolean(
        string='Group 1 Completed',
        compute='_compute_service_groups_progress',
        store=False
    )

    group_2_progress = fields.Char(
        string='Xét nghiệm',
        compute='_compute_service_groups_progress',
        store=False
    )
    group_2_completed = fields.Boolean(
        string='Group 2 Completed',
        compute='_compute_service_groups_progress',
        store=False
    )

    group_3_progress = fields.Char(
        string='Chuẩn đoán hình ảnh',
        compute='_compute_service_groups_progress',
        store=False
    )
    group_3_completed = fields.Boolean(
        string='Group 3 Completed',
        compute='_compute_service_groups_progress',
        store=False
    )

    group_4_progress = fields.Char(
        string='Chuyên khoa',
        compute='_compute_service_groups_progress',
        store=False
    )
    group_4_completed = fields.Boolean(
        string='Group 4 Completed',
        compute='_compute_service_groups_progress',
        store=False
    )

    estimated_time = fields.Char(string='Estimated Wait Time', compute='_compute_estimated_time', store=False)

    @api.depends('queue_package_id', 'queue_history_ids')
    def _compute_service_groups_progress(self):
        """Tính toán tiến độ từng nhóm dịch vụ"""
        for patient in self:
            # Reset tất cả các trường
            patient.group_1_progress = ""
            patient.group_2_progress = ""
            patient.group_3_progress = ""
            patient.group_4_progress = ""
            patient.group_1_completed = False
            patient.group_2_completed = False
            patient.group_3_completed = False
            patient.group_4_completed = False

            if not patient.queue_package_id:
                return

            # Lấy các nhóm dịch vụ từ gói theo thứ tự sequence
            package_services = patient.queue_package_id.service_ids
            service_groups = package_services.mapped('service_group_id').sorted(key=lambda g: g.sequence)

            # Danh sách 4 trường để map
            progress_fields = ['group_1_progress', 'group_2_progress', 'group_3_progress', 'group_4_progress']
            completed_fields = ['group_1_completed', 'group_2_completed', 'group_3_completed', 'group_4_completed']

            for idx, group in enumerate(service_groups[:4]):  # Chỉ lấy tối đa 4 nhóm
                # Lấy các dịch vụ trong nhóm thuộc gói này
                group_services_in_package = package_services.filtered(
                    lambda s, current_group=group: s.service_group_id.id == current_group.id
                )
                total_services = len(group_services_in_package)

                # Đếm số dịch vụ đã hoàn thành trong nhóm
                completed_tokens = patient.queue_history_ids.filtered(
                    lambda t, current_group=group, services_ids=group_services_in_package.ids: (t.service_id.service_group_id.id == current_group.id and t.state == 'completed' and t.service_id.id in services_ids)
                )
                completed_services = len(completed_tokens)

                # Đặt giá trị cho trường tương ứng
                setattr(patient, progress_fields[idx], f"{completed_services}/{total_services}")
                setattr(patient, completed_fields[idx], completed_services == total_services)

    def action_open_current_service_room_selection(self):
        """Mở cửa sổ chọn phòng cho dịch vụ đang chờ hiện tại"""
        self.ensure_one()

        if not self.current_waiting_token_id:
            raise UserError(NOT_WAITING_SERVICE)

        token = self.current_waiting_token_id

        return {
            'name': _('Clinic Options'),
            'type': IR_ACTIONS_WINDOW,
            'res_model': MATE_QUEUE_ROOM_SELECTION_WIRARD,
            'view_mode': 'form',
            'view_id': self.env.ref('mate_smart_queue.view_queue_room_selection_wizard_simple_form').id,
            'target': 'new',
            'context': {
                'default_patient_id': self.id,
                'default_service_id': token.service_id.id,
                'default_current_room_id': token.room_id.id if token.room_id else False,
                'default_coordination_type': COORDINATION_ROOM_CHANGE
            }
        }

    @api.depends('queue_history_ids', 'queue_history_ids.state')
    def _compute_current_service_info(self):
        for patient in self:
            # Đặt lại các giá trị
            patient.current_waiting_token_id = False
            patient.next_service_name = False
            patient.next_service_room = False
            patient.next_service_position = 0
            patient.next_service_queue_count = 0
            patient.next_service_wait_time = 0
            patient.next_service_token_name = False

            # Tìm token đang chờ
            waiting_token = patient.queue_history_ids.filtered(
                lambda t: t.state == 'waiting'
            )

            if waiting_token:
                token = waiting_token[0]
                patient.current_waiting_token_id = token
                patient.next_service_name = token.service_id.name
                patient.next_service_room = token.room_id.name
                patient.next_service_position = token.position
                patient.next_service_token_name = token.name

                # Tính số lượng hàng đợi
                queue_count = self.env[MATE_QUEUE_TOKEN].search_count([
                    ('room_id', '=', token.room_id.id),
                    ('state', '=', 'waiting'),
                    ('position', '<', token.position)
                ])
                patient.next_service_queue_count = queue_count
                patient.next_service_wait_time = token.estimated_wait_time

    @api.depends('queue_package_id', 'completed_service_ids', 'queue_history_ids.state')
    def _compute_available_coordination_services(self):
        """Tính toán danh sách dịch vụ có thể điều phối"""
        for patient in self:
            # Kiểm tra xem có token đang chờ không
            waiting_tokens = patient.queue_history_ids.filtered(lambda t: t.state == 'waiting')
            if not waiting_tokens:
                patient.available_coordination_service_ids = [(6, 0, [])]
                continue

            # Lấy các dịch vụ chưa hoàn thành trong gói
            package_services = patient.queue_package_id.service_ids
            completed_services = patient.completed_service_ids
            remaining_services = package_services - completed_services

            # Loại bỏ dịch vụ đang chờ hiện tại
            current_service = waiting_tokens[0].service_id
            remaining_services = remaining_services - current_service

            # Lọc các dịch vụ có phòng khả dụng
            available_service_ids = []

            for service in remaining_services:
                service_info = patient.get_service_coordination_info(service.id)
                # Chỉ thêm dịch vụ nếu có phòng khả dụng
                if service_info.get('available', False):
                    available_service_ids.append(service.id)

            patient.available_coordination_service_ids = [(6, 0, available_service_ids)]

    @api.depends('queue_history_ids', 'queue_history_ids.state', 'completed_service_ids', 'queue_package_id', 'queue_package_id.service_ids')
    def get_service_coordination_info(self, service_id):
        """Lấy thông tin điều phối thời gian thực cho một dịch vụ"""
        service = self.env[PRODUCT_PRODUCT].browse(service_id)
        if not service.exists():
            return {'available': False, 'message': _('Service does not exist')}

        # Lấy các phòng khả dụng
        available_rooms = self.env[HR_DEPARTMENT].search([
            ('service_id', '=', service.id),
            ('state', '=', 'open')
        ])

        if not available_rooms:
            return {
                'available': False,
                'message': _('No available rooms'),
                'room_count': 0,
                'queue_length': 0,
                'estimated_wait': 0
            }

        # Lấy phòng ít tải nhất
        least_loaded_room = self._find_least_loaded_room_for_service(service)

        # Lấy thống kê hàng đợi chỉ cho phòng được đề xuất
        if least_loaded_room:
            waiting_tokens = self.env[MATE_QUEUE_TOKEN].search([
                ('room_id', '=', least_loaded_room.id),
                ('state', '=', 'waiting')
            ])

            room_waiting = len(waiting_tokens)

            # Tính thời gian chờ ước tính
            if room_waiting > 0:
                total_wait_time = sum(token.estimated_wait_time for token in waiting_tokens)
                avg_wait = total_wait_time / room_waiting
            else:
                avg_wait = 0
        else:
            room_waiting = 0
            avg_wait = 0

        # Xác định màu thời gian chờ
        if avg_wait < 25:
            wait_color = 'success'
        elif avg_wait <= 45:
            wait_color = 'warning'
        else:
            wait_color = 'danger'

        return {
            'available': True,
            'service_name': service.name,
            'room_count': len(available_rooms),
            'recommended_room': least_loaded_room.name if least_loaded_room else '',
            'queue_length': room_waiting,
            'estimated_wait': int(avg_wait),
            'wait_color': wait_color
        }

    @api.depends('date_of_birth')
    def _compute_age(self):
        """Tính tuổi từ ngày sinh"""
        for patient in self:
            if patient.date_of_birth:
                today = date.today()
                born = patient.date_of_birth
                patient.age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
            else:
                patient.age = 0

    @api.depends('queue_history_ids')
    def _compute_queue_history_count(self):
        """Đếm số lượng token được phát hành cho bệnh nhân"""
        for patient in self:
            patient.queue_history_count = len(patient.queue_history_ids)

    def action_back(self):
        """Quay lại danh sách bệnh nhân"""
        return {
            'type': IR_ACTIONS_WINDOW,
            'name': _('Patient List'),
            'res_model': HIS_PATIENT,
            'view_mode': 'kanban,list',
            'context': {'default_is_patient': True},
            'target': 'current',
        }

    def _compute_estimated_time(self):
        """Tính thời gian chờ ước tính"""
        for patient in self:
            if patient.queue_history_ids:
                waiting_token = patient.queue_history_ids.filtered(
                    lambda t: t.state == 'waiting'
                ).sorted('estimated_wait_time')

                if waiting_token:
                    time_minutes = waiting_token[0].estimated_wait_time
                    hours = int(time_minutes // 60)
                    minutes = int(time_minutes % 60)
                    if hours > 0:
                        patient.estimated_time = _("%(hours)d hours %(minutes)d minutes") % {
                            'hours': hours, 'minutes': minutes
                        }
                    else:
                        patient.estimated_time = _("%(minutes)d minutes") % {'minutes': minutes}
                else:
                    patient.estimated_time = ''
            else:
                patient.estimated_time = ''

    def _validate_service_coordination_request(self, target_service_id):
        """Xác thực yêu cầu điều phối dịch vụ"""
        # Tìm token đang chờ hiện tại
        current_waiting_tokens = self.queue_history_ids.filtered(lambda t: t.state == 'waiting')
        if not current_waiting_tokens:
            return {
                'error': True,
                'type': IR_ACTIONS_CLIENT,
                'tag': 'display_notification',
                'params': {'title': TEXT_NOTIFICATION, 'message': NOT_WAITING_SERVICE, 'type': 'warning'}
            }

        current_token = current_waiting_tokens[0]

        # Xác thực dịch vụ đích
        target_service = self.env[PRODUCT_PRODUCT].browse(target_service_id)
        if not target_service.exists():
            return {
                'error': True,
                'type': IR_ACTIONS_CLIENT,
                'tag': 'display_notification',
                'params': {'title': _('Error'), 'message': _('Service does not exist'), 'type': 'danger'}
            }

        # Kiểm tra xem dịch vụ có trong gói không
        if self.queue_package_id and target_service not in self.queue_package_id.service_ids:
            return {
                'error': True,
                'type': IR_ACTIONS_CLIENT,
                'tag': 'display_notification',
                'params': {'title': _('Error'), 'message': _('Service is not in health check package'),
                           'type': 'danger'}
            }

        # Kiểm tra xem đã hoàn thành chưa
        if target_service in self.completed_service_ids:
            return {
                'error': True,
                'type': IR_ACTIONS_CLIENT,
                'tag': 'display_notification',
                'params': {'title': _('Error'), 'message': _('Service has been completed'), 'type': 'danger'}
            }

        # Kiểm tra xem có phải cùng dịch vụ không
        if current_token.service_id.id == target_service.id:
            return {
                'error': True,
                'type': IR_ACTIONS_CLIENT,
                'tag': 'display_notification',
                'params': {'title': TEXT_NOTIFICATION, 'message': _('Already in this service'), 'type': 'info'}
            }

        return {
            'error': False,
            'current_token': current_token,
            'target_service': target_service
        }

    def _validate_room_coordination_request(self, target_room_id):
        """Xác thực yêu cầu điều phối phòng"""
        # Tìm token đang chờ hiện tại
        current_waiting_tokens = self.queue_history_ids.filtered(lambda t: t.state == 'waiting')
        if not current_waiting_tokens:
            return {
                'error': True,
                'type': IR_ACTIONS_CLIENT,
                'tag': 'display_notification',
                'params': {'title': TEXT_NOTIFICATION, 'message': NOT_WAITING_SERVICE, 'type': 'warning'}
            }

        current_token = current_waiting_tokens[0]

        # Xác thực phòng đích
        target_room = self.env[HR_DEPARTMENT].browse(target_room_id)
        if not target_room.exists():
            return {
                'error': True,
                'type': IR_ACTIONS_CLIENT,
                'tag': 'display_notification',
                'params': {'title': _('Error'), 'message': _('Room does not exist'), 'type': 'danger'}
            }

        # Kiểm tra xem phòng có mở không
        if target_room.state != 'open':
            return {
                'error': True,
                'type': IR_ACTIONS_CLIENT,
                'tag': 'display_notification',
                'params': {'title': _('Error'), 'message': _('Room is closed or under maintenance'), 'type': 'danger'}
            }

        # Kiểm tra xem phòng có hỗ trợ dịch vụ hiện tại không
        if target_room.service_id.id != current_token.service_id.id:
            return {
                'error': True,
                'type': IR_ACTIONS_CLIENT,
                'tag': 'display_notification',
                'params': {'title': _('Error'), 'message': _('Room does not support current service'), 'type': 'danger'}
            }

        return {
            'error': False,
            'current_token': current_token,
            'target_room': target_room
        }

    def _find_least_loaded_room_for_service(self, service):
        """Tìm phòng ít tải nhất cho dịch vụ"""
        available_rooms = self.env[HR_DEPARTMENT].search([
            ('service_id', '=', service.id),
            ('state', '=', 'open')
        ])

        if not available_rooms:
            return False

        least_loaded_room = None
        min_load = float('inf')

        for room in available_rooms:
            waiting_count = self.env[MATE_QUEUE_TOKEN].search_count([
                ('room_id', '=', room.id),
                ('state', '=', 'waiting')
            ])

            load_ratio = waiting_count / room.capacity if room.capacity > 0 else float('inf')

            if load_ratio < min_load:
                min_load = load_ratio
                least_loaded_room = room

        return least_loaded_room

    def _create_coordination_token(self, current_token, target_service, target_room):
        """Tạo token mới cho điều phối - xếp vào cuối hàng đợi"""
        # Tính vị trí ở CUỐI hàng đợi
        existing_tokens = self.env[MATE_QUEUE_TOKEN].search([
            ('room_id', '=', target_room.id),
            ('state', '=', 'waiting')
        ], order='position desc')

        # Lấy vị trí cuối + 1
        if existing_tokens:
            new_position = existing_tokens[0].position + 1
        else:
            new_position = 1

        # Tạo giá trị token mới
        new_token_vals = {
            'patient_id': self.id,
            'service_id': target_service.id,
            'room_id': target_room.id,
            'position': new_position,
            'priority': current_token.priority,
            'priority_id': current_token.priority_id.id if current_token.priority_id else False,
            'emergency': current_token.emergency,
            'package_id': current_token.package_id.id if current_token.package_id else False,
            'state': 'waiting',
            'notes': _("Coordinated from %s at %s") % (current_token.service_id.name,
                                                       fields.Datetime.now().strftime('%H:%M'))
        }

        # Tạo token với context bỏ qua phân công tự động
        new_token = self.env[MATE_QUEUE_TOKEN].with_context(skip_auto_assignment=True).create(new_token_vals)

        return new_token

    def _log_coordination(self, old_token_data, new_token, coordination_type, reason):
        """
        Ghi log hoạt động điều phối - Hàm thống nhất
        
        Args:
            old_token_data: Dict chứa thông tin token cũ hoặc token object
            new_token: Token mới
            coordination_type: Loại điều phối
            reason: Lý do điều phối
        """
        # Xử lý linh hoạt cho cả token object và dict data
        if hasattr(old_token_data, 'service_id'):
            # old_token_data là token object
            log_vals = {
                'patient_id': self.id,
                'coordination_type': coordination_type,
                'from_service_id': old_token_data.service_id.id,
                'to_service_id': new_token.service_id.id,
                'from_room_id': old_token_data.room_id.id if old_token_data.room_id else False,
                'to_room_id': new_token.room_id.id,
                'old_position': old_token_data.position,
                'new_position': new_token.position,
                'old_token_id': old_token_data.id,
                'new_token_id': new_token.id,
                'priority': new_token.priority,
                'coordination_reason': reason
            }
        else:
            # old_token_data là dict
            log_vals = {
                'patient_id': self.id,
                'coordination_type': coordination_type,
                'from_service_id': old_token_data['service_id'],
                'to_service_id': new_token.service_id.id,
                'from_room_id': old_token_data['room_id'],
                'to_room_id': new_token.room_id.id,
                'old_position': old_token_data['position'],
                'new_position': new_token.position,
                'old_token_id': old_token_data['id'],
                'new_token_id': new_token.id,
                'priority': new_token.priority,
                'coordination_reason': reason
            }

        self.env[MATE_QUEUE_COORDINATION_LOG].create(log_vals)

    def action_swap_to_service(self):
        """
        Nút điều phối nhanh - Chuyển sang dịch vụ với phòng được recommend
        Context cần có: target_service_id
        """
        target_service_id = self.env.context.get('target_service_id')
        if not target_service_id:
            return self._get_error_response(_('Cannot determine target service'))

        # Validation cơ bản
        validation_result = self._validate_service_coordination_request(target_service_id)
        if validation_result.get('error'):
            return self._get_error_response(
                validation_result.get('message', _('Unknown error')), 
                validation_result.get('type', 'danger')
            )

        # Lấy dịch vụ đích và tìm phòng tối ưu
        target_service = validation_result['target_service']
        target_room = self._find_least_loaded_room_for_service(target_service)
        
        if not target_room:
            return self._get_error_response(
                _('No available room for service %s') % target_service.name
            )

        # Sử dụng hàm chung để điều phối
        return self._coordinate_to_room(
            target_service_id=target_service.id,
            target_room_id=target_room.id,
            coordination_type=COORDINATION_SERVICE_CHANGE
        )
        
    def action_coordinate_room(self):
        """Chuyển phòng cho dịch vụ hiện tại"""
        target_room_id = self.env.context.get('target_room_id')
        
        if not target_room_id:
            return self._get_error_response(_('Cannot determine target room'))
        
        try:
            target_room_id = int(target_room_id)
        except (ValueError, TypeError):
            return self._get_error_response(_('Invalid room ID'))
        
        return self._coordinate_to_room(
            target_service_id=None,
            target_room_id=target_room_id,
            coordination_type=COORDINATION_ROOM_CHANGE
        )

    def action_coordinate_service_room(self):
        """
        Điều phối với phòng được chọn từ wizard
        Được gọi khi chọn dịch vụ từ danh sách dịch vụ có thể điều phối và phòng được chọn
        Context cần có: target_service_id, target_room_id
        """
        target_service_id = self.env.context.get('target_service_id')
        target_room_id = self.env.context.get('target_room_id')
        
        if not target_service_id or not target_room_id:
            return self._get_error_response(_('Missing service or room information'))
        
        try:
            target_service_id = int(target_service_id)
            target_room_id = int(target_room_id)
        except (ValueError, TypeError):
            return self._get_error_response(_('Invalid service or room ID'))
        
        return self._coordinate_to_room(
            target_service_id=target_service_id,
            target_room_id=target_room_id,
            coordination_type=COORDINATION_SERVICE_CHANGE
        )
    
    def _coordinate_to_room(self, target_service_id, target_room_id, coordination_type):
        """
        Hàm chung để điều phối phòng/dịch vụ
        
        Args:
            target_service_id: ID dịch vụ đích (None nếu room_change)
            target_room_id: ID phòng đích
            coordination_type: COORDINATION_ROOM_CHANGE hoặc COORDINATION_SERVICE_CHANGE
        """
        _logger = logging.getLogger(__name__)
        _logger.info("=== ĐIỀU PHỐI %s ===", coordination_type.upper())

        # Bước 1: Validation
        validation_result = self._get_coordination_validation_result(
            coordination_type, target_service_id, target_room_id
        )
        
        if validation_result.get('error'):
            return self._get_error_response(
                validation_result.get('message', 'Unknown error'),
                validation_result.get('type', 'danger')
            )

        try:
            # Bước 2: Lấy thông tin từ validation
            current_token = validation_result['current_token']
            target_room = validation_result['target_room']
            
            if coordination_type == COORDINATION_SERVICE_CHANGE:
                target_service = validation_result['target_service']
            else:  # room_change
                target_service = current_token.service_id

            # Bước 3: Lưu dữ liệu token cũ trước khi thao tác
            old_token_data = self._prepare_old_token_data(current_token)

            # Bước 4: Tạo token mới
            new_token = self._create_coordination_token(current_token, target_service, target_room)

            # Bước 5: Ghi log (sử dụng hàm thống nhất)
            reason = self._get_coordination_reason(coordination_type, old_token_data, target_service, target_room)
            self._log_coordination(old_token_data, new_token, coordination_type, reason)

            # Bước 6: Xóa token cũ
            current_token.unlink()

            # Bước 7: Làm mới cache nếu cần
            if coordination_type == COORDINATION_SERVICE_CHANGE:
                self.invalidate_recordset(['available_coordination_service_ids'])

            # Bước 8: Return success
            return self._get_success_response()

        except Exception as e:
            _logger.error("Điều phối %s thất bại: %s", coordination_type, str(e))
            return self._get_error_response(
                _('Cannot perform coordination: %s') % str(e),
                error_type='danger',
                sticky=True
            )
        
    def _get_coordination_validation_result(self, coordination_type, target_service_id=None, target_room_id=None):
        """
        Validation chung cho tất cả loại điều phối
        Returns: dict with 'error', 'current_token', 'target_service', 'target_room'
        """
        if coordination_type == COORDINATION_ROOM_CHANGE:
            # Dùng validation sẵn có cho room change
            return self._validate_room_coordination_request(target_room_id)
        
        elif coordination_type == COORDINATION_SERVICE_CHANGE:
            # Validation cho service change
            if not target_service_id or not target_room_id:
                return {
                    'error': True,
                    'message': _('Missing service or room information'),
                    'type': 'danger'
                }
            
            try:
                # Kiểm tra tồn tại của service và room
                target_service = self.env['product.product'].browse(target_service_id)
                target_room = self.env['hr.department'].browse(target_room_id)

                if not target_service.exists() or not target_room.exists():
                    return {
                        'error': True,
                        'message': _('Service or room does not exist'),
                        'type': 'danger'
                    }

                # Kiểm tra phòng có hỗ trợ dịch vụ không
                if target_room.service_id.id != target_service.id:
                    return {
                        'error': True,
                        'message': _('Room does not support this service'),
                        'type': 'danger'
                    }

                # Tìm token đang chờ hiện tại
                current_token = self.queue_history_ids.filtered(lambda t: t.state == 'waiting')
                if not current_token:
                    return {
                        'error': True,
                        'message': _('No waiting token found'),
                        'type': 'warning'
                    }

                # Kiểm tra xem có cần thiết phải chuyển không (tránh chuyển không cần thiết)
                current_token = current_token[0]
                if (current_token.service_id.id == target_service.id and 
                    current_token.room_id.id == target_room.id):
                    return {
                        'error': True,
                        'message': _('Already in the same service and room'),
                        'type': 'info'
                    }

                return {
                    'error': False,
                    'current_token': current_token,
                    'target_service': target_service,
                    'target_room': target_room
                }

            except Exception as e:
                return {
                    'error': True,
                    'message': str(e),
                    'type': 'danger'
                }
        
        return {
            'error': True,
            'message': _('Unknown coordination type'),
            'type': 'danger'
        }

    def _get_coordination_reason(self, coordination_type, old_token_data, target_service, target_room):
        """
        Tạo lý do điều phối - Hỗ trợ cả token object và dict
        """
        if coordination_type == COORDINATION_ROOM_CHANGE:
            old_room_name = old_token_data.get('room_name', 'Unknown') if isinstance(old_token_data, dict) else \
                        (old_token_data.room_id.name if old_token_data.room_id else 'Unknown')
            return _('Room changed from %(old_room)s to %(new_room)s') % {
                'old_room': old_room_name,
                'new_room': target_room.name
            }
        elif coordination_type == COORDINATION_SERVICE_CHANGE:
            old_service_name = old_token_data.get('service_name', 'Unknown') if isinstance(old_token_data, dict) else \
                            old_token_data.service_id.name
            return _('Coordinated from service %(old_service)s to %(new_service)s') % {
                'old_service': old_service_name,
                'new_service': target_service.name
            }
        else:
            return _('Coordination completed')

    def _get_response(self, message, response_type='success', error_type='info', sticky=False):
        """Response thống nhất cho tất cả trường hợp"""
        if response_type == 'success':
            return {
                'type': IR_ACTIONS_CLIENT,
                'tag': 'reload',
                'params': {
                    'menu_id': self.env.context.get('menu_id'),
                },
                'context': self.env.context,
            }
        else:  # error
            return {
                'type': IR_ACTIONS_CLIENT,
                'tag': 'display_notification',
                'params': {
                    'title': _('Error') if error_type == 'danger' else _('Warning'),
                    'message': str(message),
                    'type': error_type,
                    'sticky': sticky
                }
            }

    def _get_success_response(self):
        """Response thành công"""
        return self._get_response('', 'success')

    def _get_error_response(self, error_msg, error_type='danger', sticky=False):
        """Response lỗi"""
        return self._get_response(error_msg, 'error', error_type, sticky)

    def action_view_coordination_history_patient(self):
        """Xem log điều phối từ chi tiết bệnh nhân"""
        self.ensure_one()
        return {
            'name': 'Lịch sử điều phối - %s' % self.name,
            'type': IR_ACTIONS_WINDOW,
            'res_model': MATE_QUEUE_COORDINATION_LOG,
            'view_mode': 'list,form',
            'view_id': False,
            'views': [(self.env.ref('mate_smart_queue.view_queue_coordination_log_list').id, 'list')],
            'domain': [('patient_id', '=', self.id)],
            'context': dict(self.env.context,
                            default_patient_id=self.id,
                            search_default_today=1),  # Mặc định filter hôm nay
            'target': 'current',
        }
    
    def action_open_service_room_selection(self):
        """Mở cửa sổ chọn phòng cho dịch vụ được chỉ định từ danh sách ưu tiên"""
        self.ensure_one()
        
        if not self.current_waiting_token_id:
            raise UserError(_('No service waiting'))  # Sử dụng constant có sẵn
        
        # Lấy service_id từ context
        target_service_id = self.env.context.get('target_service_id')
        if not target_service_id:
            raise UserError(_('Missing target service information'))
        
        # Xác thực dịch vụ đích
        target_service = self.env['product.product'].browse(target_service_id)
        if not target_service.exists():
            raise UserError(_('Service does not exist'))
        
        current_token = self.current_waiting_token_id
        
        return {
            'name': _('Clinic Options'),
            'type': IR_ACTIONS_WINDOW,
            'res_model': 'mate.queue.room.selection.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('mate_smart_queue.view_queue_room_selection_wizard_simple_form').id,
            'target': 'new',
            'context': {
                'default_patient_id': self.id,
                'default_service_id': target_service.id,
                'default_current_room_id': current_token.room_id.id if current_token.room_id else False,
                'default_coordination_type': COORDINATION_SERVICE_CHANGE
            }
        }
    
    def _prepare_old_token_data(self, current_token):
        """Chuẩn bị dữ liệu token cũ để sử dụng an toàn"""
        return {
            'id': current_token.id,
            'service_id': current_token.service_id.id,
            'service_name': current_token.service_id.name,
            'room_id': current_token.room_id.id if current_token.room_id else False,
            'room_name': current_token.room_id.name if current_token.room_id else '',
            'position': current_token.position,
            'priority': current_token.priority,
            'priority_id': current_token.priority_id.id if current_token.priority_id else False,
            'emergency': current_token.emergency,
            'package_id': current_token.package_id.id if current_token.package_id else False,
        }
