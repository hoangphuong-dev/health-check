from odoo import api, fields, models
MATE_HMS_PHYSICIAN = 'mate_hms.physician'


class ResPartner(models.Model):
    _inherit = "res.partner"
    is_referring_doctor = fields.Boolean(string="Is Refereinng Physician")
    # Mate Note: Adding assignee as relation with partner for receptionist or Doctor to access only those patients assigned to them
    assignee_ids = fields.Many2many('res.partner', 'mate_partner_asignee_relation', 'partner_id', 'assigned_partner_id', 'Assignees', help='Assigned partners for receptionist or doctor etc to see the records')


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.depends('physician_ids')
    def _compute_physician_count(self):
        for user in self.with_context(active_test=False):
            user.physician_count = len(user.physician_ids)

    def _compute_patient_count(self):
        patient = self.env['mate_hms.patient']
        for user in self.with_context(active_test=False):
            user.patient_count = patient.search_count([('partner_id', '=', user.partner_id.id)])

    department_ids = fields.Many2many('hr.department', 'user_department_rel', 'user_id', 'department_id', domain=[('patient_department', '=', True)], string='Departments')
    physician_count = fields.Integer(string="# Physician", compute="_compute_physician_count")
    physician_ids = fields.One2many(MATE_HMS_PHYSICIAN, 'user_id', string='Related Physician')
    patient_count = fields.Integer(string="# Patient", compute="_compute_patient_count")

    # Mate NOTE: On changing the department clearing the cache for the access rights and record rules
    def write(self, values):
        if 'department_ids' in values:
            self.env['ir.model.access'].call_cache_clearing_methods()
        return super(ResUsers, self).write(values)

    @property
    def SELF_READABLE_FIELDS(self):
        user_fields = ['department_ids', 'physician_count', 'physician_ids', 'patient_count']
        return super().SELF_READABLE_FIELDS + user_fields

    @property
    def SELF_WRITEABLE_FIELDS(self):
        user_fields = ['department_ids', 'physician_count', 'physician_ids', 'patient_count']
        return super().SELF_WRITEABLE_FIELDS + user_fields

    def action_create_physician(self):
        self.ensure_one()
        self.env[MATE_HMS_PHYSICIAN].create({
            'user_id': self.id,
            'name': self.name,
        })

    def action_create_patient(self):
        self.ensure_one()
        self.env['mate_hms.patient'].create({
            'partner_id': self.partner_id.id,
            'name': self.name,
        })


class HospitalDepartment(models.Model):
    _inherit = 'hr.department'

    note = fields.Text('Note')
    patient_department = fields.Boolean("Patient Department", default=True)
    appointment_ids = fields.One2many("mate_hms.appointment", "department_id", "Appointments")
    department_type = fields.Selection([('general', 'General')], string="Hospital Department")
    consultaion_service_id = fields.Many2one('product.product', ondelete='restrict', string='Consultation Service')
    followup_service_id = fields.Many2one('product.product', ondelete='restrict', string='Followup Service')
    image = fields.Binary(string='Image')


class MateEthnicity(models.Model):
    _description = "Ethnicity"
    _name = 'mate.ethnicity'

    name = fields.Char(string='Name', required=True, translate=True)
    code = fields.Char(string='Code')
    notes = fields.Char(string='Notes')

    _sql_constraints = [('name_uniq', 'UNIQUE(name)', 'Name must be unique!')]


class MateMedicalAlert(models.Model):
    _name = 'mate_hms.medical.alert'
    _description = "Medical Alert for Patient"

    name = fields.Char(required=True)
    description = fields.Text('Description')


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    birthday = fields.Date('Date of Birth')


class MateFamilyRelation(models.Model):
    _name = 'mate.family.relation'
    _description = "Family Relation"
    _order = "sequence"

    name = fields.Char(required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    inverse_relation_id = fields.Many2one("mate.family.relation", string="Inverse Relation")

    def _compute_display_name(self):
        for rec in self:
            name = rec.name
            if rec.inverse_relation_id:
                name += ' - ' + rec.inverse_relation_id.name
            rec.display_name = name

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The Relation must be unique!')
    ]

    def manage_inverser_relation(self):
        for rec in self:
            if rec.inverse_relation_id and not rec.inverse_relation_id.inverse_relation_id:
                rec.inverse_relation_id.inverse_relation_id = rec.id

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for record in res:
            record.manage_inverser_relation()
        return res

    def write(self, values):
        res = super(MateFamilyRelation, self).write(values)
        self.manage_inverser_relation()
        return res


class product_template(models.Model):
    _inherit = "product.template"

    hospital_product_type = fields.Selection(selection_add=[('procedure', 'Procedure'), ('consultation', 'Consultation')])
    common_dosage_id = fields.Many2one('medicament.dosage', ondelete='cascade', string='Frequency', help='Drug form, such as tablet or gel')
    manual_prescription_qty = fields.Boolean("Manual Prescription Qty")
    procedure_time = fields.Float("Procedure Time")
    appointment_invoice_policy = fields.Selection([('at_end', 'Invoice in the End'), ('anytime', 'Invoice Anytime'), ('advance', 'Invoice in Advance')], string="Appointment Invoicing Policy")
    mate_allow_substitution = fields.Boolean(string='Allow Substitution')


class MateConsumableLine(models.Model):
    _inherit = "mate_hms.consumable.line"

    appointment_id = fields.Many2one('mate_hms.appointment', ondelete="cascade", string='Appointment')
    procedure_id = fields.Many2one('mate_hms.patient.procedure', ondelete="cascade", string="Procedure")
    move_ids = fields.Many2many('stock.move', 'consumable_line_stock_move_rel', 'move_id', 'consumable_id', 'Kit Stock Moves', readonly=True)
    # Mate: In case of kit moves set move_ids but add move_id also. Else it may lead to comume material process again.


class Physician(models.Model):
    _inherit = MATE_HMS_PHYSICIAN

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for record in res:
            record.groups_id = [(4, self.env.ref('mate_hms.group_hms_jr_doctor').id)]
        return res
