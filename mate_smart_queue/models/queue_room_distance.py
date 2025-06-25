from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

HR_DEPARTMENT = 'hr.department'


class QueueRoomDistance(models.Model):
    _name = 'queue.room.distance'
    _description = 'Khoảng Cách Giữa Các Phòng'
    _rec_name = 'display_name'

    room_from_id = fields.Many2one(HR_DEPARTMENT, string=_('From Room'), required=True, ondelete='cascade')
    room_to_id = fields.Many2one(HR_DEPARTMENT, string=_('To Room'), required=True, ondelete='cascade')
    distance = fields.Float(string=_('Distance (unit)'), required=True, default=1.0,
                            help=_("Relative distance between rooms, unit is optional (can be meters, steps, etc.)"))
    travel_time = fields.Float(string=_('Travel Time (minutes)'),
                               help=_("Estimated travel time between two rooms"))
    display_name = fields.Char(string=_('Display Name'), compute='_compute_display_name', store=True)

    @api.depends('room_from_id', 'room_to_id', 'distance')
    def _compute_display_name(self):
        for record in self:
            if record.room_from_id and record.room_to_id:
                record.display_name = f"{record.room_from_id.name} → {record.room_to_id.name} ({record.distance})"
            else:
                record.display_name = _("New")

    @api.constrains('room_from_id', 'room_to_id')
    def _check_different_rooms(self):
        for record in self:
            if record.room_from_id.id == record.room_to_id.id:
                raise ValidationError(_("Source room and destination room must be different!"))

            # Kiểm tra trùng lặp
            existing = self.search([
                ('room_from_id', '=', record.room_from_id.id),
                ('room_to_id', '=', record.room_to_id.id),
                ('id', '!=', record.id)
            ])
            if existing:
                raise ValidationError(_("Distance between room %s and room %s already exists!")
                                      % (record.room_from_id.name, record.room_to_id.name))

    @api.model
    def get_distance(self, from_room_id, to_room_id):
        """Lấy khoảng cách giữa hai phòng, bao gồm cả chiều ngược lại"""
        if from_room_id == to_room_id:
            return 0.0

        # Tìm bản ghi trực tiếp
        distance_record = self.search([
            '|',
            '&', ('room_from_id', '=', from_room_id), ('room_to_id', '=', to_room_id),
            '&', ('room_from_id', '=', to_room_id), ('room_to_id', '=', from_room_id)
        ], limit=1)

        if distance_record:
            return distance_record.distance
        else:
            # Giá trị mặc định nếu không tìm thấy
            return 5.0
