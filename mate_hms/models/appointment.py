import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

MATE_APPOINTMENT = 'mate_hms.appointment'
HR_DEPARTMENT = 'hr.department'

_logger = logging.getLogger()


class MateAppointmentPurpose(models.Model):
    _name = 'mate_hms.appointment.purpose'
    _description = "Appointment Purpose"
    name = fields.Char(string='Purpose', required=True)


class MateAppointmentCabin(models.Model):
    _name = 'mate_hms.appointment.cabin'
    _description = "Appointment Cabin"
    name = fields.Char(string='Cabin', required=True)


class MateCancelReason(models.Model):
    _name = 'mate_hms.cancel.reason'
    _description = "Cancel Reason"
    name = fields.Char(string='Reason', required=True)


class MateAppointment(models.Model):
    _name = MATE_APPOINTMENT
    _inherit = ['mail.thread', 'mail.activity.mixin', 'mate_hms.mixin', 'mate_hms.document.mixin']
    _description = "Appointment"
    _order = "id desc"

    IR_ACTIONS = "ir.actions.actions"
    MATE_HMS_PHYSICIAN = "mate_hms.physician"

    @api.model
    def _get_service_id(self):
        consultation = False
        if self.env.company.consultation_product_id:
            consultation = self.env.company.consultation_product_id.id
        return consultation

    @api.model
    def _get_default_physician(self):
        physician_id = False
        if self.env.user.sudo().physician_id:
            physician_id = self.env.user.physician_id.id
        return physician_id

    @api.depends('medical_alert_ids')
    def _get_alert_count(self):
        for rec in self:
            rec.alert_count = len(rec.medical_alert_ids)

    @api.depends('consumable_line_ids')
    def _get_consumable_line_count(self):
        for rec in self:
            rec.consumable_line_count = len(rec.consumable_line_ids)

    @api.depends('patient_id', 'patient_id.birthday', 'date')
    def get_patient_age(self):
        for rec in self:
            age = ''
            if rec.patient_id.birthday:
                end_data = rec.date or fields.Datetime.now()
                delta = relativedelta(end_data, rec.patient_id.birthday)
                if delta.years <= 2:
                    age = str(delta.years) + _(" Year") + str(delta.months) + _(" Month ") + str(delta.days) + _(" Days")
                else:
                    age = str(delta.years) + _(" Year")
            rec.age = age

    @api.depends('patient_id', 'patient_id.hospital_number')
    def compute_patient_hospital_number(self):
        for rec in self:
            if rec.patient_id.hospital_number:
                rec.hospital_number = rec.patient_id.hospital_number

    @api.depends('evaluation_ids')
    def _get_evaluation(self):
        for rec in self:
            rec.evaluation_id = rec.evaluation_ids[0].id if rec.evaluation_ids else False

    def _acs_get_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

    def _acs_invoice_policy(self):
        for rec in self:
            appointment_invoice_policy = rec.sudo().company_id.appointment_invoice_policy
            if rec.product_id.appointment_invoice_policy:
                appointment_invoice_policy = rec.product_id.appointment_invoice_policy
            rec.appointment_invoice_policy = appointment_invoice_policy

    def get_procudures_to_invoice(self):
        procedure = self.env['mate_hms.patient.procedure']
        for rec in self:
            procedures = procedure.search([('appointment_ids', 'in', rec.id), ('invoice_id', '=', False)])
            rec.procedure_to_invoice_ids = [(6, 0, procedures.ids)]

    def acs_get_department(self):
        for rec in self:
            acs_department_id = False
            if rec.department_id and rec.department_id.id:
                acs_department_id = self.env[HR_DEPARTMENT].sudo().search([('id', '=', rec.department_id.id)]).id
            rec.acs_department_id = acs_department_id

    @api.depends('date')
    def get_appointment_date(self):
        for rec in self:
            rec.appointment_date = rec.date.date()

    name = fields.Char(string='Number', readonly=True, copy=False, tracking=1)
    patient_id = fields.Many2one('mate_hms.patient', ondelete='restrict', string='Patient', required=True, index=True, help='Patient Name', tracking=1)
    image_128 = fields.Binary(related='patient_id.image_128', string='Image', readonly=True)
    physician_id = fields.Many2one(MATE_HMS_PHYSICIAN, ondelete='restrict', string='Physician', index=True, help='Physician\'s Name', tracking=1, default=_get_default_physician)
    department_id = fields.Many2one(HR_DEPARTMENT, ondelete='restrict', domain=[('patient_department', '=', True)], string='Department', tracking=1)

    # ACS: Added department field agian here to avoid portal error. Insted of reading department_id used acs_department_idfield so error vanbe avoided.
    acs_department_id = fields.Many2one(HR_DEPARTMENT, compute="acs_get_department")
    invoice_exempt = fields.Boolean(string='Invoice Exempt')
    follow_date = fields.Datetime(string="Follow Up Date", copy=False)

    reminder_date = fields.Datetime(string="Reminder Date", copy=False)
    acs_reminder_sent = fields.Boolean("Reminder Sent", default=False)

    evaluation_ids = fields.One2many('mate_hms.patient.evaluation', 'appointment_id', 'Evaluations')
    evaluation_id = fields.Many2one('mate_hms.patient.evaluation', ondelete='restrict', compute=_get_evaluation, string='Evaluation', store=True)

    weight = fields.Float(related="evaluation_id.weight", string='Weight', help="Weight in KG")
    height = fields.Float(related="evaluation_id.height", string='Height', help="Height in cm")
    temp = fields.Float(related="evaluation_id.temp", string='Temp')
    hr = fields.Integer(related="evaluation_id.hr", string='HR', help="Heart Rate")
    rr = fields.Integer(related="evaluation_id.rr", string='RR', help='Respiratory Rate')
    systolic_bp = fields.Integer(related="evaluation_id.systolic_bp", string="Systolic BP")
    diastolic_bp = fields.Integer(related="evaluation_id.diastolic_bp", string="Diastolic BP")
    spo2 = fields.Integer(related="evaluation_id.spo2", string='SpO2', help='Oxygen Saturation, percentage of oxygen bound to hemoglobin')
    rbs = fields.Integer(related="evaluation_id.rbs", string='RBS', help="Random blood sugar measures blood glucose regardless of when you last ate.")
    bmi = fields.Float(related="evaluation_id.bmi", string='Body Mass Index')
    bmi_state = fields.Selection(related="evaluation_id.bmi_state", string='BMI State')
    mate_weight_name = fields.Char(related="evaluation_id.mate_weight_name", string='Patient Weight unit of measure label')
    mate_height_name = fields.Char(related="evaluation_id.mate_height_name", string='Patient Height unit of measure label')
    mate_temp_name = fields.Char(related="evaluation_id.mate_temp_name", string='Patient Temp unit of measure label')
    mate_spo2_name = fields.Char(related="evaluation_id.mate_spo2_name", string='Patient SpO2 unit of measure label')
    mate_rbs_name = fields.Char(related="evaluation_id.mate_rbs_name", string='Patient RBS unit of measure label')

    pain_level = fields.Selection(related="evaluation_id.pain_level", string="Pain Level")
    pain = fields.Selection(related="evaluation_id.pain", string="Pain")

    differencial_diagnosis = fields.Text(string='Differential Diagnosis', help="The process of weighing the probability of one disease versus that of other diseases possibly accounting for a patient's illness.")
    medical_advice = fields.Text(string='Medical Advice', help="The provision of a formal professional opinion regarding what a specific individual should or should not do to restore or preserve health.")
    chief_complain = fields.Text(string='Chief Complaints', help="The concise statement describing the symptom, problem, condition, diagnosis, physician-recommended return, or other reason for a medical encounter.")
    present_illness = fields.Text(string='History of Present Illness')
    lab_report = fields.Text(string='Lab Report', help="Details of the lab report.")
    radiological_report = fields.Text(string='Radiological Report', help="Details of the Radiological Report")
    notes = fields.Text(string='Notes')
    past_history = fields.Text(string='Past History', help="Past history of any diseases.")
    invoice_id = fields.Many2one('account.move', string='Invoice', copy=False)
    payment_state = fields.Selection(related="invoice_id.payment_state", store=True, string="Payment Status")
    urgency = fields.Selection([('normal', 'Normal'), ('urgent', 'Urgent'), ('medical_emergency', 'Medical Emergency')], string='Urgency Level', default='normal')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'), ('waiting', 'Waiting'), ('in_consultation', 'In consultation'), ('pause', 'Pause'), ('to_invoice', 'To Invoice'), ('done', 'Done'), ('cancel', 'Cancelled')], string='Status', default='draft', required=True, copy=False, tracking=1)
    product_id = fields.Many2one('product.product', ondelete='restrict', string='Consultation Service', help="Consultation Services", domain=[('hospital_product_type', '=', "consultation")], required=True, default=_get_service_id)
    age = fields.Char(compute="get_patient_age", string='Age', store=True, help="Computed patient age at the moment of the evaluation")
    hospital_number = fields.Char(compute="compute_patient_hospital_number", store=True, help="Computed patient age at the moment of the evaluation")
    company_id = fields.Many2one('res.company', ondelete='restrict', string='Hospital', default=lambda self: self.env.company)
    appointment_invoice_policy = fields.Selection([('at_end', 'Invoice in the End'), ('anytime', 'Invoice Anytime'), ('advance', 'Invoice in Advance')], compute=_acs_invoice_policy, string="Appointment Invoicing Policy")
    invoice_exempt = fields.Boolean('Invoice Exempt')
    consultation_type = fields.Selection([('consultation', 'Consultation'), ('followup', 'Follow Up')], 'Consultation Type', copy=False)

    diseases_ids = fields.Many2many('mate_hms.diseases', 'diseases_appointment_rel', 'diseas_id', 'appointment_id', 'Diseases')
    medical_history = fields.Text(related='patient_id.medical_history', string="Past Medical History", readonly=True)
    patient_diseases_ids = fields.One2many('mate_hms.patient.disease', readonly=True, related='patient_id.patient_diseases_ids', string='Disease History')

    date = fields.Datetime(string='Date', default=fields.Datetime.now, tracking=1, copy=False)
    date_to = fields.Datetime(string='Date To', default=fields.Datetime.now() + timedelta(minutes=15), copy=False, tracking=1)
    appointment_date = fields.Date(string='Appointment Date', compute="get_appointment_date", copy=False, store=True)

    planned_duration = fields.Float('Duration', compute="_get_planned_duration", inverse='_inverse_planned_duration', default=lambda self: self.env.company.mate_appointment_planned_duration)
    manual_planned_duration = fields.Float('Manual Duration')

    waiting_date_start = fields.Datetime('Waiting Start Date', copy=False)
    waiting_date_end = fields.Datetime('Waiting end Date', copy=False)
    waiting_duration = fields.Float('Wait Time', readonly=True, copy=False)
    waiting_duration_timer = fields.Float(string='Wait Timer', compute="_compute_waiting_running_duration", readonly=True, default="0.1", copy=False)

    date_start = fields.Datetime(string='Start Date', copy=False)
    date_end = fields.Datetime(string='End Date', copy=False)
    appointment_duration = fields.Float('Consultation Time', readonly=True, copy=False)
    appointment_duration_timer = fields.Float(string='Consultation Timer', compute="_compute_consulataion_running_duration", readonly=True, default="0.1", copy=False)

    purpose_id = fields.Many2one('mate_hms.appointment.purpose', ondelete='cascade', string='Purpose', help="Appointment Purpose")
    cabin_id = fields.Many2one('mate_hms.appointment.cabin', ondelete='cascade', string='Consultation Room (Cabin)', help="Appointment Cabin", copy=False)
    treatment_id = fields.Many2one('hms.treatment', ondelete='cascade', string='Treatment', help="Treatment Id", tracking=1)

    ref_physician_id = fields.Many2one('res.partner', ondelete='restrict', string='Referring Physician', index=True, help='Referring Physician', domain=[('is_referring_doctor', '=', True)])
    responsible_id = fields.Many2one(MATE_HMS_PHYSICIAN, "Responsible Jr. Doctor")
    medical_alert_ids = fields.Many2many('mate_hms.medical.alert', 'appointment_medical_alert_rel', 'appointment_id', 'alert_id', string='Medical Alerts', related='patient_id.medical_alert_ids')
    alert_count = fields.Integer(compute='_get_alert_count', default=0)
    consumable_line_ids = fields.One2many('mate_hms.consumable.line', 'appointment_id', string='Consumable Line', copy=False)
    consumable_line_count = fields.Integer(compute="_get_consumable_line_count", store=True)
    # Field dùng để tính toán tổng số tiền của các services mà bệnh nhân sử dụng
    amount_total = fields.Float(default=0)
    # Only used in case of advance invoice
    consumable_invoice_id = fields.Many2one('account.move', string="Consumables Invoice", copy=False)

    pause_date_start = fields.Datetime('Pause Start Date', copy=False)
    pause_date_end = fields.Datetime('Pause end Date', copy=False)
    pause_duration = fields.Float('Paused Time', readonly=True, copy=False)
    prescription_ids = fields.One2many('prescription.order', 'appointment_id', 'Prescriptions', copy=False)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', check_company=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", help="If you change the pricelist, related invoice will be affected.")
    location = fields.Char(string="Appointment Location")
    outside_appointment = fields.Boolean(string="Outside Appointment")
    is_video_call = fields.Boolean("Is Video Call")
    cancel_reason = fields.Text(string="Cancel Reason", copy=False)
    cancel_reason_id = fields.Many2one('mate_hms.cancel.reason', string='Cancellation Reason')
    user_id = fields.Many2one('res.users', string='Responsible', ondelete='cascade', help='Responsible User for appointment validation And further Followup.')
    acs_kit_id = fields.Many2one('mate_hms.product.kit', string='Kit')
    acs_kit_qty = fields.Integer("Kit Qty", default=1)
    invoice_ids = fields.One2many("account.move", "appointment_id", string="Invoices", groups="account.group_account_invoice")
    invoice_count = fields.Integer(compute="_acs_get_invoice_count", string="# Invoices", groups="account.group_account_invoice")
    procedure_to_invoice_ids = fields.Many2many('mate_hms.patient.procedure', 'acs_appointment_procedure_rel', 'appointment_id', 'procedure_id', compute="get_procudures_to_invoice", string="Procedures to Invoice")
    refer_reason = fields.Text(string='Refer Reason')

    refered_from_appointment_id = fields.Many2one(MATE_APPOINTMENT, string="Refered From Appointment")
    refered_from_physician_id = fields.Many2one(MATE_HMS_PHYSICIAN, related='refered_from_appointment_id.physician_id', string='Refered from Physician', tracking=1, store=True)
    refered_from_reason = fields.Text(related='refered_from_appointment_id.refer_reason', string='Refered From Reason', tracking=1, store=True)

    refered_to_appointment_id = fields.Many2one(MATE_APPOINTMENT, string="Refered Appointment")
    refered_to_physician_id = fields.Many2one(MATE_HMS_PHYSICIAN, related='refered_to_appointment_id.physician_id', ondelete='restrict', string='Refered to Physician', tracking=1, store=True)

    # ACS NOTE: Because of error for portal appointment creation added _compute_field_value method.
    department_type = fields.Selection(related='department_id.department_type', string="Appointment Department", store=True)

    # Just to make object selectable in selction field this is required: Waiting Screen
    acs_show_in_wc = fields.Boolean(default=True)
    nurse_id = fields.Many2one('res.users', 'Assigned Nurse')
    acs_show_create_invoice = fields.Boolean(compute="get_acs_show_create_invoice", string="Show Create Invoice Button")
    acs_show_conumable_create_invoice = fields.Boolean(compute="get_acs_show_create_invoice", string="Show Consumable Create Invoice Button")

    # ACS: Compute visiblity of create invocie button.
    def get_acs_show_create_invoice(self):
        for rec in self:
            acs_show_create_invoice = False
            if not rec.invoice_id :
                if rec.state == 'to_invoice':
                    acs_show_create_invoice = True
                elif rec.appointment_invoice_policy == 'anytime' and not rec.invoice_exempt:
                    acs_show_create_invoice = True
                elif rec.appointment_invoice_policy == 'advance' and not rec.invoice_exempt:
                    acs_show_create_invoice = True

            rec.acs_show_conumable_create_invoice = True if ((not rec.invoice_id) and rec.state != 'done' and (not rec.invoice_exempt) and (rec.consumable_line_count) and (not rec.consumable_invoice_id) and rec.appointment_invoice_policy != 'at_end') else False
            rec.acs_show_create_invoice = acs_show_create_invoice

    @api.depends('date', 'date_to')
    def _get_planned_duration(self):
        for rec in self:
            if rec.date and rec.date_to:
                diff = rec.date_to - rec.date
                planned_duration = (diff.days * 24) + (diff.seconds / 3600)
                if rec.planned_duration != planned_duration:
                    rec.planned_duration = planned_duration
                else:
                    rec.planned_duration = rec.manual_planned_duration

    @api.onchange('planned_duration')
    def _inverse_planned_duration(self):
        for rec in self:
            rec.manual_planned_duration = rec.planned_duration
            if rec.date:
                rec.date_to = rec.date + timedelta(hours=rec.planned_duration)

    @api.depends('waiting_date_start', 'waiting_date_end')
    def _compute_waiting_running_duration(self):
        for rec in self:
            if rec.waiting_date_start and rec.waiting_date_end:
                rec.waiting_duration_timer = round((rec.waiting_date_end - rec.waiting_date_start).total_seconds() / 60.0, 2)
            elif rec.waiting_date_start:
                rec.waiting_duration_timer = round((fields.Datetime.now() - rec.waiting_date_start).total_seconds() / 60.0, 2)
            else:
                rec.waiting_duration_timer = 0

    @api.depends('date_end', 'date_start')
    def _compute_consulataion_running_duration(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                rec.appointment_duration_timer = round((rec.date_end - rec.date_start).total_seconds() / 60.0, 2)
            elif rec.date_start:
                rec.appointment_duration_timer = round((fields.Datetime.now() - rec.date_start).total_seconds() / 60.0, 2)
            else:
                rec.appointment_duration_timer = 0

    @api.model
    def default_get(self, fields):
        res = super(MateAppointment, self).default_get(fields)
        if self._context.get('acs_department_type'):
            department = self.env[HR_DEPARTMENT].search([('department_type', '=', self._context.get('acs_department_type'))], limit=1)
            if department:
                res['department_id'] = department.id
        return res

    def _compute_field_value(self, field):
        if field.name == 'department_type':
            for rec in self:
                if rec.department_id and rec.department_id.id:
                    department = self.env[HR_DEPARTMENT].sudo().search([('id', '=', rec.department_id.id)])
                    rec.write({
                        'department_type': department.department_type
                    })
        else:
            super()._compute_field_value(field)

    def action_create_dental_invoice(self):
        pass

    def update_reminder_dates(self):
        for rec in self:
            if fields.Datetime.now() < rec.date:
                reminder_date = rec.date - timedelta(days=int(rec.company_id.mate_reminder_day)) - timedelta(hours=int(rec.company_id.mate_reminder_hours))
                if reminder_date >= fields.Datetime.now():
                    rec.reminder_date = reminder_date

    def update_appoinemtn_refering(self):
        for rec in self:
            if rec.refered_from_appointment_id and rec.refered_from_appointment_id.refered_to_appointment_id != rec:
                rec.refered_from_appointment_id.refered_to_appointment_id = rec.id

    @api.model
    def send_appointment_reminder(self):
        date_time_now = fields.Datetime.now()
        reminder_appointments = self.sudo().search([('acs_reminder_sent', '=', False), ('state', 'in', ['draft', 'confirm']), ('date', '>', fields.Datetime.now()), ('reminder_date', '<=', date_time_now)])
        if reminder_appointments:
            for reminder_appointment in reminder_appointments:
                reminder_appointment.acs_reminder_sent = True
        return reminder_appointments

    @api.onchange('department_id')
    def onchange_department(self):
        res = {}
        if self.department_id:
            physicians = self.env[self.MATE_HMS_PHYSICIAN].search([('department_ids', 'in', self.department_id.id)])
            res['domain'] = {'physician_id': [('id', 'in', physicians.ids)]}
            self.department_type = self.department_id.department_type
        return res

    @api.model_create_multi
    def create(self, vals_list):
        NEW_APPOINTMENT = 'New Appointment'
        for values in vals_list:
            if values.get('name', NEW_APPOINTMENT) == NEW_APPOINTMENT:
                values['name'] = self.env['ir.sequence'].next_by_code(MATE_APPOINTMENT) or NEW_APPOINTMENT
        res = super().create(vals_list)
        for record in res:
            record.update_reminder_dates()
            record.update_appoinemtn_refering()
        return res

    def write(self, values):
        res = super(MateAppointment, self).write(values)
        if 'follow_date' in values:
            self.sudo()._create_edit_followup_reminder()
        if 'date' in values:
            self.sudo().update_reminder_dates()
        if 'refered_from_appointment_id' in values:
            self.sudo().update_appoinemtn_refering()
        if 'consumable_line_ids' in values:
            self.update_amount_total()
        return res

    @api.onchange('consumable_line_ids')
    def update_amount_total(self):
        if self.consumable_line_ids:
            total = 0
            # Tính tổng tiền của những services được sử dụng
            for item in self.consumable_line_ids:
                total += item.qty * item.price_unit
            self.amount_total = total
        else:
            self.amount_total = 0

    @api.ondelete(at_uninstall=False)
    def _unlink_except_draft_or_cancel(self):
        for record in self:
            if record.state not in ('draft', 'cancel'):
                raise UserError(_("You can delete a record in draft or cancelled state only."))

    def print_report(self):
        return self.env.ref('mate_hms.action_appointment_report').report_action(self)

    def action_appointment_send(self):
        '''
        This function opens a window to compose an email, with the template message loaded by default
        '''
        self.ensure_one()
        template_id = self.env['ir.model.data']._xmlid_to_res_id('mate_hms.acs_appointment_email', raise_if_not_found=False)

        ctx = {
            'default_model': MATE_APPOINTMENT,
            'default_res_ids': self.ids,
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'force_email': True
        }
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    def acs_appointment_inv_product_data(self, with_product=True):
        product_data = []
        if with_product:
            product_id = self.product_id
            if not product_id:
                raise UserError(_("Please Set Consultation Service first."))

            product_data = [{'product_id': product_id}]

        if self.consumable_line_ids:
            product_data.append({
                'name': _("Consumed Product/services"),
            })
            for consumable in self.consumable_line_ids:
                product_data.append({
                    'product_id': consumable.product_id,
                    'quantity': consumable.qty,
                    'lot_id': consumable.lot_id and consumable.lot_id.id or False,
                    'product_uom_id': consumable.product_uom_id.id,
                })

        # ACS: Check if we need it or not as it is getting created in combined
        # invocie call by default. related method is also commented.
        if self._context.get('with_procedure'):
            if self.procedure_to_invoice_ids:
                product_data += self.procedure_to_invoice_ids.get_procedure_invoice_data()

        return product_data

    def acs_appointment_inv_data(self):
        return {
            'ref_physician_id': self.ref_physician_id and self.ref_physician_id.id or False,
            'physician_id': self.physician_id and self.physician_id.id or False,
            'appointment_id': self.id,
            'hospital_invoice_type': 'appointment',
        }

    def action_import_services_excel(self):
        self.ensure_one()
        action = self.env.ref('mate_hms.action_mate_hms_handle_consumed_services').read()[0]
        action['context'] = {
            'default_appointment_id': self.id
        }
        return action

    # Method to collect other related records data
    def acs_appointment_common_data(self, invoice_id):
        """
            Currently we are managing  follwoing related records invoicing:
            1> Procedures: that are already coverd in acs_appointment_inv_product_data and dene here also
            2> Pharmacy: done in pharmacy module
            3> Surgery: done in surgey module
            4> Laboratory: done in hms Laboratory module
            5> Radiology: done in hms Radiology module
        """
        # Procedure Invoicing
        data = self.procedure_to_invoice_ids.mate_hms_common_invoice_procedure_data(invoice_id)
        return data

    # mehtod to create invoice on related records like done in hospitalization
    def acs_appointment_common_invoicing(self, invoice_id):
        data = self.acs_appointment_common_data(invoice_id)
        # create Invoice lines only if invoice is passed
        if invoice_id:
            for line in data:
                self.with_context(acs_pricelist_id=self.pricelist_id.id).mate_hms_create_invoice_line(line, invoice_id)
        return data

    def get_appointment_product_data(self):
        return self.acs_appointment_inv_product_data()

    def create_invoice(self):
        inv_data = self.acs_appointment_inv_data()
        product_data = self.get_appointment_product_data()
        acs_context = {'commission_partner_id': self.physician_id.partner_id.id}
        if self.pricelist_id:
            acs_context.update({'acs_pricelist_id': self.pricelist_id.id})
        invoice = self.with_context(acs_context).mate_hms_create_invoice(partner=self.patient_id.partner_id, patient=self.patient_id, product_data=product_data, inv_data=inv_data)
        self.invoice_id = invoice.id
        self.acs_appointment_common_invoicing(invoice)
        if self.state == 'to_invoice':
            self.appointment_done()

        if self.state == 'draft' and not self._context.get('avoid_confirmation'):
            if self.invoice_id and not self.company_id.acs_check_appo_payment:
                self.appointment_confirm()

    def create_consumed_prod_invoice(self):
        if not self.consumable_line_ids:
            raise UserError(_("There is no consumed product to invoice."))

        inv_data = self.acs_appointment_inv_data()
        product_data = self.acs_appointment_inv_product_data(with_product=False)

        pricelist_context = {}
        if self.pricelist_id:
            pricelist_context = {'acs_pricelist_id': self.pricelist_id.id}
        invoice = self.with_context(pricelist_context).mate_hms_create_invoice(partner=self.patient_id.partner_id, patient=self.patient_id, product_data=product_data, inv_data=inv_data)
        self.consumable_invoice_id = invoice.id
        self.acs_appointment_common_invoicing(invoice)
        if self.state == 'to_invoice':
            self.appointment_done()

    def action_create_invoice_with_procedure(self):
        return self.with_context(with_procedure=True).create_invoice()

    def view_invoice(self):
        appointment_invoices = self.invoice_ids
        action = self.mate_hms_action_view_invoice(appointment_invoices)
        action['context'].update({'default_partner_id': self.patient_id.partner_id.id, 'default_patient_id': self.patient_id.id, 'default_appointment_id': self.id, 'default_ref_physician_id': self.ref_physician_id and self.ref_physician_id.id or False, 'default_physician_id': self.physician_id and self.physician_id.id or False, 'default_hospital_invoice_type': 'appointment', 'default_ref': self.name})
        return action

    def action_refer_doctor(self):
        action = self.env[self.IR_ACTIONS]._for_xml_id("mate_hms.action_appointment")
        action['domain'] = [('patient_id', '=', self.id)]
        action['context'] = {'default_patient_id': self.patient_id.id, 'default_physician_id': self.physician_id.id, 'default_refered_from_appointment_id': self.id}
        action['views'] = [(self.env.ref('mate_hms.view_hms_appointment_form').id, 'form')]
        return action

    def action_create_evaluation(self):
        action = self.env[self.IR_ACTIONS]._for_xml_id("mate_hms.action_acs_patient_evaluation_popup")
        action['domain'] = [('patient_id', '=', self.id)]
        action['context'] = {'default_patient_id': self.patient_id.id, 'default_physician_id': self.physician_id.id, 'default_appointment_id': self.id}
        return action

    @api.onchange('patient_id', 'date')
    def onchange_patient_id(self):

        if self.patient_id:
            self.age = self.patient_id.age
            followup_days = self.env.company.followup_days
            followup_day_limit = (datetime.now() - timedelta(days=followup_days)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            appointment_id = self.search([('patient_id', '=', self.patient_id.id), ('date', '>=', followup_day_limit), ('state', 'not in', ['cancel', 'draft'])])

            # Avoid setting physician if already there from treatment or manually selected.
            if not self.physician_id:
                self.physician_id = self.patient_id.primary_physician_id and self.patient_id.primary_physician_id.id
            if appointment_id and followup_days:
                self.consultation_type = 'followup'
                if self.env.company.followup_product_id:
                    self.product_id = self.env.company.followup_product_id.id
            else:
                self.consultation_type = 'consultation'

    @api.onchange('physician_id', 'department_id', 'consultation_type')
    def onchange_physician(self):

        product_id = False
        # ACS: First check configuration on department.
        if self.acs_department_id:
            # ACS: To avoid portal access error research department here.
            if self.consultation_type == 'followup':
                if self.acs_department_id.followup_service_id:
                    product_id = self.acs_department_id.followup_service_id.id

            elif self.acs_department_id.consultaion_service_id:
                product_id = self.acs_department_id.consultaion_service_id.id

        if self.physician_id:
            if self.consultation_type == 'followup':
                if self.physician_id.followup_service_id:
                    product_id = self.physician_id.followup_service_id.id

            elif self.physician_id.consultaion_service_id:
                product_id = self.physician_id.consultaion_service_id.id

            if self.physician_id.appointment_duration and not self._context.get('acs_online_transaction'):
                self.planned_duration = self.physician_id.appointment_duration

        if product_id:
            self.product_id = product_id

    def appointment_confirm(self):
        if (not self._context.get('acs_online_transaction')) and (not self.invoice_exempt):
            if self.appointment_invoice_policy == 'advance' and not self.invoice_id:
                raise UserError(_('Invoice is not created yet'))

            elif self.invoice_id and self.company_id.acs_check_appo_payment and self.payment_state not in ['in_payment', 'paid']:
                raise UserError(_('Invoice is not Paid yet.'))

        if not self.user_id:
            self.user_id = self.env.user.id

        if self.patient_id.email and (self.company_id.acs_auto_appo_confirmation_mail or self._context.get('acs_online_transaction')):
            template = self.env.ref('mate_hms.acs_appointment_email')
            template.sudo().send_mail(self.id, raise_exception=False)

        self.state = 'confirm'

    def appointment_waiting(self):
        self.state = 'waiting'
        self.waiting_date_start = datetime.now()
        self.waiting_duration = 0.1

    def appointment_consultation(self):
        if not self.waiting_date_start:
            raise UserError(('No waiting start time defined.'))
        datetime_diff = datetime.now() - self.waiting_date_start
        m, s = divmod(datetime_diff.total_seconds(), 60)
        h, m = divmod(m, 60)
        self.waiting_duration = float(('%0*d') % (2, h) + '.' + ('%0*d') % (2, m * 1.677966102))
        self.state = 'in_consultation'
        self.waiting_date_end = datetime.now()
        self.date_start = datetime.now()

    def action_pause(self):
        self.state = 'pause'
        self.pause_date_start = datetime.now()

        if self.date_start:
            datetime_diff = datetime.now() - self.date_start
            m, s = divmod(datetime_diff.total_seconds(), 60)
            h, m = divmod(m, 60)
            self.appointment_duration = float(('%0*d') % (2, h) + '.' + ('%0*d') % (2, m * 1.677966102)) - self.pause_duration
        self.date_end = datetime.now()

    def action_start_paused(self):
        self.state = 'in_consultation'
        self.pause_date_end = datetime.now()
        self.date_end = False
        datetime_diff = datetime.now() - self.pause_date_start
        m, s = divmod(datetime_diff.total_seconds(), 60)
        h, m = divmod(m, 60)
        self.pause_duration += float(('%0*d') % (2, h) + '.' + ('%0*d') % (2, m * 1.677966102))

    def consultation_done(self):
        if not self.date_end:
            if self.date_start:
                datetime_diff = datetime.now() - self.date_start
                m, s = divmod(datetime_diff.total_seconds(), 60)
                h, m = divmod(m, 60)
                self.appointment_duration = float(('%0*d') % (2, h) + '.' + ('%0*d') % (2, m * 1.677966102)) - self.pause_duration
        self.date_end = datetime.now()
        if (self.invoice_exempt or self.invoice_id) and not (self.consumable_line_ids and self.appointment_invoice_policy == 'advance' and not self.invoice_exempt and not self.consumable_invoice_id):
            self.appointment_done()
        else:
            self.state = 'to_invoice'
        if self.consumable_line_ids:
            self.consume_appointment_material()

        # Only create disease history if treatment is not linked.
        if not self.treatment_id:
            for disease in self.diseases_ids:
                self.env['mate_hms.patient.disease'].create({
                    'patient_id': self.patient_id.id,
                    'physician_id': self.physician_id.id,
                    'disease_id': disease.id,
                    'age': self.age,
                    'diagnosed_date': self.date,
                })

    def appointment_done(self):
        self.state = 'done'
        if self.company_id.sudo().auto_followup_days:
            self.follow_date = self.date + timedelta(days=self.company_id.sudo().auto_followup_days)

    def appointment_cancel(self):
        self.state = 'cancel'
        self.waiting_date_start = False
        self.waiting_date_end = False

        if self.sudo().invoice_id and self.sudo().invoice_id.state == 'draft':
            self.sudo().invoice_id.unlink()

    def appointment_draft(self):
        self.state = 'draft'

    def action_reopen(self):
        self.state = 'in_consultation'

    def action_prescription(self):
        action = self.env[self.IR_ACTIONS]._for_xml_id("mate_hms.act_open_hms_prescription_order_view")
        action['domain'] = [('appointment_id', '=', self.id)]
        action['context'] = {'default_patient_id': self.patient_id.id, 'default_physician_id': self.physician_id.id, 'default_diseases_ids': [(6, 0, self.diseases_ids.ids)], 'default_treatment_id': self.treatment_id and self.treatment_id.id or False, 'default_appointment_id': self.id}
        return action

    def button_pres_req(self):
        action = self.env[self.IR_ACTIONS]._for_xml_id("mate_hms.act_open_hms_prescription_order_view")
        action['domain'] = [('appointment_id', '=', self.id)]
        action['views'] = [(self.env.ref('mate_hms.view_hms_prescription_order_form').id, 'form')]
        action['context'] = {'default_patient_id': self.patient_id.id, 'default_physician_id': self.physician_id.id, 'default_diseases_ids': [(6, 0, self.diseases_ids.ids)], 'default_treatment_id': self.treatment_id and self.treatment_id.id or False, 'default_appointment_id': self.id}
        return action

    def action_view_treatment(self):
        action = self.env[self.IR_ACTIONS]._for_xml_id("mate_hms.acs_action_form_hospital_treatment")
        action['context'] = {'default_appointment_ids': [(6, 0, self.ids)], 'default_patient_id': self.patient_id.id, 'acs_current_appointment': self.id}
        action['views'] = [(self.env.ref('mate_hms.view_hospital_hms_treatment_form').id, 'form')]
        if self.treatment_id:
            action['domain'] = [('id', '=', self.treatment_id.id)]
            action['res_id'] = self.treatment_id.id
        elif self.patient_id.treatment_ids.filtered(lambda trt: trt.state in ['draft', 'runnig']):
            running_treatment_ids = self.patient_id.treatment_ids.filtered(lambda trt: trt.state in ['draft', 'runnig'])
            action['domain'] = [('id', 'in', running_treatment_ids.ids)]
            action['views'] = [(self.env.ref('mate_hms.view_acs_hms_treatment_appointment_tree').id, 'list')]
        return action

    def acs_get_consume_locations(self):
        if not self.company_id.appointment_usage_location_id:
            raise UserError(_('Please define a appointment location where the consumables will be used.'))
        if not self.company_id.appointment_stock_location_id:
            raise UserError(_('Please define a appointment location from where the consumables will be taken.'))

        dest_location_id = self.company_id.appointment_usage_location_id.id
        source_location_id = self.company_id.appointment_stock_location_id.id
        return source_location_id, dest_location_id

    def _consume_kit_product(self, line, source_location_id, dest_location_id):
        """Consume kit product materials and return move ids"""
        move_ids = []
        for kit_line in line.product_id.acs_kit_line_ids:
            if kit_line.product_id.tracking != 'none':
                raise UserError("In Consumable lines Kit product with component having lot/serial tracking is not allowed. Please remove such kit product from consumable lines.")
            move = self.consume_material(source_location_id, dest_location_id, {'product': kit_line.product_id, 'qty': kit_line.product_qty * line.qty})
            move.appointment_id = self.id
            move_ids.append(move.id)
        line.move_id = move.id
        line.move_ids = [(6, 0, move_ids)]
        return move_ids

    def _consume_single_product(self, line, source_location_id, dest_location_id):
        """Consume single product material and return the move"""
        move = self.consume_material(
            source_location_id,
            dest_location_id,
            {
                'product': line.product_id,
                'qty': line.qty,
                'lot_id': line.lot_id and line.lot_id.id or False
            }
        )
        move.appointment_id = self.id
        line.move_id = move.id
        return move

    def consume_appointment_material(self):
        for rec in self:
            source_location_id, dest_location_id = rec.acs_get_consume_locations()
            lines_to_process = rec.consumable_line_ids.filtered(lambda s: not s.move_id)

            for line in lines_to_process:
                if line.product_id.is_kit_product:
                    rec._consume_kit_product(line, source_location_id, dest_location_id)
                else:
                    rec._consume_single_product(line, source_location_id, dest_location_id)

    def action_view_patient_procedures(self):
        action = self.env[self.IR_ACTIONS]._for_xml_id("mate_hms.action_acs_patient_procedure")
        domain = [('appointment_ids', 'in', self.id)]
        if self.treatment_id:
            domain = ['|', ('treatment_id', '=', self.treatment_id.id)] + domain
        action['domain'] = domain
        action['context'] = {'default_treatment_id': self.treatment_id and self.treatment_id.id or False, 'default_appointment_ids': [(6, 0, [self.id])], 'default_patient_id': self.patient_id.id, 'default_physician_id': self.physician_id.id, 'default_department_id': self.department_id.id}
        return action

    def get_acs_kit_lines(self):
        if not self.acs_kit_id:
            raise UserError("Please Select Kit first.")

        lines = []
        for line in self.acs_kit_id.acs_kit_line_ids:
            lines.append((0, 0, {
                'product_id': line.product_id.id,
                'product_uom_id': line.product_id.uom_id.id,
                'qty': line.product_qty * self.acs_kit_qty,
            }))
        self.consumable_line_ids = lines

    # Create/Edit Followup activity if needed
    def _create_edit_followup_reminder(self):
        activity = self.env['mail.activity']
        default_activity_type = self.env['mail.activity.type'].search([], limit=1)
        res_model = self.env['ir.model'].sudo().search([('model', '=', self._name)])
        for rec in self:
            if rec.follow_date:
                company = rec.company_id.sudo() or self.env.company.sudo()
                activity_type = company.mate_hms_followup_activity_type_id or default_activity_type
                if not activity_type:
                    raise UserError(_("Please Set Followup activity Type on Configiration."))

                followup_date = rec.follow_date - timedelta(days=1)
                if not rec.user_id:
                    rec.user_id = self.env.user.id
                user_id = rec.user_id

                existing_activity = activity.search([('res_id', '=', rec.id), ('res_model_id', '=', self._name), ('activity_type_id', '=', activity_type.id), ('user_id', '=', user_id.id)])
                if existing_activity:
                    existing_activity.date_deadline = followup_date
                else:
                    activity_vals = {
                        'res_id': rec.id,
                        'res_model_id': res_model.id,
                        'activity_type_id': activity_type.id,
                        'summary': _('Appointment Follow up'),
                        'date_deadline': followup_date,
                        'automated': True,
                        'user_id': user_id.id
                    }
                    self.env['mail.activity'].with_context(mail_activity_quick_update=True).create(activity_vals)

    def cancel_old_appointments(self):
        yesterday = fields.Datetime.now().replace(hour=0, minute=0, second=0)
        if self.env.user.sudo().company_id.mate_cancel_old_appointment:
            previous_appointments = self.env[MATE_APPOINTMENT].search([('date', '<=', yesterday), ('state', 'in', ['draft', 'confirm'])])
            for appointment in previous_appointments:
                appointment.with_context(cancel_from_cron=True).appointment_cancel()
        return

    def acs_reschedule_appointments(self, reschedule_time):
        for rec in self:
            rec.date = rec.date + timedelta(hours=reschedule_time)
            rec.date_to = rec.date_to + timedelta(hours=reschedule_time)


class StockMove(models.Model):
    _inherit = "stock.move"

    appointment_id = fields.Many2one(MATE_APPOINTMENT, string="Appointment", ondelete="restrict")
