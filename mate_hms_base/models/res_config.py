# Part of Mate Technology JSC. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.service import common
import requests
import json


class ResCompany(models.Model):
    _inherit = "res.company"
    IR_MODULE_MODULE = "ir.module.module"

    birthday_mail_template_id = fields.Many2one('mail.template', 'Birthday Wishes Template', help="This will set the default mail template for birthday wishes.")
    unique_gov_code = fields.Boolean('Unique Government Identity for Patient', help='Set this True if the Givernment Identity in patients should be unique.')

    # Định nghĩa hằng số cho các chuỗi lặp lại
    MATE_ACCESS_EXPIRED = "mate.access.expired"
    MATE_ACCESS_MESSAGE = "mate.access.message"
    IR_CONFIG_PARAMETER = "ir.config_parameter"

    # Call this method directly in case of dependcy issue like mate_certification (call in mate_hms_certification)
    def mate_create_sequence(self, name, code, prefix, padding=3):
        self.env['ir.sequence'].sudo().create({
            'name': self.name + " : " + name,
            'code': code,
            'padding': padding,
            'number_next': 1,
            'number_increment': 1,
            'prefix': prefix,
            'company_id': self.id,
            'mate_auto_create': False,
        })

    def mate_auto_create_sequences(self):
        sequences = self.env['ir.sequence'].search([('mate_auto_create', '=', True)])
        for sequence in sequences:
            self.mate_create_sequence(name=sequence.name, code=sequence.code, prefix=sequence.prefix,
                                      padding=sequence.padding)

    # Auto create marked sequences in other HMS modules.
    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for record in res:
            record.mate_auto_create_sequences()
        return res

    @api.model
    def mate_get_blocking_data(self):
        ir_config_model = self.env[self.IR_CONFIG_PARAMETER]
        access_is_blocked = ir_config_model.sudo().get_param(self.MATE_ACCESS_EXPIRED, "False")
        message = ''
        if access_is_blocked != 'False':
            message = ir_config_model.sudo().get_param(self.MATE_ACCESS_MESSAGE)
            if not message:
                message = "Your Access Are blocked please contact at info@mate.com.vn"
        return {"name": message}

    @api.model
    def mate_send_access_data(self, data):
        ir_config_model = self.env[self.IR_CONFIG_PARAMETER].sudo()

        domain = "https://www.almightyhms.com" + '/mate/module/checksubscription'
        reply = requests.post(domain, json.dumps(data),
                              headers={'accept': 'application/json', 'Content-Type': 'application/json'})
        if reply.status_code == 200:
            reply = json.loads(reply.text)
            subscription_status = reply['result'].get('subscription_status')
            if subscription_status != 'active':
                ir_config_model.set_param(self.MATE_ACCESS_EXPIRED, "True")
            if subscription_status == 'active':
                ir_config_model.set_param(self.MATE_ACCESS_EXPIRED, "False")

    @api.model
    def mate_update_access_data(self):
        data = self._prepare_basic_access_data()
        self._enrich_data_with_version_info(data)
        self._enrich_data_with_module_info(data)
        self.mate_send_access_data(data)

    @api.model
    def _prepare_basic_access_data(self):
        user = self.env.user
        company = user.sudo().company_id
        ir_config_model = self.env[self.IR_CONFIG_PARAMETER].sudo()
        secret = ir_config_model.get_param("database.secret")
        url = ir_config_model.get_param("web.base.url")
        module = self.env[self.IR_MODULE_MODULE].sudo()
        return {
            "installed_modules": module.search([('state', '=', 'installed')]).mapped('name'),
            "db_secret": secret,
            "company_name": company.name,
            "email": company.email,
            "mobile": company.mobile,
            "url": url,
            'users': self.env['res.users'].sudo().search_count([('share', '=', False)]),
            'physicians': self.env['mate_hms.physician'].sudo().search_count([]),
            'patients': self.env['mate_hms.patient'].sudo().search_count([]),
        }

    @api.model
    def _enrich_data_with_version_info(self, data):
        version_info = common.exp_version()
        data['version'] = version_info.get('server_serie')

    @api.model
    def _enrich_data_with_module_info(self, data):
        module = self.env[self.IR_MODULE_MODULE].sudo()
        self._add_hms_module_data(data, module)
        self._add_additional_modules_data(data, module)

    @api.model
    def _add_hms_module_data(self, data, module):
        if module.search([('name', '=', 'mate_hms'), ('state', '=', 'installed')]):
            data.update({
                'appointments': self.env['mate_hms.appointment'].sudo().search_count([]),
                'evaluations': self.env['mate_hms.patient.evaluation'].sudo().search_count([]),
                'prescriptions': self.env['prescription.order'].sudo().search_count([]),
                'procedures': self.env['mate_hms.patient.procedure'].sudo().search_count([]),
                'treatments': self.env['mate_hms.treatment'].sudo().search_count([]),
            })

    @api.model
    def _add_additional_modules_data(self, data, module):
        modules_to_check = [
            ('mate_hms_insurance', lambda: {
                'insurance_policies': self.env['mate_hms.patient.insurance'].sudo().search_count([]),
                'claims': self.env['mate_hms.insurance.claim'].sudo().search_count([])
            }),
            ('mate_hms_certification', lambda: {
                'certificates': self.env['certificate.management'].sudo().search_count([])
            }),
            ('mate_hms_hospitalization', lambda: {
                'hospitalizations': self.env['mate.hospitalization'].sudo().search_count([])
            }),
            ('mate_consent_form', lambda: {
                'consentforms': self.env['mate.consent.form'].sudo().search_count([])
            }),
            ('mate_hms_laboratory', lambda: {
                'laboratory_requests': self.env['mate.laboratory.request'].sudo().search_count([]),
                'laboratory_results': self.env['patient.laboratory.test'].sudo().search_count([])
            }),
            ('mate_hms_radiology', lambda: {
                'radiology_requests': self.env['mate.radiology.request'].sudo().search_count([]),
                'radiology_results': self.env['patient.radiology.test'].sudo().search_count([])
            }),
            ('mate_hms_commission', lambda: {
                'commissions': self.env['mate.commission'].sudo().search_count([])
            }),
            ('mate_hms_vaccination', lambda: {
                'vaccinations': self.env['mate.vaccination'].sudo().search_count([])
            }),
            ('mate_hms_emergency', lambda: {
                'emergencies': self.env['mate.hms.emergency'].sudo().search_count([])
            }),
            ('mate_hms_surgery', lambda: {
                'surgeries': self.env['mate_hms.surgery'].sudo().search_count([])
            }),
            ('mate_sms', lambda: {
                'sms': self.env['mate.sms'].sudo().search_count([])
            }),
            ('mate_whatsapp', lambda: {
                'whatsapp': self.env['mate.whatsapp.message'].sudo().search_count([])
            }),
        ]

        for module_name, data_getter in modules_to_check:
            if module.search([('name', '=', module_name), ('state', '=', 'installed')]):
                data.update(data_getter())


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    birthday_mail_template_id = fields.Many2one('mail.template', related='company_id.birthday_mail_template_id', string='Birthday Wishes Template', help="This will set the default mail template for birthday wishes.", readonly=False)
    unique_gov_code = fields.Boolean('Unique Government Identity for Patient', related='company_id.unique_gov_code', readonly=False, help='Set this True if the Givernment Identity in patients should be unique.')
