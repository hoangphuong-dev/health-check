from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime


class MatePatient(models.Model):
    RES_PARNER = 'res.partner'
    _name = 'mate_hms.patient'
    _description = 'Patient'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'mate_hms.mixin', 'mate_hms.document.mixin']
    _inherits = {
        RES_PARNER: 'partner_id',
    }
    _rec_names_search = ['name', 'code']

    def _rec_count(self):
        Invoice = self.env['account.move']
        for rec in self:
            rec.invoice_count = Invoice.sudo().search_count([('partner_id', '=', rec.partner_id.id)])

    partner_id = fields.Many2one(RES_PARNER, required=True, ondelete='restrict', auto_join=True, string='Related Partner', help='Partner-related data of the Patient')
    hospital_number = fields.Char(string='Hospital Number', required=True, copy=False, tracking=True)
    gov_code = fields.Char(string='Government Identity', copy=False, tracking=True)
    gov_code_label = fields.Char(compute="mate_get_gov_code_label", string="Government Identity Label")
    marital_status = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widow', 'Widow')], string='Marital Status', default="single")
    spouse_name = fields.Char("Spouse's Name")
    spouse_edu = fields.Char("Spouse's Education")
    spouse_business = fields.Char("Spouse's Business")
    education = fields.Char("Patient Education")
    is_corpo_tieup = fields.Boolean(string='Corporate Tie-Up', help="If not checked, these Corporate Tie-Up Group will not be visible at all.")
    corpo_company_id = fields.Many2one(RES_PARNER, string='Corporate Company', domain="[('is_company', '=', True), ('customer_rank', '>', 0)]", ondelete='restrict')
    emp_code = fields.Char(string='Employee Code')
    user_id = fields.Many2one('res.users', string='Related User', ondelete='cascade', help='User-related data of the patient')
    primary_physician_id = fields.Many2one('mate_hms.physician', 'Primary Care Doctor')
    mate_tag_ids = fields.Many2many('mate_hms.patient.tag', 'patient_tag_hms_rel', 'tag_id', 'patient_tag_id', string="HMS Tags")

    invoice_count = fields.Integer(compute='_rec_count', string='# Invoices')
    occupation = fields.Char("Occupation")
    mate_religion_id = fields.Many2one('mate_hms.religion', string="Religion")
    caste = fields.Char("Tribe")
    nationality_id = fields.Many2one("res.country", string="Nationality")
    passport = fields.Char("Passport Number")
    active = fields.Boolean(string="Active", default=True)
    location_url = fields.Text()

    _sql_constraints = [
        ('unique_hospital_number', 'UNIQUE(hospital_number)', 'The hospital number already exists.'),
    ]

    def mate_get_gov_code_label(self):
        for rec in self:
            rec.gov_code_label = self.env.company.country_id.gov_code_label

    def check_gov_code(self, gov_code):
        patient = self.search([('gov_code', '=', gov_code)], limit=1)
        if patient:
            raise ValidationError(_('Patient already exists with Government Identity: %s.') % (gov_code))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', '/') == '/':
                vals['code'] = self.env['ir.sequence'].next_by_code('mate_hms.patient') or ''
            company_id = vals.get('company_id')
            if company_id:
                company_id = self.env['res.company'].sudo().search([('id', '=', company_id)], limit=1)
            else:
                company_id = self.env.company
            if company_id.unique_gov_code and vals.get('gov_code'):
                self.check_gov_code(vals.get('gov_code'))
            vals['customer_rank'] = True
        return super().create(vals_list)

    def write(self, values):
        company_id = self.sudo().company_id or self.env.user.sudo().company_id
        if company_id.unique_gov_code and values.get('gov_code'):
            self.check_gov_code(values.get('gov_code'))
        return super(MatePatient, self).write(values)

    def view_invoices(self):
        invoices = self.env['account.move'].search([('partner_id', '=', self.partner_id.id), ('move_type', 'in', ('out_invoice', 'out_refund'))])
        action = self.with_context(mate_open_blank_list=True).mate_hms_action_view_invoice(invoices)
        action['context'].update({
            'default_partner_id': self.partner_id.id,
            'default_patient_id': self.id,
        })
        return action

    @api.model
    def send_birthday_email(self):
        wish_template_id = self.env.ref('mate_hms_base.email_template_birthday_wish', raise_if_not_found=False)
        user_cmp_template = self.env.company.birthday_mail_template_id
        today = datetime.now()
        today_month_day = '%-' + today.strftime('%m') + '-' + today.strftime('%d')
        patient_ids = self.search([('birthday', 'like', today_month_day)])
        for patient_id in patient_ids:
            if patient_id.email:
                wish_temp = patient_id.company_id.birthday_mail_template_id or user_cmp_template or wish_template_id
                wish_temp.sudo().send_mail(patient_id.id, force_send=True)

    def _compute_display_name(self):
        for rec in self:
            name = rec.name
            if rec.title and rec.title.shortcut:
                name = (rec.title.shortcut or '') + ' ' + (rec.name or '')
            rec.display_name = name

    @api.onchange('mobile')
    def _onchange_mobile_warning(self):
        if not self.mobile:
            return
        message = ''
        domain = [('mobile', '=', self.mobile)]
        if self._origin and self._origin.id:
            domain += [('id', ' != ', self._origin.id)]
        patients = self.sudo().search(domain)
        for patient in patients:
            message += _('\nThe Mobile number is already registered with another Patient: %s, Government Identity:%s, DOB: %s.') % (patient.name, patient.gov_code, patient.birthday)
        if message:
            message += _('\n\n Are you sure you want to create a new Patient?')
            return {
                'warning': {
                    'title': _("Warning for Mobile Dupication"),
                    'message': message,
                }
            }

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        company = self.env.company
        if company.country_id.vat_label:
            for node in arch.xpath("//field[@name='gov_code']"):
                node.attrib["string"] = company.country_id.gov_code_label
        return arch, view

    @api.onchange('hospital_number')
    def _check_hospital_number(self):
        num_str = self.hospital_number or ''
        if self.hospital_number:
            if len(num_str) != 9 or not num_str.startswith('8') or not num_str.isdigit():
                raise ValidationError(_("Hospital number must start with 9 and must be 9 characters long."))

    @api.onchange('name')
    def _check_name(self):
        if self.name and len(self.name) > 100:
            raise ValidationError("Name cannot be longer than 100 characters.")
