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

    coordination_service_info = fields.Text(
        string='Coordination Service Details',
        compute='_compute_coordination_service_info',
        store=False
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

    # Thêm 8 trường (4 progress + 4 completed)
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
            
            _logger = logging.getLogger(__name__)
            _logger.info("YYYYYYY")
            _logger.info(service_groups)
            _logger.info(package_services)
            
            # Danh sách 4 trường để map
            progress_fields = ['group_1_progress', 'group_2_progress', 'group_3_progress', 'group_4_progress']
            completed_fields = ['group_1_completed', 'group_2_completed', 'group_3_completed', 'group_4_completed']
            
            
            for idx, group in enumerate(service_groups[:4]):  # Chỉ lấy tối đa 4 nhóm
                # Lấy các dịch vụ trong nhóm thuộc gói này
                group_services_in_package = package_services.filtered(
                    lambda s: s.service_group_id.id == group.id
                )
                total_services = len(group_services_in_package)
                
                # Đếm số dịch vụ đã hoàn thành trong nhóm
                completed_tokens = patient.queue_history_ids.filtered(
                    lambda t: (t.service_id.service_group_id.id == group.id and 
                            t.state == 'completed' and
                            t.service_id.id in group_services_in_package.ids)
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
            'type': 'ir.actions.act_window',
            'res_model': MATE_QUEUE_ROOM_SELECTION_WIRARD,
            'view_mode': 'form',
            'view_id': self.env.ref('mate_smart_queue.view_queue_room_selection_wizard_simple_form').id,
            'target': 'new',
            'context': {
                'default_patient_id': self.id,
                'default_service_id': token.service_id.id,
                'default_current_room_id': token.room_id.id if token.room_id else False,
                'default_coordination_type': 'room_change'
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

    @api.depends('available_coordination_service_ids')
    def _compute_coordination_service_info(self):
        """Tính toán thông tin chi tiết dịch vụ điều phối"""
        import json

        for patient in self:
            if not patient.available_coordination_service_ids:
                patient.coordination_service_info = '{}'
                continue

            info_dict = {}
            for service in patient.available_coordination_service_ids:
                service_info = patient.get_service_coordination_info(service.id)
                info_dict[str(service.id)] = service_info

            patient.coordination_service_info = json.dumps(info_dict, ensure_ascii=False)

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

    @api.depends('queue_history_ids', 'queue_history_ids.state', 'completed_service_ids',
                 'queue_package_id', 'queue_package_id.service_ids')
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

    def _get_room_queue_info(self, room):
        """Lấy thông tin hàng đợi của phòng"""
        if not room:
            return {'waiting_count': 0, 'priority_count': 0}

        # Đếm token đang chờ trong phòng
        waiting_tokens = self.env[MATE_QUEUE_TOKEN].search([
            ('room_id', '=', room.id),
            ('state', '=', 'waiting')
        ])

        # Đếm token ưu tiên
        priority_tokens = waiting_tokens.filtered(
            lambda t: t.emergency or t.priority > 5
        )

        return {
            'waiting_count': len(waiting_tokens),
            'priority_count': len(priority_tokens)
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
            'type': 'ir.actions.act_window',
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
                    patient.estimated_time = _("1 hour 12 minutes")
            else:
                patient.estimated_time = _("1 hour 12 minutes")

    def action_swap_to_service(self):
        """
        Điều phối: Chuyển từ dịch vụ đang chờ sang dịch vụ mới được chọn => Có Recommend target_room
        Context cần có: target_service_id
        """
        target_service_id = self.env.context.get('target_service_id')
        if not target_service_id:
            return {
                'type': IR_ACTIONS_CLIENT,
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Cannot determine target service'),
                    'type': 'danger',
                    'sticky': False
                }
            }

        try:
            # Bước 1: Xác thực
            validation_result = self._validate_service_coordination_request(target_service_id)
            if validation_result.get('error'):
                return {
                    'type': IR_ACTIONS_CLIENT,
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Coordination Error'),
                        'message': validation_result.get('message', _('Unknown error')),
                        'type': 'danger',
                        'sticky': False
                    }
                }

            # Bước 2: Lấy token đang chờ hiện tại và dịch vụ đích
            current_token = validation_result['current_token']
            target_service = validation_result['target_service']

            # Bước 3: Tìm phòng ít tải nhất cho dịch vụ đích
            target_room = self._find_least_loaded_room_for_service(target_service)
            if not target_room:
                return {
                    'type': IR_ACTIONS_CLIENT,
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Error'),
                        'message': _('No available room for service %s') % target_service.name,
                        'type': 'danger',
                        'sticky': False
                    }
                }

            # Bước 4: Tạo token mới
            new_token = self._create_coordination_token(current_token, target_service, target_room)

            # Bước 5: Ghi log điều phối
            self._log_coordination(
                current_token=current_token,
                new_token=new_token,
                coordination_type='service_change',
                reason=_('Coordinated from service %s to %s') % (current_token.service_id.name, target_service.name)
            )

            # Bước 6: Xóa token cũ
            current_token.unlink()

            # Bước 7: Làm mới các trường tính toán
            self.invalidate_recordset(['available_coordination_service_ids'])

            return {
                'type': IR_ACTIONS_CLIENT,
                'tag': 'reload',
                'params': {
                    'menu_id': self.env.context.get('menu_id'),
                },
                'context': self.env.context,
            }

        except Exception as e:
            return {
                'type': IR_ACTIONS_CLIENT,
                'tag': 'display_notification',
                'params': {
                    'title': _('System Error'),
                    'message': _('Cannot perform coordination: %s') % str(e),
                    'type': 'danger',
                    'sticky': True
                }
            }

    def action_coordinate_room(self):
        """
        Thực hiện điều phối phòng cho cùng dịch vụ
        Context cần có: target_room_id
        """
        _logger = logging.getLogger(__name__)

        _logger.info("=== ĐIỀU PHỐI PHÒNG ===")
        _logger.info("Context: %s", self.env.context)

        target_room_id = self.env.context.get('target_room_id')
        if not target_room_id:
            return {
                'type': IR_ACTIONS_CLIENT,
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Cannot determine target room'),
                    'type': 'danger'
                }
            }

        try:
            # Xác thực yêu cầu
            validation_result = self._validate_room_coordination_request(target_room_id)
            if validation_result.get('error'):
                return validation_result

            current_token = validation_result['current_token']
            target_room = validation_result['target_room']

            # Tạo token mới trong phòng đích
            new_token = self._create_coordination_token(
                current_token,
                current_token.service_id,
                target_room
            )

            # Ghi log điều phối
            self._log_coordination(
                current_token=current_token,
                new_token=new_token,
                coordination_type='room_change',
                reason=_('Room changed from %s to %s') % (current_token.room_id.name, target_room.name)
            )

            # Xóa token cũ
            current_token.unlink()

            return {
                'type': IR_ACTIONS_CLIENT,
                'tag': 'reload',
                'params': {
                    'menu_id': self.env.context.get('menu_id'),
                }
            }

        except Exception as e:
            _logger.error("Điều phối phòng thất bại: %s", str(e))
            return {
                'type': IR_ACTIONS_CLIENT,
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': str(e),
                    'type': 'danger'
                }
            }

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

    def _log_coordination(self, current_token, new_token, coordination_type, reason):
        """Ghi log hoạt động điều phối"""
        log_vals = {
            'patient_id': self.id,
            'coordination_type': coordination_type,
            'from_service_id': current_token.service_id.id,
            'to_service_id': new_token.service_id.id,
            'from_room_id': current_token.room_id.id if current_token.room_id else False,
            'to_room_id': new_token.room_id.id,
            'old_position': current_token.position,
            'new_position': new_token.position,
            'old_token_id': current_token.id,
            'new_token_id': new_token.id,
            'priority': new_token.priority,
            'coordination_reason': reason
        }

        self.env[MATE_QUEUE_COORDINATION_LOG].create(log_vals)

    def action_coordinate_service_room(self):
        """
        Điều phối cho dịch vụ với phòng được chọn
        Được gọi khi chọn dịch vụ từ danh sách dịch vụ có thể điều phối và phòng được chọn
        Context cần có: target_service_id, target_room_id
        """
        _logger = logging.getLogger(__name__)

        target_service_id = self.env.context.get('target_service_id')
        target_room_id = self.env.context.get('target_room_id')

        if not target_service_id or not target_room_id:
            return {
                'type': IR_ACTIONS_CLIENT,
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Missing service or room information'),
                    'type': 'danger'
                }
            }

        try:
            target_service = self.env[PRODUCT_PRODUCT].browse(target_service_id)
            target_room = self.env[HR_DEPARTMENT].browse(target_room_id)

            if not target_service.exists() or not target_room.exists():
                raise UserError(_('Service or room does not exist'))

            # Kiểm tra xem phòng có hỗ trợ dịch vụ không
            if target_room.service_id.id != target_service.id:
                raise UserError(_('Room does not support this service'))

            # Tìm token đang chờ hiện tại cho dịch vụ này
            current_token = self.queue_history_ids.filtered(
                lambda t: t.state == 'waiting' and t.service_id.id == target_service_id
            )

            if current_token:
                # Đã có token cho dịch vụ này - chỉ cần đổi phòng
                old_room = current_token.room_id

                # Tạo token mới trong phòng mới
                new_token = self._create_coordination_token(current_token, target_service, target_room)

                # Ghi log điều phối
                self._log_coordination(
                    current_token=current_token,
                    new_token=new_token,
                    coordination_type='room_change',
                    reason=_('Room changed from %(old_room)s to %(new_room)s') % {
                        'old_room': old_room.name,
                        'new_room': target_room.name
                    }
                )

            else:
                # Không có token hiện tại - tạo mới
                new_token = self.env[MATE_QUEUE_TOKEN].with_context(
                    skip_auto_assignment=True
                ).create({
                    'patient_id': self.id,
                    'service_id': target_service.id,
                    'room_id': target_room.id,
                    'state': 'waiting',
                    'notes': _('Created via room customization')
                })

                # Ghi log điều phối
                self._log_coordination(
                    current_token=current_token,
                    new_token=new_token,
                    coordination_type='service_change',
                    reason=_('Coordinated from service %s to %s') % (current_token.service_id.name, target_service.name)
                )

            # Bước 6: Xóa token cũ
            current_token.unlink()
            
            # Làm mới các trường tính toán
            self.invalidate_recordset(['available_coordination_service_ids'])

            return {
                'type': IR_ACTIONS_CLIENT,
                'tag': 'reload',
                'params': {
                    'menu_id': self.env.context.get('menu_id'),
                }
            }

        except Exception as e:
            _logger.error("Điều phối dịch vụ phòng thất bại: %s", str(e))
            return {
                'type': IR_ACTIONS_CLIENT,
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': str(e),
                    'type': 'danger'
                }
            }
        
    
    def action_view_coordination_history_patient(self):
        """Xem log điều phối từ chi tiết bệnh nhân"""
        self.ensure_one()
        return {
            'name': 'Lịch sử điều phối - %s' % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'mate.queue.coordination.log',
            'view_mode': 'list,form',
            'view_id': False,
            'views': [(self.env.ref('mate_smart_queue.view_queue_coordination_log_list').id, 'list')],
            'domain': [('patient_id', '=', self.id)],
            'context': dict(self.env.context, 
                        default_patient_id=self.id,
                        search_default_today=1),  # Mặc định filter hôm nay
            'target': 'current',
        }
