from odoo import models, fields, api, _
import logging
from odoo.exceptions import ValidationError
import re

_logger = logging.getLogger(__name__)

RES_CONFIG_SETTINGS = 'res.config.settings'
MATE_HMS_APPOINTMENT = 'mate_hms.appointment'
MATE_HMS_SUBSCRIPTIONS = 'mate_hms.subscriptions'
MATE_HMS_CONSUMABLE_LINE = 'mate_hms.consumable.line'
MATE_HMS_APPOINTMENT_PACKAGE_USAGE = 'mate_hms.appointment.package.usage'
IR_CONFIG_PARAMETER = 'ir.config_parameter'


class MateAppointment(models.Model):
    _inherit = [MATE_HMS_APPOINTMENT]

    package_usage_ids = fields.One2many(
        MATE_HMS_APPOINTMENT_PACKAGE_USAGE,
        'appointment_id',
        string='Package Usage',
    )
    visit_number = fields.Char(string='Visit Number')
    subscriptions_ids = fields.One2many(
        MATE_HMS_SUBSCRIPTIONS, 'patient_id', string='Subscriptions', related='patient_id.subscriptions_ids'
    )
    attachment_id = fields.Many2one('ir.attachment', string='Attachment')

    custom_subscriptions_domain = fields.Char(string='Custom subscriptions domain', default='[]')

    @api.constrains('visit_number')
    def _check_visit_number_format(self):
        for record in self:
            if record.visit_number:
                pattern = r'^TN\d{6}\.\d{7}$'
                if not re.match(pattern, record.visit_number):
                    raise ValidationError(
                        _('Visit Number must follow the format: TNxxxxxx.xxxxxxx')
                    )

    @api.onchange('patient_id')
    def _onchange_patient_id(self):
        if self.patient_id:
            # Lấy các gói package mà patient_id đã đăng ký từ subscriptions_ids
            subscriptions_ids = self.patient_id.subscriptions_ids.filtered(lambda x: x._check_validate()).ids
            self.custom_subscriptions_domain = [('id', 'in', subscriptions_ids)]
        else:
            self.custom_subscriptions_domain = []

    @api.depends("state")
    def _compute_onchange_status(self):
        if self.env[IR_CONFIG_PARAMETER].get_param("mate_hms_subscriptions.service_generation_option") == 'appointment':
            if self.state == self.env[IR_CONFIG_PARAMETER].get_param("mate_hms_subscriptions.appointment_status") :
                package_usage = next(
                    (
                        package
                        for subscription in self.subscriptions_ids
                        for package in subscription.package_ids
                        if package.product_id.id == self.product_id.id and package.remaining_qty > 0
                    ),
                    None
                )
                self.env[MATE_HMS_CONSUMABLE_LINE].create({
                    'product_id': self.product_id.id,
                    'qty': 1,
                    'price_unit': self.product_id.list_price,
                    'patient_id': self.patient_id.id,
                    'physician_id': self.physician_id.id,
                    'appointment_id': self.id,
                    'subscription_id': package_usage.subscription_id.id if package_usage else False,
                })
            return True
        return False

    service_generation = fields.Boolean(compute=_compute_onchange_status, store=True)

    def action_reopen(self):
        super(MateAppointment, self).action_reopen()
        for package_usage in self.package_usage_ids:
            package_usage.subscription_line_id.remaining_qty += package_usage.usage
        self.package_usage_ids.unlink()

        self.consumable_line_ids.filtered(lambda x: x.qty < 0 and not x.split_from_package).unlink()

        split_from_package = self.consumable_line_ids.filtered(lambda x: x.split_from_package)
        consumables_by_product = {}
        for consumable in split_from_package:
            if consumable.product_id.id not in consumables_by_product:
                consumables_by_product[consumable.product_id.id] = []
            consumables_by_product[consumable.product_id.id].append(consumable)

        # Process each product group
        for product_id, consumables in consumables_by_product.items():
            total_qty = sum(consumable.qty for consumable in consumables if consumable.split_from_package and consumable.qty > 0)
            self.env[MATE_HMS_CONSUMABLE_LINE].create({
                'product_id': product_id,
                'qty': total_qty,
                'price_unit': consumables[0].product_id.list_price,
                'patient_id': self.patient_id.id,
                'physician_id': self.physician_id.id,
                'appointment_id': self.id,
                'subscription_id': consumables[0].subscription_id.id if consumables[0].subscription_id else False,
            })
        split_from_package.unlink()
        return True

    def consultation_done(self):
        super(MateAppointment, self).consultation_done()

        list_new_consumable = []
        list_new_package_usage = []

        for consumable in self.consumable_line_ids:
            subscription_line = self.get_subscription_line(consumable.subscription_id, consumable.product_id.id)
            if not subscription_line:
                consumable.package_group_type = 'out_package'
                continue

            if subscription_line.remaining_qty == 0:
                consumable.package_group_type = 'over_package'
                continue

            qty_diff = subscription_line.remaining_qty - consumable.qty

            if qty_diff >= 0:
                subscription_line.remaining_qty = qty_diff
                consumable.package_group_type = 'in_package'
                list_new_package_usage.append({
                    'appointment_id': self.id,
                    'subscription_line_id': subscription_line.id,
                    'product_id': consumable.product_id.id,
                    'usage': consumable.qty,
                    'qty': subscription_line.qty,
                    'remaining_qty': qty_diff,
                })
            else:
                used_qty = subscription_line.remaining_qty
                remaining_usage = abs(qty_diff)
                list_new_consumable.extend([
                    self._prepare_consumable_dict(subscription_line, consumable, used_qty, False, True, group_type='in_package'),
                    self._prepare_consumable_dict(subscription_line, consumable, remaining_usage, False, True, True, group_type='over_package')
                ])
                list_new_package_usage.append({
                    'appointment_id': self.id,
                    'subscription_line_id': subscription_line.id,
                    'product_id': consumable.product_id.id,
                    'usage': used_qty,
                    'qty': subscription_line.qty,
                    'remaining_qty': 0,
                })
                consumable.unlink()
                subscription_line.remaining_qty = 0

        if list_new_consumable:
            self.env[MATE_HMS_CONSUMABLE_LINE].create(list_new_consumable)
        if list_new_package_usage:
            self.env[MATE_HMS_APPOINTMENT_PACKAGE_USAGE].create(list_new_package_usage)
        self.update_amount_total()
        return True

    @api.model
    def action_create_appointment_import_services_excel(self):
        action = self.env.ref('mate_hms.action_mate_hms_handle_consumed_services').read()[0]
        action['context'] = {
            "create_appointment": True,
        }
        return action

    def _prepare_consumable_dict(self, sub_line, consumable, qty, use_package_name=False, split=False, override_product=False, group_type=False):
        name = f"{sub_line.name} - {sub_line.package_id.name}" if use_package_name else sub_line.name
        sub_line_id = consumable.subscription_id.id if consumable.subscription_id else None
        return {
            'name': name,
            'product_id': sub_line.product_id.id if override_product else consumable.product_id.id,
            'qty': qty,
            'patient_id': self.patient_id.id,
            'appointment_id': self.id,
            'physician_id': self.physician_id.id,
            'price_unit': consumable.product_id.list_price,
            'subscription_id': sub_line_id,
            'split_from_package': split,
            'package_group_type': group_type if sub_line_id else 'out_package',
        }

    def get_subscription_line(self, subscription, product_id):
        """
        Lấy dòng đăng ký tương ứng với sản phẩm và đăng ký.
        :param subscription: Đối tượng đăng ký.
        :param product_id: ID của sản phẩm.
        :return: Dòng đăng ký tương ứng hoặc None nếu không tìm thấy.
        """
        for line in subscription.package_ids:
            if line.product_id.id == product_id:
                return line
        return None

    def get_appointment_product_data(self):
        setting = self.env[RES_CONFIG_SETTINGS].sudo().search([('company_id', '=', self.env.company.id)], limit=1)
        return self.acs_appointment_inv_product_data(with_product=setting.service_generation_option == 'invoice')

    def calulate_package_quantity(self, package_lines, quantities):
        """
        Giảm số lượng gói dịch vụ trong danh sách package_lines dựa trên số lượng đã sử dụng.
        :param package_lines: Danh sách các dòng gói dịch vụ.
        :param quantities: Số lượng đã sử dụng.
        """
        package_usage = []
        for package_line in package_lines:
            if package_line.remaining_qty <= 0:
                continue

            if quantities <= package_line.remaining_qty:
                package_line.remaining_qty -= quantities
                package_usage.append({
                    'appointment_id': self.id,
                    'subscription_line_id': package_line.id,
                    'product_id': package_line.product_id.id,
                    'usage': quantities,
                    'qty': package_line.qty,
                    'remaining_qty': package_line.remaining_qty,
                })
                break
            else:
                quantities -= package_line.remaining_qty
                package_usage.append({
                    'appointment_id': self.id,
                    'subscription_line_id': package_line.id,
                    'product_id': package_line.product_id.id,
                    'usage': package_line.remaining_qty,
                    'qty': package_line.qty,
                    'remaining_qty': package_line.remaining_qty,
                })
                package_line.remaining_qty = 0
        if len(package_usage) > 0:
            self.env[MATE_HMS_APPOINTMENT_PACKAGE_USAGE].create(package_usage)
        return quantities


class MateConsumableLine(models.Model):
    _inherit = MATE_HMS_CONSUMABLE_LINE

    subscription_id = fields.Many2one(
        MATE_HMS_SUBSCRIPTIONS,
        string='Subscription Line',
        ondelete='cascade',
    )

    custom_subscriptions_domain = fields.Char(string='Custom subscriptions domain', related='appointment_id.custom_subscriptions_domain')

    package_group_type = fields.Selection(
        [('in_package', 'In package'), ('out_package', 'Out of package'), ('over_package', 'Over the package')],
    )

    split_from_package = fields.Boolean(String='Split from Package', default=False)


class MateConsumedServicesLine(models.TransientModel):
    _inherit = 'mate_hms.consumed.services.line'

    subscription_id = fields.Many2one(
        MATE_HMS_SUBSCRIPTIONS,
        string='Subscription Line',
        ondelete='cascade',
    )
