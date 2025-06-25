# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
import hashlib
import logging

_logger = logging.getLogger(__name__)

NEXT_SERVICE = "next_service"
DONE_SERVICE = "service_completed"
TEXT_INSTRUCT = "Vui lòng hướng dẫn bệnh nhân đến %s cho dịch vụ %s"
FLOAT_EPSILON = 1e-9

HR_DEPARTMENT = 'hr.department'
PRODUCT_PRODUCT = 'product.product'
HIS_PATIENT = 'his.patient'
MATE_HEALTH_CHECK_PACKAGE = 'mate.health.check.package'

MATE_QUEUE_TOKEN = "mate.queue.token"
MATE_HEALTH_CHECK_GROUP = "mate.health.check.group"
MATE_QUEUE_PRIORITY = "mate.queue.priority"
MATE_QUEUE_SERVICE_ROUTE = "mate.queue.service.route"

IR_ACTIONS_CLIENT = "ir.actions.client"
MATE_QUEUE_SERVICE_GROUP_ROUTE = "mate.queue.service.group.route"


class QueueToken(models.Model):
    _name = MATE_QUEUE_TOKEN
    _description = 'Patient Queue Token'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, position, create_date asc'

    name = fields.Char(string='Token Code', readonly=True, default=lambda self: _('New'))
    patient_id = fields.Many2one(HIS_PATIENT, string='Patient', required=True)
    service_id = fields.Many2one(PRODUCT_PRODUCT, string='Service', required=True, ondelete='cascade')
    room_id = fields.Many2one(HR_DEPARTMENT, string='Assigned Room', tracking=True, ondelete='cascade')
    position = fields.Integer(string='Queue Position', tracking=True, default=0, index=True)
    priority = fields.Integer(string='Priority Level', default=0, tracking=True)
    priority_id = fields.Many2one(MATE_QUEUE_PRIORITY, string='Priority Type', tracking=True, ondelete='cascade')
    estimated_wait_time = fields.Float(string='Estimated Wait Time (minutes)', compute='_compute_wait_time')
    state = fields.Selection([
        ('draft', 'Scheduled'),  # Trạng thái mới này cho token đã tạo nhưng chưa đưa vào hàng đợi
        ('waiting', 'Waiting'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    patient_pid = fields.Char(
        string='PID',
        related='patient_id.patient_id_number',
        readonly=True,
        store=True
    )
    start_time = fields.Datetime(string='Start Time')
    end_time = fields.Datetime(string='End Time')
    actual_duration = fields.Float(string='Actual Duration (minutes)', compute='_compute_duration', store=True)
    notes = fields.Text(string='Notes')
    next_service_id = fields.Many2one(PRODUCT_PRODUCT, string='Next Service', compute='_compute_next_service',
                                      ondelete='cascade')
    package_id = fields.Many2one(MATE_HEALTH_CHECK_PACKAGE, string='Service Package', ondelete='cascade')
    emergency = fields.Boolean(string='Emergency', default=False, tracking=True)
    color = fields.Integer(string='Color', compute='_compute_color')
    service_group_id = fields.Many2one(MATE_HEALTH_CHECK_GROUP, string='Service Group', ondelete='cascade')
    is_parallel = fields.Boolean(string='Is Parallel Service', compute='_compute_is_parallel', store=True)
    next_recommended_service_id = fields.Many2one(
        PRODUCT_PRODUCT,
        string='Next Recommended Service',
        compute='_compute_next_recommended_service',
        ondelete='cascade'
    )

    parallel_token_ids = fields.Many2many(MATE_QUEUE_TOKEN, 'queue_token_parallel_rel', 'token_id', 'parallel_token_id',
                                          string='Parallel Tokens',
                                          help="Other tokens in the same parallel service group")
    origin_token_id = fields.Many2one(MATE_QUEUE_TOKEN, string='Origin Token',
                                      help="Original token that created this token",
                                      ondelete='cascade')

    @api.depends('service_group_id')
    def _compute_is_parallel(self):
        for token in self:
            if token.service_group_id and len(token.service_group_id.service_ids) > 1:
                token.is_parallel = True
            else:
                token.is_parallel = False

    @api.model
    def reorder_position(self, token_id, new_position, old_position):
        """
        Xử lý khi token được kéo thả đến vị trí mới
        """
        _logger.info("=== REORDER POSITION START ===")
        _logger.info("Token ID: %s, Old Position: %s, New Position: %s", token_id, old_position, new_position)

        # Ensure new_position and old_position are integers
        try:
            new_position = int(new_position)
            old_position = int(old_position)
            token_id = int(token_id)
        except (ValueError, TypeError):
            _logger.error("Invalid position values")
            return False

        token = self.browse(token_id)

        if not token.exists():
            _logger.error("Token không tồn tại: %s", token_id)
            return False

        if token.state != 'waiting':
            _logger.error("Token không ở trạng thái waiting: %s", token.state)
            raise UserError(_('can_only_change_waiting_token_position'))

        if new_position == old_position:
            _logger.info("Vị trí không thay đổi, bỏ qua")
            return True

        room_id = token.room_id.id
        _logger.info("Room ID: %s", room_id)

        # Use a transaction to ensure data consistency
        with self.env.cr.savepoint():
            try:
                # Get all waiting tokens in the room ordered by position
                tokens_in_room = self.search([
                    ('room_id', '=', room_id),
                    ('state', '=', 'waiting'),
                    ('id', '!=', token_id)  # Exclude the moved token
                ], order='position')

                _logger.info("Found %s other tokens in room", len(tokens_in_room))

                # Update position of the moved token
                token.write({'position': new_position})

                # Reorder other tokens
                current_pos = 1
                for t in tokens_in_room:
                    if current_pos == new_position:
                        current_pos += 1  # Skip the position we just assigned
                    t.write({'position': current_pos})
                    current_pos += 1

                # Flush to database
                self.env.cr.flush()

                # Invalidate cache
                self.invalidate_recordset(['position'])

                # Log the movement
                self._create_position_change_log(token, old_position, new_position)

                # Notify queue change
                self._notify_queue_change(token.room_id)

                _logger.info("=== REORDER POSITION SUCCESS ===")
                return True

            except Exception as e:
                _logger.error("Error during reorder: %s", str(e))
                raise UserError(_('error_changing_token_position') % str(e))

    def _create_position_change_log(self, token, old_pos, new_pos):
        """Tạo log khi thay đổi vị trí"""
        try:
            log_vals = {
                'patient_id': token.patient_id.id,
                'coordination_type': 'position_change',
                'from_service_id': token.service_id.id,
                'to_service_id': token.service_id.id,
                'from_room_id': token.room_id.id,
                'to_room_id': token.room_id.id,
                'old_position': old_pos,
                'new_position': new_pos,
                'old_token_id': token.id,
                'new_token_id': token.id,
                'priority': token.priority,
                'coordination_reason': f'Điều chỉnh vị trí từ {old_pos} đến {new_pos}'
            }

            self.env['mate.queue.coordination.log'].create(log_vals)
            _logger.info("Đã tạo log điều phối cho token %s", token.name)
        except Exception as e:
            _logger.error("Lỗi khi tạo log điều phối: %s", str(e))

    @api.model_create_multi
    def create(self, vals_list):
        """
        Ghi đè phương thức create để tạo mã token tự động và thực hiện quy trình phân phối
        Quy trình:
        1. Tạo mã token
        2. Tính toán mức ưu tiên dựa trên thông tin bệnh nhân
        3. Chỉ định phòng bằng thuật toán hash
        4. Thêm vào hàng đợi và sắp xếp theo ưu tiên
        5. Override create method với logic skip auto assignment cho coordination
        """
        # Generate sequence cho tất cả tokens
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(MATE_QUEUE_TOKEN) or _('New')

        # Tạo tokens như bình thường
        tokens = super(QueueToken, self).create(vals_list)

        # Post-processing for each token
        for token in tokens:
            # 🔑 KEY: Kiểm tra context flag
            if self.env.context.get('skip_auto_assignment'):
                # Token từ coordination → Skip auto flow
                continue

            # Token bình thường → Chạy full auto flow
            token._calculate_priority()
            token._assign_room_by_hash()
            token._add_to_queue_and_sort()
            token._send_notifications('new_token')

        return tokens

    def _calculate_priority(self):
        """
        Tính toán mức ưu tiên dựa trên thuộc tính bệnh nhân

        Quy tắc ưu tiên:
        - Khẩn cấp: 10
        - Mức độ ưu tiên bác sĩ chỉ định: 5
        - VIP: 4
        - Tình trạng cấp thiết: 3
        - Mang thai/Khuyết tật: 2
        - Người cao tuổi (>65): 1
        - Thông thường: 0
        """
        for token in self:
            # Kiểm tra và xử lý trường hợp khẩn cấp trước
            if token.emergency:
                self._set_emergency_priority(token)
                continue

            # Tính toán mức ưu tiên cho các trường hợp không khẩn cấp
            priority = self._compute_patient_priority(token.patient_id)

            # Đặt mức ưu tiên và loại ưu tiên tương ứng
            token.priority = priority
            self._set_priority_type(token, priority)

    def _set_emergency_priority(self, token):
        """Đặt mức ưu tiên cao nhất cho trường hợp khẩn cấp"""
        token.priority = 10
        token.priority_id = self.env.ref('mate_smart_queue.priority_emergency', False)

    def _compute_patient_priority(self, patient):
        """Tính toán mức ưu tiên dựa trên thông tin bệnh nhân"""
        priority = 0

        # Ưu tiên theo độ tuổi
        if patient.age >= 65:
            priority = max(priority, 1)

        # Kiểm tra mang thai hoặc khuyết tật
        if patient.is_pregnant or patient.is_disabled:
            priority = max(priority, 2)

        # Kiểm tra tình trạng y tế cấp thiết
        if patient.has_urgent_condition:
            priority = max(priority, 3)

        # Bệnh nhân VIP
        if patient.is_vip:
            priority = max(priority, 4)

        # Ưu tiên đặc biệt do bác sĩ chỉ định
        if patient.doctor_assigned_priority:
            priority = max(priority, 5)

        return priority

    def _set_priority_type(self, token, priority):
        ref_map = {
            0: 'priority_normal',
            1: 'priority_elderly',
            2: 'priority_special_condition',
            3: 'priority_urgent',
            4: 'priority_vip',
        }
        ref_key = ref_map.get(priority, 'priority_doctor_assigned')
        token.priority_id = self.env.ref(f'mate_smart_queue.{ref_key}', False)

    def _assign_room_by_hash(self):
        """
        Chỉ định phòng cho bệnh nhân sử dụng thuật toán hash và cân bằng tải

        Thuật toán:
        1. Nếu bệnh nhân ưu tiên cao -> chỉ định vào phòng ít tải nhất
        2. Bệnh nhân thông thường -> sử dụng hàm hash để phân bổ đều
        3. Nếu phòng đã quá tải (>150% so với phòng ít nhất) -> chuyển sang phòng ít tải
        """
        for token in self:
            # Tìm các phòng có thể thực hiện dịch vụ này
            available_rooms = self.env[HR_DEPARTMENT].search([
                ('service_id', '=', token.service_id.id),
                ('state', '=', 'open')
            ])

            if not available_rooms:
                raise UserError(_("no_available_room_for_service"))

            # Với bệnh nhân ưu tiên cao, chỉ định phòng ít tải nhất
            if token.priority > 0:
                least_loaded_room = self._get_least_loaded_room(available_rooms)
                token.room_id = least_loaded_room.id
            else:
                # Với bệnh nhân thông thường, sử dụng hash để phân bổ đều
                hash_input = f"{token.patient_id.id}-{token.service_id.id}"
                hash_value = int(hashlib.sha256(hash_input.encode()).hexdigest(), 16)
                room_index = hash_value % len(available_rooms)
                selected_room = available_rooms[room_index]

                # Kiểm tra nếu phòng được chọn đã quá tải
                least_loaded_room = self._get_least_loaded_room(available_rooms)
                if self._get_room_load(selected_room) > self._get_room_load(least_loaded_room) * 1.5:
                    # Nếu quá tải >150% so với phòng ít nhất, chuyển sang phòng ít tải
                    token.room_id = least_loaded_room.id
                else:
                    token.room_id = selected_room.id

    def _get_least_loaded_room(self, rooms):
        """
        Tìm phòng có tải thấp nhất trong danh sách phòng

        Tham số:
            rooms: Recordset các phòng cần kiểm tra

        Trả về:
            room: Phòng có tải thấp nhất
        """
        if not rooms:
            return False

        min_load = float('inf')
        least_loaded_room = rooms[0]

        for room in rooms:
            room_load = self._get_room_load(room)
            if room_load < min_load:
                min_load = room_load
                least_loaded_room = room

        return least_loaded_room

    def _get_room_load(self, room):
        """
        Tính toán tải của phòng (số người đợi / công suất)

        Tham số:
            room: Phòng cần tính tải

        Trả về:
            float: Tỷ lệ tải (số người đợi / công suất)
        """
        waiting_count = self.search_count([
            ('room_id', '=', room.id),
            ('state', '=', 'waiting')
        ])
        return waiting_count / room.capacity if room.capacity > 0 else float('inf')

    def _add_to_queue_and_sort(self):
        """
        Thêm token vào hàng đợi và sắp xếp dựa trên ưu tiên và thời gian
        Quy tắc sắp xếp:
        1. Ưu tiên cao được xếp trước
        2. Với cùng mức ưu tiên, ai đến trước được phục vụ trước (FIFO)
        """
        for token in self:
            if token.state == 'draft' and not token.is_parallel:
                # Chỉ chuyển sang waiting nếu không phải token song song
                token.state = 'waiting'

            # Lấy tất cả token đang đợi trong cùng phòng
            waiting_tokens = self.search([
                ('room_id', '=', token.room_id.id),
                ('state', '=', 'waiting')
            ])

            # Sắp xếp theo mức ưu tiên (giảm dần) và thời gian tạo (tăng dần)
            sorted_tokens = waiting_tokens.sorted(key=lambda r: (-r.priority, r.create_date))

            # Cập nhật vị trí cho mỗi token
            for index, t in enumerate(sorted_tokens):
                t.position = index + 1

            # Thông báo thay đổi hàng đợi đến màn hình hiển thị phòng
            self._notify_queue_change(token.room_id)

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        """
        Tính toán thời gian phục vụ thực tế
        """
        for token in self:
            if token.start_time and token.end_time:
                duration = (token.end_time - token.start_time).total_seconds() / 60
                token.actual_duration = duration
            else:
                token.actual_duration = 0

    def _compute_next_service(self):
        """Xác định dịch vụ tiếp theo dựa trên dịch vụ hiện tại và gói dịch vụ"""
        for token in self:
            next_service = self._get_next_service(token.service_id, token.package_id)
            token.next_service_id = next_service.id if next_service else False

    def _get_next_service(self, current_service, package):
        """Lấy dịch vụ tiếp theo dựa trên dịch vụ hiện tại và gói dịch vụ"""
        if not current_service or not package:
            _logger.info("Thiếu thông tin: current_service=%s, package=%s",
                         current_service and current_service.name,
                         package and package.name)
            return False
            # Lấy tất cả tuyến đường có thể từ dịch vụ hiện tại
        routes = self.env[MATE_QUEUE_SERVICE_ROUTE].search([
            ('service_from_id', '=', current_service.id)
        ], order='sequence')

        _logger.info("Tìm thấy %d tuyến đường cho dịch vụ %s", len(routes), current_service.name)
        if not routes:
            _logger.info("Không tìm thấy tuyến đường nào cho dịch vụ %s", current_service.name)
            return False

        # Ghi log tất cả các tuyến đường tìm thấy
        for route in routes:
            _logger.info("Tuyến đường: %s -> %s, Gói: %s",
                         route.service_from_id.name,
                         route.service_to_id.name,
                         route.package_id and route.package_id.name or "Không có")

        # Tìm tuyến đường cụ thể cho gói
        package_routes = routes.filtered(lambda r: r.package_id and r.package_id.id == package.id)
        if package_routes:
            _logger.info("Tìm thấy tuyến đường theo gói %s: %s -> %s",
                         package.name,
                         package_routes[0].service_from_id.name,
                         package_routes[0].service_to_id.name)
            return package_routes[0].service_to_id

        # Tìm tuyến đường không có gói cụ thể (chung cho tất cả)
        general_routes = routes.filtered(lambda r: not r.package_id)
        if general_routes:
            _logger.info("Tìm thấy tuyến đường chung: %s -> %s",
                         general_routes[0].service_from_id.name,
                         general_routes[0].service_to_id.name)
            return general_routes[0].service_to_id

        # Nếu không có tuyến đường nào phù hợp, trả về tuyến đầu tiên
        _logger.info("Không tìm thấy tuyến đường phù hợp, sử dụng tuyến đầu tiên: %s -> %s",
                     routes[0].service_from_id.name,
                     routes[0].service_to_id.name)
        return routes[0].service_to_id

    def _compute_color(self):
        """Tính toán màu sắc cho giao diện kanban dựa trên trạng thái và mức độ ưu tiên"""
        for token in self:
            if token.emergency:
                token.color = 1  # Màu đỏ
            elif token.priority >= 5:
                token.color = 2  # Màu cam
            elif token.priority >= 3:
                token.color = 3  # Màu vàng
            elif token.state == 'waiting':
                token.color = 5  # Màu xanh dương
            elif token.state == 'in_progress':
                token.color = 6  # Màu tím
            elif token.state == 'completed':
                token.color = 10  # Màu xanh lá cây
            else:
                token.color = 0  # Màu xám cho trạng thái hủy hoặc nháp

    def _notify_queue_change(self, room):
        """Thông báo cho màn hình phòng về sự thay đổi hàng đợi"""
        self.env['bus.bus']._sendone(
            f'room_display_{room.id}',
            'queue_updated',
            {'room_id': room.id}
        )

    def action_start_service(self):
        """Bắt đầu phục vụ token này"""
        for token in self:
            if token.state != 'waiting':
                raise UserError(_("can_only_start_waiting_tokens"))

            token.write({
                'state': 'in_progress',
                'start_time': fields.Datetime.now(),
                'position': 0
            })

            # Sắp xếp lại hàng đợi vì token này đang được phục vụ
            waiting_tokens = self.search([
                ('room_id', '=', token.room_id.id),
                ('state', '=', 'waiting')
            ])

            # Sắp xếp theo ưu tiên (giảm dần) và ngày tạo (tăng dần)
            sorted_tokens = waiting_tokens.sorted(key=lambda r: (-r.priority, r.create_date))

            # Cập nhật vị trí trong hàng đợi
            for index, t in enumerate(sorted_tokens, 1):
                t.position = index

            # Thông báo cho màn hình phòng về sự thay đổi hàng đợi
            self._notify_queue_change(token.room_id)

            # Sau khi ấn tiếp nhận => Trả ra chi tiết hồ sơ chuyên khoa
            return {
                'type': 'ir.actions.act_window',
                'name': 'Chi tiết hồ sơ chuyên khoa',
                'res_model': 'mate.queue.token',
                'res_id': token.id,
                'view_mode': 'form',
                'target': 'current',
            }

    def action_cancel(self):
        """Hủy token này"""
        for token in self:
            if token.state in ['completed', 'cancelled']:
                raise UserError(_("cannot_cancel_completed_or_cancelled_token"))

            token.write({
                'state': 'cancelled'
            })

            # Sắp xếp lại hàng đợi
            self._add_to_queue_and_sort()

    def _predict_next_service(self, patient_id, current_service_id, package_id=False):
        """
        Phương thức nâng cao để dự đoán dịch vụ tiếp theo cho bệnh nhân
        Sử dụng kết hợp quy tắc nghiệp vụ và tuyến đường được cấu hình
        """
        # Lấy thông tin cần thiết
        patient = self.env[HIS_PATIENT].browse(patient_id)
        current_service = self.env[PRODUCT_PRODUCT].browse(current_service_id)
        package = self._get_package(patient, package_id)

        # Tìm các tuyến đường phù hợp
        return self._find_appropriate_route(current_service, package, patient)

    def _get_package(self, patient, package_id):
        """Lấy gói dịch vụ của bệnh nhân"""
        if package_id:
            return self.env[MATE_HEALTH_CHECK_PACKAGE].browse(package_id)
        return patient.queue_package_id

    def _find_appropriate_route(self, current_service, package, patient):
        """Tìm tuyến đường phù hợp từ dịch vụ hiện tại"""
        # Tìm tất cả các tuyến đường có thể từ dịch vụ hiện tại
        all_routes = self.env[MATE_QUEUE_SERVICE_ROUTE].search([
            ('service_from_id', '=', current_service.id)
        ], order='sequence')

        # Nếu không có tuyến đường, trả về False
        if not all_routes:
            return False

        # Ưu tiên tuyến đường cụ thể cho gói dịch vụ nếu có
        if package:
            package_routes = all_routes.filtered(lambda r: r.package_id.id == package.id)
            if package_routes:
                return package_routes[0].service_to_id

        # Tìm tuyến đường không có điều kiện hoặc có điều kiện phù hợp
        return self._evaluate_route_conditions(all_routes, patient, current_service, package)

    def _evaluate_route_conditions(self, routes, patient, current_service, package):
        """Đánh giá các điều kiện của tuyến đường"""
        for route in routes:
            if not route.condition or not route.condition.strip():
                # Nếu không có điều kiện, sử dụng tuyến đường mặc định
                return route.service_to_id
            else:
                # Đánh giá điều kiện
                if self._check_route_condition(route, patient, current_service, package):
                    return route.service_to_id

        # Mặc định, trả về tuyến đường đầu tiên
        return routes[0].service_to_id

    def _check_route_condition(self, route, patient, current_service, package):
        """Kiểm tra điều kiện của tuyến đường"""
        # Chuẩn bị môi trường an toàn để đánh giá
        local_dict = {
            'patient': patient,
            'current_service': current_service,
            'package': package,
        }
        try:
            return safe_eval(route.condition, local_dict=local_dict)
        except Exception as e:
            # Ghi log lỗi nhưng không làm gián đoạn luồng
            _logger.error(f"Lỗi khi đánh giá điều kiện tuyến: {str(e)}")
            return False

    # Thêm các phương thức này vào class QueueToken
    def _send_notifications(self, notification_type):
        """
        Gửi thông báo dựa trên loại thông báo và cấu hình hệ thống

        Tham số:
            notification_type (str): Loại thông báo (new_token, token_called, room_change)
        """
        self.ensure_one()
        patient = self.patient_id

        # Kiểm tra cấu hình thông báo
        ir_config = self.env['ir.config_parameter'].sudo()
        enable_sms = ir_config.get_param('mate_smart_queue.enable_sms', 'False').lower() == 'true'
        enable_email = ir_config.get_param('mate_smart_queue.enable_email', 'False').lower() == 'true'

        # Gửi thông báo SMS nếu được kích hoạt và bệnh nhân có số điện thoại
        if enable_sms and patient.mobile:
            self._send_sms_notification(notification_type, ir_config)

        # Gửi thông báo email nếu được kích hoạt và bệnh nhân có email
        if enable_email and patient.email:
            self._send_email_notification(notification_type, ir_config)

    def _send_sms_notification(self, notification_type, ir_config):
        """Gửi thông báo SMS dựa trên loại thông báo"""
        try:
            template_id = self._get_sms_template_id(notification_type, ir_config)
            if template_id:
                self.env['sms.template'].browse(template_id).send_sms(self.id)
        except Exception as e:
            _logger.error("Lỗi khi gửi SMS: %s", str(e))

    def _send_email_notification(self, notification_type, ir_config):
        """Gửi thông báo email dựa trên loại thông báo"""
        try:
            template_id = self._get_email_template_id(notification_type, ir_config)
            if template_id:
                template = self.env['mail.template'].browse(template_id)
                template.send_mail(self.id, force_send=True)
        except Exception as e:
            _logger.error("Lỗi khi gửi email: %s", str(e))

    def _get_sms_template_id(self, notification_type, ir_config):
        """Lấy ID mẫu SMS dựa trên loại thông báo"""
        if notification_type == 'new_token':
            return int(ir_config.get_param('mate_smart_queue.sms_template_id', '0')) or \
                self.env.ref('mate_smart_queue.sms_template_new_token').id
        elif notification_type == 'token_called':
            return self.env.ref('mate_smart_queue.sms_template_token_called').id
        elif notification_type == 'room_change':
            return self.env.ref('mate_smart_queue.sms_template_room_change').id
        return False

    def _get_email_template_id(self, notification_type, ir_config):
        """Lấy ID mẫu email dựa trên loại thông báo"""
        if notification_type == 'new_token':
            return int(ir_config.get_param('mate_smart_queue.email_template_id', '0')) or \
                self.env.ref('mate_smart_queue.email_template_new_token').id
        elif notification_type == 'token_called':
            return self.env.ref('mate_smart_queue.email_template_token_called').id
        elif notification_type == 'room_change':
            return self.env.ref('mate_smart_queue.email_template_room_change').id
        return False

    @api.model
    def _run_load_balancing(self):
        """Công việc định kỳ cân bằng tải giữa các phòng"""
        # Lấy cấu hình cân bằng tải
        config = self._get_load_balancing_config()

        # Tìm phòng mở và đóng
        open_rooms, closed_rooms = self._get_rooms_by_state()

        # Nếu không có phòng mở nào, không thực hiện cân bằng tải
        if not open_rooms:
            return

        # Xử lý các phòng đã đóng
        self._process_closed_rooms(closed_rooms, open_rooms)

        # Phân loại phòng thành quá tải và nhàn rỗi
        overloaded_rooms, underloaded_rooms = self._classify_rooms_by_load(open_rooms, config['wait_threshold'])

        # Xử lý các phòng quá tải
        self._process_overloaded_rooms(overloaded_rooms, underloaded_rooms, config['max_patients_to_move'])

    def _get_load_balancing_config(self):
        """Lấy cấu hình cân bằng tải từ tham số hệ thống"""
        ir_config = self.env['ir.config_parameter'].sudo()
        return {
            'wait_threshold': float(ir_config.get_param('mate_smart_queue.wait_threshold', '30.0')),
            'max_patients_to_move': int(ir_config.get_param('mate_smart_queue.max_patients_to_move', '3'))
        }

    def _get_rooms_by_state(self):
        """Phân loại phòng theo trạng thái (mở/đóng)"""
        open_rooms = self.env[HR_DEPARTMENT].search([('state', '=', 'open')])
        closed_rooms = self.env[HR_DEPARTMENT].search([('state', '!=', 'open')])
        return open_rooms, closed_rooms

    def _classify_rooms_by_load(self, open_rooms, wait_threshold):
        """Phân loại phòng thành quá tải và nhàn rỗi"""
        overloaded_rooms = []
        underloaded_rooms = []

        for room in open_rooms:
            if room.estimated_wait_time > wait_threshold:
                overloaded_rooms.append(room)
            elif room.queue_length <= 2:  # Phòng có ít hơn hoặc bằng 2 token đang chờ
                underloaded_rooms.append(room)

        return overloaded_rooms, underloaded_rooms

    def _process_closed_rooms(self, closed_rooms, open_rooms):
        """Xử lý token trong các phòng đã đóng"""
        for closed_room in closed_rooms:
            # Tìm các token đang chờ trong phòng đã đóng
            waiting_tokens = self.search([
                ('room_id', '=', closed_room.id),
                ('state', '=', 'waiting')
            ])

            if not waiting_tokens:
                continue

            # Tìm phòng mở cùng dịch vụ
            service_id = closed_room.service_id.id
            compatible_open_rooms = [r for r in open_rooms if r.service_id.id == service_id]

            if not compatible_open_rooms:
                continue

            # Tìm phòng ít tải nhất
            target_room = min(compatible_open_rooms, key=lambda r: r.estimated_wait_time)

            # Di chuyển token
            self._move_tokens_to_room(waiting_tokens, closed_room, target_room)

    def _process_overloaded_rooms(self, overloaded_rooms, underloaded_rooms, max_patients_to_move):
        """Xử lý các phòng quá tải"""
        for o_room in overloaded_rooms:
            service = o_room.service_id

            # Tìm các phòng ít tải tương thích
            compatible_rooms = [
                r for r in underloaded_rooms
                if r.service_id.id == service.id
            ]

            if not compatible_rooms:
                continue

            # Lấy các token để di chuyển (tối đa theo cấu hình)
            tokens_to_move = self.search([
                ('room_id', '=', o_room.id),
                ('state', '=', 'waiting')
            ], order='position desc', limit=max_patients_to_move)

            if not tokens_to_move:
                continue

            # Tìm phòng ít tải nhất
            target_room = min(compatible_rooms, key=lambda r: r.estimated_wait_time)

            # Di chuyển token
            self._move_tokens_to_room(tokens_to_move, o_room, target_room)

    def _move_tokens_to_room(self, tokens, source_room, target_room):
        """Di chuyển danh sách token từ phòng nguồn sang phòng đích"""
        for token in tokens:
            old_room = token.room_id
            token.room_id = target_room.id

            # Ghi log chuyển phòng
            message = _("token_moved_from_room_to_room") % (old_room.name, target_room.name)
            token.message_post(
                body=message,
                subject=_("automatic_room_change_notification")
            )

            # Gửi thông báo cho bệnh nhân
            token._send_notifications('room_change')

        # Sắp xếp lại thứ tự trong các phòng
        self._reorder_room_queue(source_room)
        self._reorder_room_queue(target_room)

        # Thông báo cho màn hình hiển thị
        self._notify_queue_change(source_room)
        self._notify_queue_change(target_room)

    # Thêm phương thức hỗ trợ sắp xếp lại hàng đợi trong phòng
    def _reorder_room_queue(self, room):
        """Sắp xếp lại thứ tự hàng đợi trong một phòng"""
        waiting_tokens = self.search([
            ('room_id', '=', room.id),
            ('state', '=', 'waiting')
        ])

        # Sắp xếp theo mức ưu tiên (giảm dần) và thời gian tạo (tăng dần)
        sorted_tokens = waiting_tokens.sorted(key=lambda r: (-r.priority, r.create_date))

        # Cập nhật vị trí
        for index, token in enumerate(sorted_tokens):
            token.position = index + 1

    # Thêm các phương thức mới vào queue_token.py để xử lý nhóm dịch vụ
    def _process_service_group_completion(self, token, service_group, patient, package):
        """Xử lý hoàn thành dịch vụ theo nhóm"""
        # Kiểm tra xem tất cả các dịch vụ trong nhóm đã hoàn thành chưa
        group_completed = self._check_service_group_completion(service_group, patient)

        if group_completed:
            _logger.info("Nhóm dịch vụ %s đã hoàn thành. Tìm nhóm tiếp theo", service_group.name)
            # Tìm nhóm dịch vụ tiếp theo
            next_group = self._get_next_service_group(service_group, package)

            if next_group:
                _logger.info("Tìm thấy nhóm dịch vụ tiếp theo: %s", next_group.name)
                # Tạo token cho tất cả dịch vụ trong nhóm tiếp theo
                self._create_tokens_for_service_group(next_group, patient, token)
            else:
                _logger.info("Không có nhóm dịch vụ tiếp theo cho bệnh nhân %s", patient.name)
                # Thông báo hoàn thành
                return {
                    'type': IR_ACTIONS_CLIENT,
                    'tag': 'display_notification',
                    'params': {
                        'title': _(DONE_SERVICE),
                        'message': _('Đã hoàn thành tất cả các dịch vụ cho bệnh nhân %s') % patient.name,
                        'sticky': False,
                        'type': 'info',
                    }
                }

    def _check_service_group_completion(self, service_group, patient):
        """Kiểm tra xem nhóm dịch vụ đã hoàn thành chưa dựa trên chính sách hoàn thành"""
        if not service_group or not patient:
            return False

        # Kiểm tra bảng completed_service_ids đã được tạo chưa
        if not hasattr(patient, 'completed_service_ids'):
            return False

        # Lấy các dịch vụ đã hoàn thành
        completed_services = patient.completed_service_ids
        # Lấy tất cả dịch vụ trong nhóm
        group_services = service_group.service_ids

        _logger.info(
            "Kiểm tra hoàn thành nhóm %s: Dịch vụ hoàn thành: %s, Dịch vụ trong nhóm: %s",
            service_group.name,
            ', '.join(completed_services.mapped('name')),
            ', '.join(group_services.mapped('name'))
        )

        # Đếm số lượng dịch vụ đã hoàn thành trong nhóm
        completed_in_group = len(group_services & completed_services)
        total_in_group = len(group_services)

        _logger.info(
            "Đã hoàn thành %d/%d dịch vụ trong nhóm %s",
            completed_in_group, total_in_group, service_group.name
        )

        # Nếu không có dịch vụ trong nhóm
        if total_in_group == 0:
            return True

        # Kiểm tra theo chính sách hoàn thành
        if service_group.completion_policy == 'all':
            # Phải hoàn thành tất cả dịch vụ
            return completed_in_group == total_in_group
        elif service_group.completion_policy == 'any':
            # Chỉ cần hoàn thành bất kỳ dịch vụ nào
            return completed_in_group > 0

        # Mặc định là 'all'
        return completed_in_group == total_in_group

    def _get_next_service_group(self, current_group, package):
        """Lấy nhóm dịch vụ tiếp theo dựa trên nhóm hiện tại và gói dịch vụ"""
        if not current_group:
            return False

        # Tìm tất cả tuyến đường từ nhóm hiện tại
        routes = self.env[MATE_QUEUE_SERVICE_GROUP_ROUTE].search([
            ('group_from_id', '=', current_group.id)
        ], order='sequence')

        if not routes:
            _logger.info("Không tìm thấy tuyến đường nào từ nhóm %s", current_group.name)
            return False

        # Tìm tuyến đường phù hợp với gói
        if package:
            package_routes = routes.filtered(lambda r: r.package_id and r.package_id.id == package.id)
            if package_routes:
                return package_routes[0].group_to_id

        # Tìm tuyến đường không có gói cụ thể
        general_routes = routes.filtered(lambda r: not r.package_id)
        if general_routes:
            return general_routes[0].group_to_id

        # Nếu không có tuyến đường nào phù hợp, trả về nhóm đầu tiên
        return routes[0].group_to_id

    # Thêm các phương thức mới
    def _compute_next_recommended_service(self):
        """Tính toán dịch vụ nên thực hiện tiếp theo"""
        for token in self:
            # Nếu là token song song và còn token khác chưa hoàn thành
            if token.is_parallel and token.parallel_token_ids:
                # Lấy các token song song ở trạng thái draft
                draft_tokens = token.parallel_token_ids.filtered(lambda t: t.state == 'draft')

                if draft_tokens:
                    # Tìm token tối ưu nhất
                    optimal_token = self._calculate_optimal_service(draft_tokens.ids)
                    if optimal_token:
                        token.next_recommended_service_id = optimal_token.service_id
                        continue

            # Nếu không phải trường hợp song song hoặc không tìm thấy token tối ưu
            token.next_recommended_service_id = False

    def _calculate_optimal_service(self, token_ids):
        """Tính toán dịch vụ tối ưu nhất để thực hiện tiếp theo"""
        tokens = self.browse(token_ids)

        if not tokens:
            return False

        # Trọng số cho các tiêu chí
        WEIGHT_MOVEMENT = 0.4  # Trọng số cho thời gian di chuyển
        WEIGHT_WAITING = 0.35  # Trọng số cho thời gian chờ đợi tại phòng
        WEIGHT_DURATION = 0.15  # Trọng số cho thời gian thực hiện dịch vụ
        WEIGHT_MEDICAL = 0.1  # Trọng số cho ưu tiên y tế

        best_token = False
        best_score = float('inf')  # Điểm càng thấp càng tốt

        # Lấy vị trí hiện tại (phòng hiện tại)
        current_location = self.room_id if self.room_id else None

        for token in tokens:
            # 1. Điểm di chuyển (dựa trên khoảng cách giữa các phòng)
            movement_score = self._calculate_distance_score(current_location, token.room_id) if current_location else 5

            # 2. Điểm thời gian chờ
            waiting_tokens = self.search_count([
                ('room_id', '=', token.room_id.id),
                ('state', '=', 'waiting')
            ])
            capacity = token.room_id.capacity if token.room_id.capacity > 0 else 1
            waiting_score = waiting_tokens / capacity * 10  # Chuẩn hóa 0-10

            # 3. Điểm thời gian thực hiện
            duration_score = token.service_id.average_duration / 10  # Chuẩn hóa, giả sử max 100 phút

            # 4. Điểm ưu tiên y tế (càng thấp càng ưu tiên)
            medical_priority = {
                'BLOOD': 1,  # Xét nghiệm máu ưu tiên cao nhất
                'XRAY': 3,
                'ULTRA': 4,
                'DOC': 2,
                'VITAL': 5,
                'REG': 10
            }
            med_score = medical_priority.get(token.service_id.code, 5)

            # Tính tổng điểm (điểm thấp hơn = ưu tiên cao hơn)
            total_score = (
                WEIGHT_MOVEMENT * movement_score + WEIGHT_WAITING * waiting_score + WEIGHT_DURATION * duration_score + WEIGHT_MEDICAL * med_score)

            _logger.info(
                "Token %s - Di chuyển: %.2f, Chờ: %.2f, Thời gian: %.2f, Y tế: %.2f, Tổng: %.2f",
                token.name, movement_score, waiting_score, duration_score, med_score, total_score
            )

            if total_score < best_score:
                best_score = total_score
                best_token = token

        return best_token

    def _calculate_distance_score(self, from_room, to_room):
        """Tính điểm khoảng cách giữa các phòng"""
        if not from_room or not to_room:
            return 5  # Giá trị mặc định

        if from_room.id == to_room.id:
            return 0  # Cùng phòng

        # Ma trận khoảng cách thực tế giữa các phòng
        distance_matrix = {
            # Format: ('from_code', 'to_code'): distance_value
            ('REG01', 'BLOOD01'): 2,
            ('REG01', 'XRAY01'): 4,
            ('REG01', 'UTR01'): 4,
            ('REG01', 'DOC01'): 3,
            ('REG01', 'DOC02'): 3,
            ('BLOOD01', 'XRAY01'): 3,
            ('BLOOD01', 'UTR01'): 2,
            ('BLOOD01', 'DOC01'): 4,
            ('BLOOD01', 'DOC02'): 4,
            ('XRAY01', 'UTR01'): 1,
            ('XRAY01', 'DOC01'): 3,
            ('XRAY01', 'DOC02'): 3,
            ('UTR01', 'DOC01'): 3,
            ('UTR01', 'DOC02'): 3,
            ('DOC01', 'DOC02'): 1,
            ('DOC01', 'PHARM01'): 2,
            ('DOC02', 'PHARM01'): 2,
        }

        # Tìm khoảng cách trong ma trận
        key = (from_room.code, to_room.code)
        reverse_key = (to_room.code, from_room.code)

        if key in distance_matrix:
            return distance_matrix[key]
        elif reverse_key in distance_matrix:
            return distance_matrix[reverse_key]
        else:
            # Nếu không tìm thấy trực tiếp, tìm đường đi gián tiếp (có thể triển khai thuật toán đường đi ngắn nhất)
            return 5  # Mặc định

    def _create_tokens_for_service_group(self, service_group, patient, origin_token, state='draft'):
        """Tạo token cho tất cả dịch vụ trong nhóm"""
        if not service_group or not patient:
            return self.env[MATE_QUEUE_TOKEN]

        # Cập nhật nhóm dịch vụ hiện tại cho bệnh nhân
        patient.write({
            'current_service_group_id': service_group.id
        })

        # Chuẩn bị các tham số chung cho token
        token_params = self._prepare_group_token_params(patient, service_group, origin_token, state)

        # Tạo token cho từng dịch vụ trong nhóm
        created_tokens = self.env[MATE_QUEUE_TOKEN]
        for service in service_group.service_ids:
            _logger.info("Tạo token cho dịch vụ %s trong nhóm %s", service.name, service_group.name)

            # Tạo token mới với các tham số đã chuẩn bị
            token_vals = dict(token_params, service_id=service.id)
            new_token = self.create(token_vals)
            created_tokens += new_token
            _logger.info("Đã tạo token %s cho dịch vụ %s thuộc nhóm %s",
                         new_token.name, service.name, service_group.name)

        # Liên kết các token song song nếu có nhiều hơn 1 token
        if len(created_tokens) > 1:
            self._link_parallel_tokens(created_tokens)

        return created_tokens

    def _prepare_group_token_params(self, patient, service_group, origin_token, state):
        """Chuẩn bị các tham số chung cho token trong nhóm dịch vụ"""

        return {
            'patient_id': patient.id,
            'service_group_id': service_group.id,
            'priority': origin_token.priority if origin_token else 0,
            'priority_id': origin_token.priority_id.id if origin_token and origin_token.priority_id else False,
            'emergency': origin_token.emergency if origin_token else False,
            'notes': _("Tự động tạo từ nhóm dịch vụ %s") % service_group.name,
            'origin_token_id': origin_token.id if origin_token else False,
            'is_parallel': True,
            'state': state,
        }

    def _link_parallel_tokens(self, tokens):
        """Liên kết các token song song với nhau"""
        _logger.info("Liên kết %s token song song với nhau", len(tokens))
        for token in tokens:
            other_tokens = tokens - token
            token.write({
                'parallel_token_ids': [(6, 0, other_tokens.ids)],
            })

    def action_complete_service(self):
        """Hoàn tất việc phục vụ token này"""
        for token in self:
            if token.state != 'in_progress':
                raise UserError(_("can_only_complete_in_progress_tokens"))

            # Lấy thông tin cơ bản
            context = self._prepare_completion_context(token)

            # Cập nhật trạng thái token và thời gian
            self._update_token_completion_status(token)

            # Cập nhật thời gian phục vụ trung bình của dịch vụ
            self._update_service_stats(context)

            # Cập nhật dịch vụ đã hoàn thành cho bệnh nhân
            self._update_patient_completed_services(context)

            # Xử lý tiếp theo dựa trên loại token
            result = self._process_token_completion(token, context)

            # Thông báo cho màn hình phòng về sự thay đổi hàng đợi
            self._notify_queue_change(token.room_id)

            return result if result else {'type': 'ir.actions.act_window_close'}

    def _prepare_completion_context(self, token):
        """Chuẩn bị ngữ cảnh cho việc hoàn thành token"""
        return {
            'token': token,
            'current_service': token.service_id,
            'patient': token.patient_id,
            'package': token.patient_id.queue_package_id,
        }

    def _update_token_completion_status(self, token):
        """Cập nhật trạng thái hoàn thành cho token"""
        token.write({
            'state': 'completed',
            'end_time': fields.Datetime.now()
        })

    def _update_service_stats(self, context):
        """Cập nhật thống kê dịch vụ"""
        token = context['token']
        current_service = context['current_service']

        if token.actual_duration > 0:
            current_service._update_average_duration(token.actual_duration)

    def _update_patient_completed_services(self, context):
        """Cập nhật dịch vụ đã hoàn thành cho bệnh nhân"""
        patient = context['patient']
        current_service = context['current_service']

        if patient and current_service and 'completed_service_ids' in patient._fields:
            patient.write({
                'completed_service_ids': [(4, current_service.id)]
            })

    def _process_token_completion(self, token, context):
        """Xử lý logic tiếp theo sau khi hoàn thành token"""
        # Xử lý dựa trên loại token
        return self._handle_parallel_token_completion(token, context['patient'])
        # if token.is_parallel and token.service_group_id:

    def _create_next_group_service_token(self, next_service, patient, token, current_group):
        """Tạo token cho dịch vụ tiếp theo trong cùng nhóm"""
        new_token = self.create({
            'patient_id': patient.id,
            'service_id': next_service.id,
            'service_group_id': current_group.id,
            'priority': token.priority,
            'priority_id': token.priority_id.id if token.priority_id else False,
            'emergency': token.emergency,
            'notes': _("auto_created_to_complete_service_group") % current_group.name,
            'origin_token_id': token.id,
            'state': 'waiting',
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("next_service"),
                'message': _("instruct_patient_to_room") % (new_token.room_id.name, new_token.service_id.name),
                'sticky': True,
                'type': 'info',
            }
        }

    # Cập nhật hàm xử lý hoàn thành token song song
    def _handle_parallel_token_completion(self, token, patient):
        """Xử lý khi hoàn thành một token trong nhóm song song"""
        # Tìm các token song song khác chưa hoàn thành
        other_tokens = token.parallel_token_ids.filtered(lambda t: t.state == 'draft')

        if not other_tokens:
            # Kiểm tra xem tất cả token đã hoàn thành chưa
            all_completed = all(t.state == 'completed' for t in token.parallel_token_ids)

            if all_completed:
                # Đã hoàn thành tất cả token song song, tạo token cho bước tiếp theo
                _logger.info("Tất cả token song song đã hoàn thành, chuyển sang bước tiếp theo")
                return self._create_next_service_token(token, patient)

            # Có thể còn token đang thực hiện, không làm gì
            return None

        # Có token chưa hoàn thành, tìm token tối ưu tiếp theo
        next_token = self._calculate_optimal_service(other_tokens.ids)

        if next_token:
            # Kích hoạt token tiếp theo
            next_token.write({
                'state': 'waiting',
                'priority': next_token.priority + 1  # Tăng ưu tiên
            })

            # Thông báo hướng dẫn
            return {
                'type': IR_ACTIONS_CLIENT,
                'tag': 'display_notification',
                'params': {
                    'title': _(NEXT_SERVICE),
                    'message': _(TEXT_INSTRUCT) % (next_token.room_id.name, next_token.service_id.name),
                    'sticky': True,
                    'type': 'info',
                }
            }

        return None

    # Trong _handle_registration_completion, cần sửa đổi để đặt một token là active và các token khác là pending
    def _handle_registration_completion(self, token, patient):
        """Xử lý khi hoàn thành đăng ký cho bệnh nhân"""
        # Tìm nhóm dịch vụ song song
        parallel_group = self.env[MATE_HEALTH_CHECK_GROUP].search([
            ('code', '=', 'PARALLEL_TESTS')
        ], limit=1)

        if not parallel_group:
            _logger.warning("Không tìm thấy nhóm dịch vụ song song với mã PARALLEL_TESTS")
            return None

        _logger.info("Tìm thấy nhóm dịch vụ song song: %s", parallel_group.name)

        # Tạo các token ở trạng thái draft thay vì waiting
        created_tokens = self._create_tokens_for_service_group(parallel_group, patient, token, state='draft')

        if not created_tokens:
            _logger.warning("Không thể tạo token song song")
            return None

        # Tính toán token tối ưu
        optimal_token = self._calculate_optimal_service(created_tokens.ids)

        if not optimal_token:
            # Nếu không tìm thấy token tối ưu, lấy token đầu tiên
            optimal_token = created_tokens[0]

        # Kích hoạt chỉ token tối ưu, các token khác giữ ở trạng thái draft
        for t in created_tokens:
            if t.id == optimal_token.id:
                t.write({
                    'state': 'waiting',
                    'priority': t.priority + 2  # Tăng priority để đảm bảo token này được ưu tiên
                })
            else:
                t.write({
                    'state': 'draft',  # Giữ các token khác ở trạng thái draft
                    'notes': t.notes + _("wait_after_completing_test") % optimal_token.service_id.name
                })

        # Thông báo hướng dẫn
        return {
            'type': IR_ACTIONS_CLIENT,
            'tag': 'display_notification',
            'params': {
                'title': _('next_recommended_service'),
                'message': _(TEXT_INSTRUCT) % (optimal_token.room_id.name, optimal_token.service_id.name),
                'sticky': True,
                'type': 'info',
            }
        }

    def _create_next_service_token(self, completed_token, patient):
        """Tạo token cho dịch vụ tiếp theo sau khi hoàn thành nhóm dịch vụ song song"""
        # Tìm nhóm dịch vụ tiếp theo
        service_group = completed_token.service_group_id
        if not service_group:
            return None

        # Tìm tuyến đường từ nhóm hiện tại đến nhóm tiếp theo
        next_group = self._get_next_service_group(service_group, patient.queue_package_id)

        if not next_group:
            _logger.info("Không tìm thấy nhóm dịch vụ tiếp theo")
            return {
                'type': IR_ACTIONS_CLIENT,
                'tag': 'display_notification',
                'params': {
                    'title': _('completed'),
                    'message': _('Đã hoàn thành tất cả các dịch vụ cho bệnh nhân %s') % patient.name,
                    'sticky': False,
                    'type': 'info',
                }
            }

        # Tạo token cho nhóm tiếp theo
        _logger.info("Tạo token cho nhóm dịch vụ tiếp theo: %s", next_group.name)
        # Kiểm tra xem nhóm tiếp theo có phải là nhóm song song không
        if len(next_group.service_ids) > 1:
            # Tạo token song song cho nhóm tiếp theo
            new_tokens = self._create_tokens_for_service_group(next_group, patient, completed_token, state='draft')

            if new_tokens:
                # Tìm token tối ưu để thực hiện đầu tiên
                optimal_token = self._calculate_optimal_service(new_tokens.ids)

                if optimal_token:
                    # Kích hoạt token đầu tiên
                    optimal_token.write({'state': 'waiting'})

                    return {
                        'type': IR_ACTIONS_CLIENT,
                        'tag': 'display_notification',
                        'params': {
                            'title': _(NEXT_SERVICE),
                            'message': _(TEXT_INSTRUCT) % (optimal_token.room_id.name, optimal_token.service_id.name),
                            'sticky': True,
                            'type': 'info',
                        }
                    }
        else:
            # Tạo token đơn cho dịch vụ đầu tiên trong nhóm
            service = next_group.service_ids[0]

            new_token = self.create({
                'patient_id': patient.id,
                'service_id': service.id,
                'service_group_id': next_group.id,
                'priority': completed_token.priority,
                'priority_id': completed_token.priority_id.id if completed_token.priority_id else False,
                'emergency': completed_token.emergency,
                'notes': _("Tự động tạo sau khi hoàn thành nhóm dịch vụ %s") % service_group.name,
                'origin_token_id': completed_token.id,
                'state': 'waiting',
            })

            return {
                'type': IR_ACTIONS_CLIENT,
                'tag': 'display_notification',
                'params': {
                    'title': _(NEXT_SERVICE),
                    'message': _(TEXT_INSTRUCT) % (new_token.room_id.name, new_token.service_id.name),
                    'sticky': True,
                    'type': 'info',
                }
            }

        return None

    def _compute_wait_time(self):
        """Tính toán thời gian chờ ước tính dựa trên nhiều yếu tố"""
        for token in self:
            if token.state != 'waiting':
                token.estimated_wait_time = 0
                continue

            room = token.room_id
            if not room:
                token.estimated_wait_time = 0
                continue

            # Lấy tất cả token đang chờ của phòng này
            waiting_tokens = self.search([
                ('room_id', '=', room.id),
                ('state', '=', 'waiting'),
                ('position', '<', token.position)
            ])

            # Tính toán thời gian cơ bản
            avg_duration = token.service_id.average_duration
            base_wait_time = len(waiting_tokens) * avg_duration / room.capacity
            token.estimated_wait_time = base_wait_time

    def _recalculate_queue_positions(self, room_id):
        """Tính lại vị trí trong hàng đợi cho tất cả token của phòng"""
        waiting_tokens = self.search([
            ('room_id', '=', room_id),
            ('state', '=', 'waiting')
        ])

        # Sắp xếp token theo ưu tiên, loại dịch vụ và thời gian tạo
        # Ưu tiên cao hơn, emergency và health_check có quyền ưu tiên
        sorted_tokens = waiting_tokens.sorted(
            key=lambda r: (
                -r.emergency,
                -r.priority,
                r.create_date
            )
        )

        # Cập nhật vị trí
        for position, token in enumerate(sorted_tokens, 1):
            token.position = position

    def _get_next_service_in_group(self, service_group, current_service):
        """Lấy dịch vụ tiếp theo trong cùng nhóm dịch vụ"""
        if not service_group or not current_service:
            return False

        all_services = service_group.service_ids
        # Sắp xếp dịch vụ theo sequence
        sorted_services = all_services.sorted(key=lambda r: r.sequence)

        # Tìm vị trí của dịch vụ hiện tại
        current_index = -1
        for i, service in enumerate(sorted_services):
            if service.id == current_service.id:
                current_index = i
                break

        # Kiểm tra nếu có dịch vụ tiếp theo
        if current_index >= 0 and current_index < len(sorted_services) - 1:
            return sorted_services[current_index + 1]

        return False

    def _handle_vip_service_completion(self, token, patient, parallel_group):
        """Xử lý đặc biệt cho bệnh nhân VIP sau khi hoàn thành nhóm đăng ký"""
        _logger.info("Bệnh nhân VIP %s đã hoàn thành nhóm đăng ký, tạo token song song", patient.name)

        # Cập nhật nhóm dịch vụ hiện tại cho bệnh nhân
        patient.write({
            'current_service_group_id': parallel_group.id
        })

        # Tạo các token ở trạng thái draft
        created_tokens = self._create_tokens_for_service_group(parallel_group, patient, token, state='draft')

        if not created_tokens:
            _logger.warning("Không thể tạo token song song")
            return None

        # Tính toán token tối ưu
        optimal_token = self._calculate_optimal_service(created_tokens.ids)

        if not optimal_token:
            # Nếu không tìm thấy token tối ưu, lấy token đầu tiên
            optimal_token = created_tokens[0]

        # Kích hoạt chỉ token tối ưu, các token khác giữ ở trạng thái draft
        for t in created_tokens:
            if t.id == optimal_token.id:
                t.write({
                    'state': 'waiting',
                    'priority': t.priority + 2  # Tăng priority để đảm bảo token này được ưu tiên
                })
            else:
                t.write({
                    'state': 'draft',  # Giữ các token khác ở trạng thái draft
                    'notes': t.notes + _("wait_after_completing_test") % optimal_token.service_id.name
                })

        # Thông báo hướng dẫn
        return {
            'type': IR_ACTIONS_CLIENT,
            'tag': 'display_notification',
            'params': {
                'title': _('next_recommended_service'),
                'message': _(TEXT_INSTRUCT) % (optimal_token.room_id.name, optimal_token.service_id.name),
                'sticky': True,
                'type': 'info',
            }
        }
