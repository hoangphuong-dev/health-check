# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)

MATE_HEALTH_CHECK_PACKAGE = 'mate.health.check.package'
PRODUCT_PRODUCT = 'product.product'
HR_DEPARTMENT = 'hr.department'
MATE_HEALTH_CHECK_PACKAGE_LINE = 'mate.health.check.package.line'
PHYSICIAN_SPECIALTY = 'physician.specialty'
MATE_HEALTH_CHECK_GROUP = 'mate.health.check.group'
MATE_HEALTH_CHECK_PACKAGE_GROUP_ORDER = 'mate.health.check.package.group.order'
MATE_HEALTH_CHECK_CUSTOMER_TYPE = 'mate.health.check.customer.type'


class MateHealthCheckPackage(models.Model):
    _name = MATE_HEALTH_CHECK_PACKAGE
    _description = 'Health Check Package'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    package_line_ids = fields.One2many(
        MATE_HEALTH_CHECK_PACKAGE_LINE,
        'package_id',
        string='Services',
        help="The services included in this health check package."
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

    @api.model
    def action_create_package(self):
        """Create a new package line for the health check package."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Package'),
            'res_model': MATE_HEALTH_CHECK_PACKAGE,
            'views': [[False, "form"]],
            'target': 'new',
            'context': {
                'dialog_size': 'extra-large',
                'reload': True,
            }
        }

    def action_create_group_sequence(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Group Sequence',
            'res_model': 'create.group.sequence.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('mate_health_check.view_create_group_sequence_wizard_form').id,
            'target': 'new',
            'context': {
                'default_package_id': self.id,
            }
        }


class MateHealthCheckPackageLine(models.Model):
    _name = MATE_HEALTH_CHECK_PACKAGE_LINE
    _description = 'Health Check Package Line'

    package_id = fields.Many2one(
        MATE_HEALTH_CHECK_PACKAGE,
        string='Packages',
        help="The health check packages that include this service."
    )
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


class MateHealthCheckService(models.Model):
    _name = PRODUCT_PRODUCT
    _description = 'Health Check Service'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description', help="Description of the health check service.")


class MateHealthCheckGroup(models.Model):
    _name = MATE_HEALTH_CHECK_GROUP
    _description = 'Health Check Group'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description', help="Description of the health check group.")


class MateHealthCheckCustomerType(models.Model):
    _name = MATE_HEALTH_CHECK_CUSTOMER_TYPE
    _description = 'Health Check Customer Type'

    name = fields.Char(string='Name', required=True)


class MatePackageGroupOrder(models.Model):
    """Model này để quản lý thứ tự nhóm dịch vụ trong gói kiểm tra sức khỏe."""
    _name = MATE_HEALTH_CHECK_PACKAGE_GROUP_ORDER
    _description = 'Health Check Package Group Order'

    name = fields.Char(string='Name')
    sequence = fields.Integer(string='Sequence', required=True)
    group_id = fields.Many2one(
        MATE_HEALTH_CHECK_GROUP,
        string='Group',
        help='The group associated with this sequence.'
    )
    package_id = fields.Many2one(
        MATE_HEALTH_CHECK_PACKAGE,
        string='Package',
        help='The package associated with this sequence.'
    )
