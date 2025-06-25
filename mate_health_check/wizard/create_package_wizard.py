from odoo import models, fields, api

MATE_HEALTH_CHECK_PACKAGE = 'mate.health.check.package'
PRODUCT_PRODUCT = 'product.product'
MATE_HEALTH_CHECK_GROUP = 'mate.health.check.group'
HR_DEPARTMENT = 'hr.department'
PHYSICIAN_SPECIALTY = 'physician.specialty'
MATE_HEALTH_CHECK_PACKAGE_LINE = 'mate.health.check.package.line'
MATE_HEALTH_CHECK_CUSTOMER_TYPE = 'mate.health.check.customer.type'


class CreatePackageWizard(models.TransientModel):
    _name = 'create.package.wizard'
    _description = 'Create Package Wizard'

    package_id = fields.Many2one(
        MATE_HEALTH_CHECK_PACKAGE, string='Package', required=True)
    package_line_ids = fields.One2many(
        'create.package.line.wizard',
        'package_wizard_id',
        string='Package Lines',
        help="List of package lines under the selected package."
    )
    gender = fields.Selection(
        [('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
        string='Gender',
        help="The gender associated with this health check package."
    )
    customer_type = fields.Many2one(
        MATE_HEALTH_CHECK_CUSTOMER_TYPE,
        string='Customer Type',
        help="The type of customer for this health check package."
    )

    def action_save_package(self):
        self.env[MATE_HEALTH_CHECK_PACKAGE_LINE].search([('package_id', '=', self.package_id.id)]).unlink()
        self.package_id.write({
            'gender': self.gender,
            'customer_type': self.customer_type.id,
        })
        for line in self.package_line_ids:
            self.env[MATE_HEALTH_CHECK_PACKAGE_LINE].create({
                'package_id': self.package_id.id,
                'department_id': line.department_id.id,
                'service_id': line.service_id.id,
                'specialty_id': line.specialty_id.id,
                'group_id': line.group_id.id,
            })
        return self.env.ref('mate_health_check.mate_health_check_package_action').read()[0]

    @api.model
    def action_create_package(self):
        action = self.env.ref('mate_health_check.action_mate_create_package_wizard').read()[0]
        action['context'] = {
            'dialog_size': 'extra-large',
        }
        return action

    @api.onchange('package_id')
    def _onchange_package_id(self):
        self.package_line_ids = [(5, 0, 0)]
        if self.package_id:
            package_line = self.env[MATE_HEALTH_CHECK_PACKAGE_LINE].search([('package_id', '=', self.package_id.id)])
            self.gender = self.package_id.gender
            self.customer_type = self.package_id.customer_type.id
            self.package_line_ids = [
                (
                    0,
                    0,
                    {
                        'department_id': line.department_id.id,
                        'service_id': line.service_id.id,
                        'specialty_id': line.specialty_id.id,
                        'group_id': line.group_id.id
                    }
                ) for line in package_line
            ]


class CreatePackageLineWizard(models.TransientModel):
    _name = 'create.package.line.wizard'
    _description = 'Create Package Line Wizard'

    package_wizard_id = fields.Many2one(
        'create.package.wizard', string='Package', required=True)
    department_id = fields.Many2one(
        HR_DEPARTMENT,
        string='Department',
        help="The department where this health check service is provided."
    )
    service_id = fields.Many2one(
        PRODUCT_PRODUCT,
        string='Service',
        help="The health check service provided in this package line."
    )
    specialty_id = fields.Many2one(
        PHYSICIAN_SPECIALTY,
        string='Specialty',
        help="The specialty associated with this health check service."
    )
    group_id = fields.Many2one(
        MATE_HEALTH_CHECK_GROUP,
        string='Group',
        help="The group associated with this health check service."
    )
