# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import secrets
import string
import logging
from datetime import datetime
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


MATE_HMS_SUBSCRIPTIONS = 'mate_hms.subscriptions'
MATE_HMS_SUBSCRIPTIONS_LINE = 'mate_hms.subscription.line'
MATE_HMS_PACKAGE_USAGE = 'mate_hms.appointment.package.usage'
IR_ACTIONS_WINDOW = 'ir.actions.act_window'
MATE_HMS_SUBSCRIPTIONS_UPDATE_HISTORY = 'mate_hms.subscription.update.history'
MATE_HMS_SUBSCRIPTIONS_UPDATE_HISTORY_LINE = 'mate_hms.subscription.update.history.line'
MATE_HMS_PACKAGE = 'mate_hms.package'


class MateSubscriptions(models.Model):
    """
    Lớp MateSubscriptions đại diện cho các đăng ký gói dịch vụ và vật tư y tế của bệnh nhân trong hệ thống.
    Attributes:
        _name (str): Tên kỹ thuật của mô hình là "mate_hms.subscriptions".
        _description (str): Mô tả của mô hình là "Subscriptions".
        patient_id (fields.Many2one): Trường liên kết đến bệnh nhân, bắt buộc phải có.
        package_id (fields.Many2one): Trường liên kết đến gói dịch vụ, bắt buộc phải có.
        start_date (fields.Datetime): Ngày bắt đầu của đăng ký, bắt buộc phải có.
        end_date (fields.Datetime): Ngày kết thúc của đăng ký, bắt buộc phải có.
        _sql_constraints (list): Ràng buộc SQL để đảm bảo mỗi bệnh nhân chỉ có một bản ghi cho mỗi gói dịch vụ.
    """
    _name = "mate_hms.subscriptions"
    _description = 'Subscriptions'
    _rec_name = 'name'

    def _default_subscription_code(self, length=5):
        random_code = ''.join(secrets.choice(string.digits) for _ in range(length))
        return 'SUB' + random_code

    active = fields.Boolean(default=True)
    name = fields.Char(related='package_id.name', store=True, readonly=True)
    code = fields.Char(string='Code', readonly=True, default=_default_subscription_code)
    patient_id = fields.Many2one('mate_hms.patient', string='Patient', required=True)
    package_id = fields.Many2one(MATE_HMS_PACKAGE, string='Package', required=True, domain="[('end_date', '>=', context_today())]")
    start_date = fields.Date("Start Date", required=True)
    end_date = fields.Date("End Date", required=True)
    history_count = fields.Integer(string='History Count', compute='_compute_history_count', store=True)
    package_ids = fields.One2many(MATE_HMS_SUBSCRIPTIONS_LINE, 'subscription_id', string='Patient Packages')
    subscriptions_line_ids = fields.One2many(MATE_HMS_SUBSCRIPTIONS_LINE, 'subscription_id', string='Subscription Lines')
    subscriptions_usage_history_ids = fields.One2many(MATE_HMS_SUBSCRIPTIONS_UPDATE_HISTORY, 'subscription_id', string='Update History')
    subscriptions_update_history_line_ids = fields.One2many(MATE_HMS_SUBSCRIPTIONS_UPDATE_HISTORY_LINE, 'subscription_id', string='Update History', order='create_date desc')

    _sql_constraints = [
        ('subscription_date', "CHECK (start_date <= end_date)", "The start date must be anterior to the end date."),
    ]

    def _check_validate(self):
        self.ensure_one()
        now = datetime.today().date()
        if not self.start_date:
            return False
        if not self.end_date:
            return True
        if self.start_date <= now and self.end_date >= now:
            return True
        return False

    @api.constrains('patient_id', 'package_id')
    def _check_unique_patient_package(self):
        for record in self:
            duplicate = self.search([
                ('id', '!=', record.id),
                ('patient_id', '=', record.patient_id.id),
                ('package_id', '=', record.package_id.id),
                ('start_date', '<=', record.end_date),
                ('end_date', '>=', record.start_date)
            ], limit=1)
            if duplicate:
                raise ValidationError(_("Each patient can only register once for each package."))

    @api.depends('package_ids.appointment_usage_ids')
    def _compute_history_count(self):
        """
        Tính toán số lượng lịch sử sử dụng gói dịch vụ của bệnh nhân.
        """
        for record in self:
            record.history_count = self.env[MATE_HMS_PACKAGE_USAGE].search_count([
                ('subscription_line_id.subscription_id', '=', record.id)
            ])

    @api.model
    def create(self, vals):
        """
        Tạo một bản ghi mới cho đăng ký. Đồng thời, tạo các dòng đăng ký liên quan dựa trên các dòng gói dịch vụ.
        Args:
            vals (dict): Giá trị để tạo bản ghi mới.
        Returns:
            MateSubscriptions: Bản ghi đăng ký mới được tạo.
        """
        subcriptions = super(MateSubscriptions, self).create(vals)
        self.env[MATE_HMS_SUBSCRIPTIONS_LINE].create([
            {
                'subscription_id': subcriptions.id,
                'package_line_id': line.id,
                'qty': line.product_uom_qty,
                'patient_id': subcriptions.patient_id.id,
                'package_id': subcriptions.package_id.id,
                'remaining_qty': line.product_uom_qty,
            }
            for line in subcriptions.package_id.order_line
        ])
        return subcriptions

    def action_view_package_lines(self):
        self.ensure_one()
        return {
            'type': IR_ACTIONS_WINDOW,
            'name': 'Chi tiết Gói',
            'res_model': 'mate_hms.subscription.line',
            'view_mode': 'list',
            'view_id': self.env.ref('mate_hms_subscriptions.mate_hms_subscriptions_line_list_view').id,
            'target': 'new',
            'domain': [('subscription_id', '=', self.id)],
        }

    def subscriptions_usage_history(self):
        """
        Trả về lịch sử sử dụng của các gói dịch vụ y tế của bệnh nhân.
        """
        self.ensure_one()
        return {
            'type': IR_ACTIONS_WINDOW,
            'name': 'Subscription Usage History',
            'res_model': MATE_HMS_PACKAGE_USAGE,
            'view_mode': 'list',
            'view_id': self.env.ref('mate_hms_subscriptions.mate_hms_package_usage_list_view').id,
            'target': 'new',
            'domain': [('subscription_line_id.subscription_id', '=', self.id)],
        }

    def action_update_package(self):
        self.ensure_one()
        if not self._check_validate():
            raise UserError(_("Cannot update package when the subscription is expired."))
        return {
            'type': IR_ACTIONS_WINDOW,
            'name': 'Update Subscriptions',
            'res_model': MATE_HMS_SUBSCRIPTIONS_UPDATE_HISTORY,
            'view_mode': 'form',
            'view_id': self.env.ref('mate_hms_subscriptions.mate_hms_subscriptions_update_form_view').id,
            'target': 'new',
            'context': {
                'default_subscription_id': self.id,
                'default_from_package_id': self.package_id.id,
                'dialog_size': 'extra-large',
            }
        }


class MateSubscriptionLine(models.Model):
    """
    Lớp MateSubscriptionLine dùng để theo dõi việc sử dụng các gói dịch vụ y tế của bệnh nhân.
    Thuộc tính:
        subscription_id (Many2one): Liên kết đến bản ghi 'mate_hms.subscriptions', đại diện cho đăng ký của bệnh nhân.
            Bắt buộc phải có và sẽ bị xóa nếu bản ghi liên quan bị xóa.
        package_id (Many2one): Liên kết đến bản ghi 'mate_hms.package', đại diện cho gói dịch vụ y tế. Bắt buộc phải có.
        package_line_id (Many2one): Liên kết đến bản ghi 'mate_hms.package.line', đại diện cho dòng gói dịch vụ gốc. Bắt buộc phải có.
        patient_id (Many2one): Liên kết đến bản ghi 'mate_hms.patient', đại diện cho bệnh nhân. Bắt buộc phải có.
        product_id (Many2one): Trường liên kết đến 'package_line_id.product_id', lưu trữ và chỉ đọc.
        name (Text): Trường liên kết đến 'package_line_id.name', lưu trữ và chỉ đọc.
        qty (Float): Số lượng còn lại của gói dịch vụ y tế. Bắt buộc phải có.
        usage (Float): Số lượng đã sử dụng, được tính toán từ số lượng còn lại.
        remaining_qty (Float): Số lượng còn lại của gói dịch vụ y tế. Mặc định là 0.0.
    """
    _name = MATE_HMS_SUBSCRIPTIONS_LINE
    _description = 'Patient Package Line (Usage tracking)'

    subscription_id = fields.Many2one(MATE_HMS_SUBSCRIPTIONS, string='Subscription', required=True, ondelete='cascade')
    package_id = fields.Many2one(MATE_HMS_PACKAGE, string='Package', required=True)
    package_line_id = fields.Many2one('mate_hms.package.line', string='Original Package Line', required=True)
    patient_id = fields.Many2one('mate_hms.patient', string='Patient', required=True)
    appointment_usage_ids = fields.One2many(
        MATE_HMS_PACKAGE_USAGE,
        'subscription_line_id',
        string='Appointment Usage'
    )
    product_id = fields.Many2one(related='package_line_id.product_id', store=True, readonly=True)
    name = fields.Char(related='package_id.name', store=True, readonly=True)

    qty = fields.Float(string='In Package Quantity', required=True)
    usage = fields.Float(string='Used Quantity', default=0.0, compute='_compute_usage_qty')
    remaining_qty = fields.Float(string='Remaining Quantity', default=0.0)

    def _compute_usage_qty(self):
        """
        Tính toán số lượng đã sử dụng dựa trên số lượng còn lại.
        """
        for record in self:
            record.usage = record.qty - record.remaining_qty

    def action_package_history(self):
        """
        Mở cửa sổ hiển thị lịch sử sử dụng gói dịch vụ y tế của bệnh nhân.
        """
        self.ensure_one()
        return {
            'type': IR_ACTIONS_WINDOW,
            'name': 'Package Usage History',
            'res_model': MATE_HMS_PACKAGE_USAGE,
            'view_mode': 'list',
            'view_id': self.env.ref('mate_hms_subscriptions.mate_hms_package_usage_list_view').id,
            'target': 'new',
            'domain': [('subscription_line_id', '=', self.id)],
            'context': {
                'dialog_size': 'extra-large',
            },
        }


class MateSubscriptionUpdateHistory(models.Model):
    _name = MATE_HMS_SUBSCRIPTIONS_UPDATE_HISTORY
    _description = 'Subscription Update History'

    name = fields.Char(string='Name')
    subscription_id = fields.Many2one(MATE_HMS_SUBSCRIPTIONS, string='Subscription', required=True, ondelete='cascade')
    from_package_id = fields.Many2one(MATE_HMS_PACKAGE, string='From Package', required=True, ondelete='cascade')
    to_package_id = fields.Many2one(MATE_HMS_PACKAGE, string='To Package', required=True, ondelete='cascade')
    subscription_update_history_line_ids = fields.One2many(MATE_HMS_SUBSCRIPTIONS_UPDATE_HISTORY_LINE, 'subscription_update_history_id', string='Update History Lines')

    @api.onchange('from_package_id', 'to_package_id')
    def _onchange_package_ids(self):
        # Đây là ví dụ logic demo – bạn có thể thay thế bằng logic thật
        if self.from_package_id and self.to_package_id:
            self.subscription_update_history_line_ids = [(5, 0, 0)]
            new_product = self.to_package_id.order_line.mapped('product_id')
            new_package_line_replace = self.to_package_id.order_line.filtered(lambda x: x.product_id.id not in self.subscription_id.subscriptions_line_ids.mapped('product_id').ids)
            line = []
            for subscription_line_id in self.subscription_id.subscriptions_line_ids:
                new_product_ids = new_product.mapped('id')
                if subscription_line_id.product_id.id not in new_product_ids:
                    line.append((0, 0, {
                        'product_id': subscription_line_id.product_id.id,
                        'old_package': subscription_line_id.qty,
                        'old_used': subscription_line_id.usage,
                        'out_package': subscription_line_id.usage,
                        'subscription_update_history_id': self.id,
                        'subscription_id': self.subscription_id.id,
                    }))
                elif subscription_line_id.product_id.id in new_product_ids:
                    package_line = self.to_package_id.order_line.filtered(lambda x, subscription_line_id=subscription_line_id: x.product_id.id == subscription_line_id.product_id.id)
                    balance = package_line.product_uom_qty - subscription_line_id.remaining_qty
                    if balance == 0:
                        continue
                    new_package_used = min(package_line.product_uom_qty, subscription_line_id.usage)
                    line.append((0, 0, {
                        'product_id': subscription_line_id.product_id.id,
                        'old_package': subscription_line_id.qty,
                        'old_used': subscription_line_id.usage,
                        'new_package': package_line.product_uom_qty,
                        'new_package_used': new_package_used,
                        'over_package': abs(subscription_line_id.usage - new_package_used),
                        'out_package': 0,
                        'subscription_update_history_id': self.id,
                        'subscription_id': self.subscription_id.id,
                    }))
            for package_line in new_package_line_replace:
                line.append((0, 0, {
                    'product_id': package_line.product_id.id,
                    'new_package': package_line.product_uom_qty,
                    'subscription_update_history_id': self.id,
                    'subscription_id': self.subscription_id.id,
                }))
            self.subscription_update_history_line_ids = line

    @api.model
    def create(self, vals):
        """
        Tạo một bản ghi mới cho lịch sử cập nhật đăng ký.
        Args:
            vals (dict): Giá trị để tạo bản ghi mới.
        Returns:
            MateSubscriptionUpdateHistory: Bản ghi lịch sử cập nhật đăng ký mới được tạo.
        """
        # Lấy danh sách các dòng lịch sử cập nhật đăng ký từ giá trị đầu vào
        subscription_update_history_line_ids = vals.get('subscription_update_history_line_ids', [])
        vals['subscription_update_history_line_ids'] = []

        # Tạo bản ghi lịch sử cập nhật đăng ký
        subscription_update_history = super(MateSubscriptionUpdateHistory, self).create(vals)
        subscription_update_history.name = f"{subscription_update_history.from_package_id.name} → {subscription_update_history.to_package_id.name}"

        for val in subscription_update_history_line_ids:
            val[2]['subscription_update_history_id'] = subscription_update_history.id
        line_vals = [val[2] for val in subscription_update_history_line_ids if val[0] == 0]

        # Tạo các dòng lịch sử cập nhật đăng ký
        self.env[MATE_HMS_SUBSCRIPTIONS_UPDATE_HISTORY_LINE].create(line_vals)
        subscription_update_history.calulate_subscription()
        return subscription_update_history

    def calulate_subscription(self):
        """
        Tính toán số lượng đăng ký dựa trên các dòng lịch sử cập nhật đăng ký.
        """
        for rec in self:
            for rec_line in rec.subscription_update_history_line_ids:
                subscription_line = rec.subscription_id.subscriptions_line_ids.filtered(
                    lambda x, rec_line=rec_line: x.product_id.id == rec_line.product_id.id
                )
                if not subscription_line:
                    package_line = self.to_package_id.order_line.filtered(
                        lambda x, rec_line=rec_line: x.product_id.id == rec_line.product_id.id
                    )
                    self.env[MATE_HMS_SUBSCRIPTIONS_LINE].create({
                        'subscription_id': rec.subscription_id.id,
                        'package_id': rec.to_package_id.id,
                        'package_line_id': package_line.id,
                        'patient_id': rec.subscription_id.patient_id.id,
                        'qty': rec_line.new_package,
                        'remaining_qty': rec_line.new_package,
                        'usage': 0,
                    })
                    continue
                if rec_line.new_package == 0:
                    subscription_line.unlink()
                    continue
                if rec_line.new_package == subscription_line.qty:
                    continue
                if subscription_line.qty != rec_line.new_package:
                    subscription_line.qty = rec_line.new_package
                    subscription_line.remaining_qty = rec_line.new_package - rec_line.new_package_used
            rec.subscription_id.package_id = rec.to_package_id.id
        return True


class MateSubscriptionUpdateHistoryLine(models.Model):
    _name = MATE_HMS_SUBSCRIPTIONS_UPDATE_HISTORY_LINE
    _description = 'Update History Line'

    name = fields.Char(string='Name')
    subscription_id = fields.Many2one(MATE_HMS_SUBSCRIPTIONS, string='Subscription', required=True, ondelete='cascade')
    subscription_update_history_id = fields.Many2one('mate_hms.subscription.update.history', string='Subscription Update History', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product')
    old_package = fields.Integer(string='Old Package', default=0)
    old_used = fields.Integer(string='Used', default=0)
    new_package = fields.Integer(string='New Package)', default=0)
    new_package_used = fields.Integer(string='New Package Used', default=0)
    over_package = fields.Integer(string='Over Package', default=0)
    out_package = fields.Integer(string='Out Package', default=0)


class MateHmsAppointmentPackageUsage(models.Model):
    _name = MATE_HMS_PACKAGE_USAGE
    _description = "Appointment Package Usage"

    appointment_id = fields.Many2one('mate_hms.appointment', string='Appointment', required=True, ondelete='cascade')
    subscription_line_id = fields.Many2one(MATE_HMS_SUBSCRIPTIONS_LINE, string='Package Line', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', related='subscription_line_id.product_id')
    usage = fields.Float(string='Used Quantity', default=1.0)
    qty = fields.Float(string='Update Quantity')
    remaining_qty = fields.Float(string='Remaining Quantity')

    def action_open_appointment(self):
        self.ensure_one()
        return {
            'type': IR_ACTIONS_WINDOW,
            'name': 'Appointment',
            'res_model': 'mate_hms.appointment',
            'res_id': self.appointment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class MateSubscriptionCategory(models.Model):
    _name = 'mate_hms.subscription.category'
    _description = 'Subscription Category'

    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)', 'The subscription category name already exists.')
    ]

    name = fields.Char(string='Name', required=True)
