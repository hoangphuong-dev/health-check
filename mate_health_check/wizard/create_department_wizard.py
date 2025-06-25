# -*- coding: utf-8 -*-
from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)

HR_DEPARTMENT = 'hr.department'


class MateCreateDepartmentWizard(models.TransientModel):
    _name = 'mate.create.department.wizard'

    specialty_id = fields.Many2one(
        'physician.specialty',
        string='Specialty',
        required=True,
        help="Select the specialty associated with this department."
    )
    department_ids = fields.One2many(
        'mate.create.department.line.wizard',
        'department_wizard_id',
        string='Departments',
        help="List of departments under the selected specialty."
    )

    def save_department(self):
        departments = self.env[HR_DEPARTMENT].search([
            ('specialty_id', '=', self.specialty_id.id)
        ])
        for dept in self.department_ids:
            if dept.code not in departments.mapped('code'):
                self.env[HR_DEPARTMENT].create({
                    'name': dept.name,
                    'location': dept.location,
                    'capacity': dept.capacity,
                    'specialty_id': self.specialty_id.id,
                    'code': dept.code,
                })
                continue
            if dept.code in departments.mapped('code'):
                existing_dept = departments.filtered(lambda d, dept=dept: d.code == dept.code)
                existing_dept.write({
                    'name': dept.name,
                    'location': dept.location,
                    'capacity': dept.capacity,
                    'specialty_id': self.specialty_id.id,
                })
        departments.filtered(lambda d: d.code not in [dept.code for dept in self.department_ids]).unlink()
        return self.env.ref('mate_health_check.mate_health_check_department_action').read()[0]

    @api.model
    def action_create_department(self):
        """Create a new department with the given parameters."""
        action = self.env.ref('mate_health_check.action_mate_create_department_wizard').read()[0]
        action['context'] = {
            'dialog_size': 'extra-large',
        }
        return action

    @api.onchange('specialty_id')
    def _onchange_specialty_id(self):
        """Reset the department lines when the specialty changes."""
        self.department_ids = [(5, 0, 0)]
        if self.specialty_id:
            department = self.env[HR_DEPARTMENT].search([
                ('specialty_id', '=', self.specialty_id.id)
            ])
            self.department_ids = [(0, 0, {'name': dept.name, 'location': dept.location, 'capacity': dept.capacity, 'code': dept.code}) for dept in department]


class MateCreateDepartmentLineWizard(models.TransientModel):
    _name = 'mate.create.department.line.wizard'

    department_wizard_id = fields.Many2one(
        'mate.create.department.wizard',
        string='Department',
        help="The department associated with this line."
    )
    name = fields.Char(
        string='Department Name',
        required=True,
        help="The name of the department."
    )
    location = fields.Text(
        string='Location',
        help="The physical location of the department."
    )
    capacity = fields.Integer(
        string='Capacity',
        help="The maximum number of patients that can be accommodated in this department."
    )
    code = fields.Char(
        string='Code',
        required=True,
        help="A unique code for the department, used for identification."
    )
