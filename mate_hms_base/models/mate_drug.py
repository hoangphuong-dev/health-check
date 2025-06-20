from odoo import fields, models


class MateFlavour(models.Model):
    _name = 'mate_hms.medicament.flavour'
    _description = "Medicament Flavour"

    name = fields.Char(required=True, translate=True)

    _sql_constraints = [
        ('name_mate_medi_flavour_uniq', 'unique (name)', 'The name of the Content must be unique !'),
    ]


class MateDrugForm(models.Model):
    _name = 'mate_hms.drug.form'
    _description = "Drug Form"

    code = fields.Char()
    name = fields.Char(string='Form', required=True, translate=True)

    _sql_constraints = [('name_uniq', 'UNIQUE(name)', 'Name must be unique!')]


class MateActiveComp(models.Model):
    _name = 'mate_hms.active.comp'
    _description = "Drug Active Component"

    name = fields.Char(string='Active Component', required=True, translate=True)
    amount = fields.Float(string='Amount of component', help='Amount of component used in the drug (eg, 250 mg) per dose')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')


class MateDrugCompany(models.Model):
    _name = 'mate_hms.drug.company'
    _description = "Drug Company"

    name = fields.Char(string='Company Name', required=True, translate=True)
    code = fields.Char()
    partner_id = fields.Many2one('res.partner', 'Partner', ondelete='restrict')
    active = fields.Boolean(string="Active", default=True)


class MateDrugRoute(models.Model):
    _name = 'mate_hms.drug.route'
    _description = "Drug Route"

    code = fields.Char()
    name = fields.Char(string='Name', required=True, translate=True)

    _sql_constraints = [('name_uniq', 'UNIQUE(name)', 'Name must be unique!')]
