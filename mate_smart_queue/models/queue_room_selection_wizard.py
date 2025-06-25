# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

HIS_PATIENT = 'his.patient'
MATE_QUEUE_TOKEN = "mate.queue.token"
HR_DEPARTMENT = 'hr.department'
PRODUCT_PRODUCT = 'product.product'

MATE_QUEUE_ROOM_SELECTION_WIRARD = 'mate.queue.room.selection.wizard'


class QueueRoomSelectionWizard(models.TransientModel):
    _name = MATE_QUEUE_ROOM_SELECTION_WIRARD
    _description = _('Queue Room Selection Wizard')

    patient_id = fields.Many2one(HIS_PATIENT, string='Patient', required=True, readonly=True)
    service_id = fields.Many2one(PRODUCT_PRODUCT, string='Service', required=True, readonly=True)
    current_room_id = fields.Many2one(HR_DEPARTMENT, string='Current Room', readonly=True)
    selected_room_id = fields.Many2one(HR_DEPARTMENT, string='Selected Room', required=True,
                                       domain="[('service_id', '=', service_id), ('state', '=', 'open')]")

    coordination_type = fields.Selection([
        ('room_change', 'Thay đổi phòng cùng dịch vụ'),
        ('service_change', 'Thay đổi dịch vụ')
    ], default='room_change', string='Loại điều phối')

    @api.model
    def default_get(self, fields_list):
        """Thiết lập giá trị mặc định từ context"""
        defaults = super().default_get(fields_list)

        # Lấy giá trị từ context
        if 'default_patient_id' in self.env.context:
            defaults['patient_id'] = self.env.context['default_patient_id']

        if 'default_service_id' in self.env.context:
            defaults['service_id'] = self.env.context['default_service_id']

        if 'default_current_room_id' in self.env.context:
            defaults['current_room_id'] = self.env.context['default_current_room_id']

        if 'default_coordination_type' in self.env.context:
            defaults['coordination_type'] = self.env.context['default_coordination_type']

        return defaults

    @api.constrains('selected_room_id', 'current_room_id')
    def _check_selected_room(self):
        """Xác thực phòng được chọn"""
        for wizard in self:
            if wizard.selected_room_id and wizard.current_room_id:
                if wizard.selected_room_id.id == wizard.current_room_id.id:
                    raise UserError(_('Phòng được chọn giống với phòng hiện tại'))

    def action_coordinate(self):
        """Thực hiện điều phối phòng"""
        self.ensure_one()

        if not self.selected_room_id:
            raise UserError(_('Vui lòng chọn phòng để chuyển đến'))

        # Xác thực phòng vẫn còn mở
        if self.selected_room_id.state != 'open':
            raise UserError(_('Phòng được chọn không khả dụng'))

        # Chọn phòng và điều phối
        if self.coordination_type == 'service_change':
            result = self.patient_id.with_context(
                target_room_id=self.selected_room_id.id,
                target_service_id=self.service_id.id,
            ).action_coordinate_service_room()
        else:
            # Thay đổi phòng thông thường (cho dịch vụ hiện tại)
            result = self.patient_id.with_context(
                target_room_id=self.selected_room_id.id,
                coordination_type='room_change'
            ).action_coordinate_room()

        return result
