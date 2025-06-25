# -*- coding: utf-8 -*-

from odoo import fields, models

RES_PARTNER = 'res.partner'
HIS_PATIENT = 'his.patient'


class MateHealthCheckPatient(models.Model):
    _name = HIS_PATIENT
    _description = 'Health Check Patient'
    _inherits = {
        RES_PARTNER: 'partner_id',
    }

    partner_id = fields.Many2one(RES_PARTNER, required=True, ondelete='restrict', auto_join=True, string='Related Partner', help='Partner-related data of the Patient')
    active = fields.Boolean(string="Active", default=True)

    def action_open_smart_queue_view(self):
        """Mở view từ module mate_smart_queue"""
        try:
            # Thử tìm action từ module con
            action = self.env.ref('mate_smart_queue.action_patient_list_main')
            return action.read()[0]
        except ValueError:
            # Nếu không tìm thấy (module con chưa cài), dùng view mặc định
            return {
                'type': 'ir.actions.act_window',
                'name': 'Patient List',
                'res_model': HIS_PATIENT,
                'view_mode': 'list,form',
                'target': 'current',
            }

    def action_open_queue_list_view(self):
        """Mở view từ module mate_smart_queue"""
        try:
            # Thử tìm action từ module con
            action = self.env.ref('mate_smart_queue.action_queue_token')
            return action.read()[0]
        except ValueError:
            # Nếu không tìm thấy (module con chưa cài), dùng view mặc định
            return {
                'type': 'ir.actions.act_window',
                'name': 'Queue List',
                'res_model': HIS_PATIENT,
                'view_mode': 'list,form',
                'target': 'current',
            }
