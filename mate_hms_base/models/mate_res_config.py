# Part of Mate Technology JSC. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.service import common
import requests
import json


class ResCompany(models.Model):
    _inherit = "res.company"
    IR_MODULE_MODULE = "ir.module.module"
    IR_CONFIG_PARAMETER = "ir.config_parameter"
    MATE_ACCESS_EXPIRED = "mate.access.expired"
    STATE_INSTALLED = "installed"

    birthday_mail_template_id = fields.Many2one('mail.template', 'Birthday Wishes Template',
                                                help="This will set the default mail template for birthday wishes.")
    unique_gov_code = fields.Boolean('Unique Government Identity for Patient',
                                     help='Set this True if the Givernment Identity in patients should be unique.')

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
            message = ir_config_model.sudo().get_param("mate.access.message")
            if not message:
                message = "Your Access Are blocked please contact at info@mate.com.vn"
        return {"name": message}

    @api.model
    def mate_send_access_data(self, data):
        ir_config_model = self.env[self.IR_CONFIG_PARAMETER].sudo()
        try:
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
        except Exception:
            pass

    @api.model
    def _prepare_base_access_data(self):
        user = self.env.user
        company = user.sudo().company_id
        ir_config_model = self.env[self.IR_CONFIG_PARAMETER].sudo()
        secret = ir_config_model.get_param("database.secret")
        url = ir_config_model.get_param("web.base.url")
        module = self.env[self.IR_MODULE_MODULE].sudo()

        data = {
            "installed_modules": module.search([('state', '=', self.STATE_INSTALLED)]).mapped('name'),
            "db_secret": secret,
            "company_name": company.name,
            "email": company.email,
            "mobile": company.mobile,
            "url": url,
            'users': self.env['res.users'].sudo().search_count([('share', '=', False)]),
            'physicians': self.env['mate_hms.physician'].sudo().search_count([]),
            'patients': self.env['mate_hms.patient'].sudo().search_count([]),
        }

        try:
            version_info = common.exp_version()
            data['version'] = version_info.get('server_serie')
        except Exception:
            pass

        return data

    @api.model
    def _prepare_hms_module_data(self):
        data = {}
        try:
            if self._is_module_installed('mate_hms'):
                data.update({
                    'appointments': self.env['mate_hms.appointment'].sudo().search_count([]),
                    'evaluations': self.env['mate_hms.patient.evaluation'].sudo().search_count([]),
                    'prescriptions': self.env['prescription.order'].sudo().search_count([]),
                    'procedures': self.env['mate_hms.patient.procedure'].sudo().search_count([]),
                    'treatments': self.env['mate_hms.treatment'].sudo().search_count([]),
                })
        except Exception:
            pass
        return data

    @api.model
    def _is_module_installed(self, module_name):
        """Check if specified module is installed."""
        module = self.env[self.IR_MODULE_MODULE].sudo()
        return bool(module.search([('name', '=', module_name), ('state', '=', self.STATE_INSTALLED)]))

    @api.model
    def _get_model_count(self, model_name):
        """Get record count for specified model."""
        try:
            return self.env[model_name].sudo().search_count([])
        except Exception:
            return 0

    @api.model
    def _check_module_data(self, module_name, model_data_dict):
        """Generic method to check module data.
        
        Args:
            module_name: Name of the module to check
            model_data_dict: Dictionary mapping model names to data keys
            
        Returns:
            Dictionary with collected data or empty dict
        """
        data = {}
        if self._is_module_installed(module_name):
            for model_name, data_key in model_data_dict.items():
                count = self._get_model_count(model_name)
                if count > 0:
                    data[data_key] = count
        return data

    @api.model
    def _check_insurance_module(self):
        return self._check_module_data('mate_hms_insurance', {
            'mate_hms.patient.insurance': 'insurance_policies',
            'mate_hms.insurance.claim': 'claims'
        })

    @api.model
    def _check_certification_module(self):
        return self._check_module_data('mate_hms_certification', {
            'certificate.management': 'certificates'
        })

    @api.model
    def _check_hospitalization_module(self):
        return self._check_module_data('mate_hms_hospitalization', {
            'mate.hospitalization': 'hospitalizations'
        })

    @api.model
    def _check_consent_module(self):
        return self._check_module_data('mate_consent_form', {
            'mate.consent.form': 'consentforms'
        })

    @api.model
    def _check_laboratory_module(self):
        return self._check_module_data('mate_hms_laboratory', {
            'mate.laboratory.request': 'laboratory_requests',
            'patient.laboratory.test': 'laboratory_results'
        })

    @api.model
    def _check_radiology_module(self):
        return self._check_module_data('mate_hms_radiology', {
            'mate.radiology.request': 'radiology_requests',
            'patient.radiology.test': 'radiology_results'
        })

    @api.model
    def _check_other_modules(self):
        data = {}
        module_mappings = [
            ('mate_hms_commission', {'mate.commission': 'commissions'}),
            ('mate_hms_vaccination', {'mate.vaccination': 'vaccinations'}),
            ('mate_hms_emergency', {'mate.hms.emergency': 'emergencies'}),
            ('mate_hms_surgery', {'mate_hms.surgery': 'surgeries'}),
            ('mate_sms', {'mate.sms': 'sms'}),
            ('mate_whatsapp', {'mate.whatsapp.message': 'whatsapp'})
        ]
        
        for module_name, model_dict in module_mappings:
            data.update(self._check_module_data(module_name, model_dict))
        
        return data

    @api.model
    def mate_update_access_data(self):
        data = self._prepare_base_access_data()

        # Add HMS module data
        data.update(self._prepare_hms_module_data())

        # Try to add data from additional modules
        try:
            # Insurance module
            data.update(self._check_insurance_module())

            # Certification module
            data.update(self._check_certification_module())

            # Hospitalization module
            data.update(self._check_hospitalization_module())

            # Consent form module
            data.update(self._check_consent_module())

            # Laboratory module
            data.update(self._check_laboratory_module())

            # Radiology module
            data.update(self._check_radiology_module())

            # Other modules
            data.update(self._check_other_modules())
        except Exception:
            pass

        # Send collected data
        self.mate_send_access_data(data)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    birthday_mail_template_id = fields.Many2one('mail.template', related='company_id.birthday_mail_template_id',
                                                string='Birthday Wishes Template',
                                                help="This will set the default mail template for birthday wishes.",
                                                readonly=False)
    unique_gov_code = fields.Boolean('Unique Government Identity for Patient', related='company_id.unique_gov_code',
                                     readonly=False,
                                     help='Set this True if the Givernment Identity in patients should be unique.')
