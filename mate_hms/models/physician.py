from odoo import fields, models


class Physician(models.Model):
    _inherit = 'mate_hms.physician'
    IR_ACTIONS = "ir.actions.actions"

    def _phy_rec_count(self):
        treatment = self.env['hms.treatment']
        appointment = self.env['mate_hms.appointment']
        prescription = self.env['prescription.order']
        patient = self.env['mate_hms.patient']
        for record in self.with_context(active_test=False):
            record.treatment_count = treatment.search_count([('physician_id', '=', record.id)])
            record.appointment_count = appointment.search_count([('physician_id', '=', record.id)])
            record.prescription_count = prescription.search_count([('physician_id', '=', record.id)])
            record.patient_count = patient.search_count(['|', ('primary_physician_id', '=', record.id), ('assignee_ids', 'in', record.partner_id.id)])

    consultaion_service_id = fields.Many2one('product.product', ondelete='restrict', string='Consultation Service')
    followup_service_id = fields.Many2one('product.product', ondelete='restrict', string='Followup Service')
    appointment_duration = fields.Float('Default Consultation Duration', default=0.25)

    is_primary_surgeon = fields.Boolean(string='Primary Surgeon')
    signature = fields.Binary('Signature')
    hr_presence_state = fields.Selection(related='user_id.employee_id.hr_presence_state')
    appointment_ids = fields.One2many("mate_hms.appointment", "physician_id", "Appointments")

    treatment_count = fields.Integer(compute='_phy_rec_count', string='# Treatments')
    appointment_count = fields.Integer(compute='_phy_rec_count', string='# Appointment')
    prescription_count = fields.Integer(compute='_phy_rec_count', string='# Prescriptions')
    patient_count = fields.Integer(compute='_phy_rec_count', string='# Patients')

    def action_treatment(self):
        action = self.env[self.IR_ACTIONS]._for_xml_id("mate_hms.mate_action_form_hospital_treatment")
        action['domain'] = [('physician_id', '=', self.id)]
        action['context'] = {'default_physician_id': self.id}
        return action

    def action_appointment(self):
        action = self.env[self.IR_ACTIONS]._for_xml_id("mate_hms.action_appointment")
        action['domain'] = [('physician_id', '=', self.id)]
        action['context'] = {'default_physician_id': self.id}
        return action

    def action_prescription(self):
        action = self.env[self.IR_ACTIONS]._for_xml_id("mate_hms.act_open_hms_prescription_order_view")
        action['domain'] = [('physician_id', '=', self.id)]
        action['context'] = {'default_physician_id': self.id}
        return action

    def action_patients(self):
        action = self.env[self.IR_ACTIONS]._for_xml_id("mate_hms_base.action_patient")
        action['domain'] = ['|', ('primary_physician_id', '=', self.id), ('assignee_ids', 'in', self.partner_id.id)]
        return action
