from odoo import fields, models


class ResourceCalendar(models.Model):
    _description = "Working Schedule"
    _inherit = "resource.calendar"

    category = fields.Selection([('doctor', 'Doctor'), ('nurse', 'Nurse')], string='Category')
    department_id = fields.Many2one('hr.department', ondelete='restrict', domain=[('patient_department', '=', True)], string='Department', help="Department for which the schedule is applicable.")
    physician_ids = fields.Many2many('mate_hms.physician', 'physician_resource_rel', 'physician_id', 'resource_id', 'Physicians')
