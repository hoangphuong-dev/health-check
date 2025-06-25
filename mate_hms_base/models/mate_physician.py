from odoo import api, fields, models


class MatePhysicianSpecialty(models.Model):
    _name = 'mate_hms.physician.specialty'
    _description = "Physician Specialty"

    code = fields.Char(string='Code')
    name = fields.Char(string='Specialty', required=True, translate=True)

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Name must be unique!'),
    ]


class MatePhysicianDegree(models.Model):
    _name = 'mate_hms.physician.degree'
    _description = "Physician Degree"

    name = fields.Char(string='Degree')

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Name must be unique!'),
    ]


class MatePhysician(models.Model):
    _name = 'mate_hms.physician'
    _description = "Physician"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _inherits = {'res.users': 'user_id'}

    user_id = fields.Many2one('res.users', string='Related User', required=True, ondelete='cascade', help='User-related data of the physician')
    code = fields.Char(string='Physician Code', default='/', tracking=True)
    degree_ids = fields.Many2many('mate_hms.physician.degree', 'physician_rel_education', 'physician_ids', 'degree_ids', string='Degree')
    specialty_id = fields.Many2one('mate_hms.physician.specialty', ondelete='set null', string='Specialty', help='Specialty Code', tracking=True)
    medical_license = fields.Char(string='Medical License', tracking=True)
    is_portal_user = fields.Boolean("Is Portal User")

    # define company to make company optional
    company_id = fields.Many2one('res.company', string='Hospital', context={'user_preference': True})

    def mate_make_dr_portal_user(self):
        group_portal = self.env.ref('base.group_portal')
        for rec in self:
            if rec.is_portal_user:
                rec.user_id.write({'groups_id': [(6, 0, [group_portal.id])]})

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get('code', '/') == '/':
                values['code'] = self.env['ir.sequence'].next_by_code('mate_hms.physician')
            if values.get('email'):
                values['login'] = values.get('email')
            # MATE: It creates issue in physican creation
            if values.get('user_ids'):
                values.pop('user_ids')

        res = super(MatePhysician, self).create(vals_list)
        res.mate_make_dr_portal_user()
        return res

    def write(self, values):
        res = super(MatePhysician, self).write(values)
        if 'is_portal_user' in values:
            self.mate_make_dr_portal_user()
        return res
