# models/queue_coordination_log.py
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

HIS_PATIENT = 'his.patient'
MATE_QUEUE_TOKEN = "mate.queue.token"
HR_DEPARTMENT = 'hr.department'
PRODUCT_PRODUCT = 'product.product'
MATE_QUEUE_COORDINATION_LOG = 'mate.queue.coordination.log'


class QueueCoordinationLog(models.Model):
    _name = MATE_QUEUE_COORDINATION_LOG
    _description = _('Queue Coordination Log')  # Log Điều Phối Hàng Đợi
    _order = 'create_date desc'
    _rec_name = 'coordination_summary'

    name = fields.Char(string=_('Log Code'), readonly=True, default=lambda self: _('New'))
    coordination_summary = fields.Char(string=_('Summary'), compute='_compute_coordination_summary', store=True)

    # Patient and user info
    patient_id = fields.Many2one(HIS_PATIENT, string=_('Patient'), required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string=_('Performer'), required=True, default=lambda self: self.env.user)

    # Coordination type
    coordination_type = fields.Selection([
        ('service_change', _('Service Change')),
        ('room_change', _('Room Change')),
        ('position_change', _('Position Change in Room'))
    ], string=_('Coordination Type'), required=True)

    # Service information
    from_service_id = fields.Many2one(PRODUCT_PRODUCT, string=_('From Service'))
    to_service_id = fields.Many2one(PRODUCT_PRODUCT, string=_('To Service'))

    patient_pid = fields.Char(
        string='PID',
        related='patient_id.patient_id_number',
        readonly=True,
        store=True
    )

    # Room information
    from_room_id = fields.Many2one(HR_DEPARTMENT, string=_('From Room'))
    to_room_id = fields.Many2one(HR_DEPARTMENT, string=_('To Room'))

    # Queue information
    old_position = fields.Integer(string=_('Old Position'))
    new_position = fields.Integer(string=_('New Position'))

    # Token information
    old_token_id = fields.Many2one(MATE_QUEUE_TOKEN, string=_('Old Token'), ondelete='set null')
    new_token_id = fields.Many2one(MATE_QUEUE_TOKEN, string=_('New Token'), ondelete='set null')

    # Additional info
    priority = fields.Integer(string=_('Priority Level'))
    coordination_reason = fields.Text(string=_('Coordination Reason'))
    coordination_date = fields.Datetime(string=_('Coordination Time'), default=fields.Datetime.now)

    service_display = fields.Char(
        string='Dịch vụ',
        compute='_compute_service_display',
        store=True
    )
    room_display = fields.Char(
        string='Phòng',
        compute='_compute_room_display',
        store=True
    )
    position_display = fields.Char(
        string='Thứ tự khám',
        compute='_compute_position_display',
        store=True
    )

    @api.depends('from_service_id', 'to_service_id')
    def _compute_service_display(self):
        for log in self:
            if log.from_service_id and log.to_service_id:
                log.service_display = f"{log.from_service_id.name} → {log.to_service_id.name}"
            elif log.from_service_id:
                log.service_display = log.from_service_id.name
            elif log.to_service_id:
                log.service_display = log.to_service_id.name
            else:
                log.service_display = ""

    @api.depends('from_room_id', 'to_room_id')
    def _compute_room_display(self):
        for log in self:
            if log.from_room_id and log.to_room_id:
                log.room_display = f"{log.from_room_id.name} → {log.to_room_id.name}"
            elif log.from_room_id:
                log.room_display = log.from_room_id.name
            elif log.to_room_id:
                log.room_display = log.to_room_id.name
            else:
                log.room_display = ""

    @api.depends('old_position', 'new_position')
    def _compute_position_display(self):
        for log in self:
            if log.old_position and log.new_position:
                log.position_display = f"{log.old_position} → {log.new_position}"
            elif log.old_position:
                log.position_display = str(log.old_position)
            elif log.new_position:
                log.position_display = str(log.new_position)
            else:
                log.position_display = ""

    @api.depends('patient_id', 'from_service_id', 'to_service_id', 'coordination_type')
    def _compute_coordination_summary(self):
        for log in self:
            if log.coordination_type == 'service_change':
                if log.from_service_id and log.to_service_id:
                    log.coordination_summary = f"{log.patient_id.name}: {log.from_service_id.name} → {log.to_service_id.name}"
                else:
                    log.coordination_summary = f"{log.patient_id.name}: Service Change"
            elif log.coordination_type == 'room_change':
                if log.from_room_id and log.to_room_id:
                    log.coordination_summary = f"{log.patient_id.name}: {log.from_room_id.name} → {log.to_room_id.name}"
                else:
                    log.coordination_summary = f"{log.patient_id.name}: Room Change"
            else:
                log.coordination_summary = f"{log.patient_id.name}: Position Change"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('queue.coordination.log') or _('New')
        return super(QueueCoordinationLog, self).create(vals_list)
