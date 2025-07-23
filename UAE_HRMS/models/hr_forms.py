# -*- coding: utf-8 -*-
from odoo import api, fields, models


class hr_forms(models.Model):  
    _name = 'hr.forms'
    _inherit = 'mail.thread'
    
    def _get_employee_id(self):
        employee_rec = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)        
        if employee_rec:
            return employee_rec[0].id
    
    
    name = fields.Char(string='Name', copy=False)
    type = fields.Selection([('passport', 'PASSPORT REQUISITION'),
                                 ('incentive', 'INCENTIVE REQUEST'),
                                 ('bank_letter', 'Bank Letter'),], 'Form Type')
    state = fields.Selection([('draft', 'New'),('to_approve', 'To Approve'),
                              ('rejected', 'Rejected'),
                              ('approved', 'Approved'), ('returned', 'Returned')], 
                              'Status', default="draft", track_visibility='onchange')
    employee_name = fields.Many2one('hr.employee', string='Name', default=_get_employee_id)
    
    #Passport Form
    
    p_to = fields.Many2one('res.users', string='To')
    p_date = fields.Date('Date')
    p_designation_dept = fields.Many2one('hr.job', string='Designation')
    p_nationality = fields.Many2one('res.country', string='Nationality')
    p_release_form = fields.Date('From')
    p_release_to = fields.Date('To')
    p_days = fields.Float(string='Days')
    p_purpose = fields.Selection([('annual_leave', 'Annual  Leave'),
                                 ('emergency_leave', 'Emergency Leave'),
                                 ('renewal', 'Renewal'),
                                 ('others', 'Others')], 'Purpose')
    
    p_passport_no = fields.Char(string='Passport No')
    p_issued_date = fields.Date('Issued Date')
    p_returned_date = fields.Date('Returned date')
    
    # INCENTIVE
    
    
    i_date = fields.Date('Date')
    i_position = fields.Many2one('hr.job', string='Position')
    i_joining_date = fields.Date('Joining Date')
    i_remarks = fields.Text("Remarks")
    i_lines= fields.One2many('hr.forms.incentive', 'form_id', string='Lines')

    #Bank Letter
    b_date = fields.Date('Date')
    b_to = fields.Char("To")
    b_manager = fields.Char("Manager")
    b_bank_name = fields.Char("Bank Name")
    b_bank_address = fields.Char("Bank Address")
 
    
    b_joining_date = fields.Date('Joining Date')
    b_position = fields.Many2one('hr.job', string='Position')
    b_salary = fields.Float(string='Salary', default=0.0)
    b_account_number = fields.Char(string='Account Number')
    
    
    @api.onchange('employee_name')
    def employee_onchnage(self):
        for form in self:
            #form.p_nationality = form.employee_name.country_id and form.employee_name.country_id.id
            print("employee_rec=================================",form.employee_name.id)
            if form.employee_name:
                employee_name = self.env['hr.employee'].sudo().search([('id', '=', form.employee_name.id)])
                form.i_position = employee_name.job_id and employee_name.job_id.id
                form.i_joining_date = employee_name.date_of_join
                
                form.p_designation_dept = employee_name.job_id and employee_name.job_id.id
                
                form.b_position = employee_name.job_id and employee_name.job_id.id
                form.b_joining_date = employee_name.date_of_join
                form.b_account_number = employee_name.bank_account_id and employee_name.bank_account_id.acc_number
                if employee_name.bank_account_id and employee_name.bank_account_id.bank_id:
                    form.b_bank_name = employee_name.bank_account_id.bank_id.name
                
                contract_ids = self.env['hr.contract'].sudo().search([('employee_id','=',form.employee_name.id)], order='date_start desc', limit=1)
                if contract_ids:
                    form.b_salary = contract_ids[0].wage
        
    
    
    @api.onchange('p_release_form', 'p_release_to')
    def compute_employee_working_days(self):
        for form in self:
            if form.p_release_form and form.p_release_to:
                from_dt = fields.Datetime.from_string(form.p_release_form)
                to_dt = fields.Datetime.from_string(form.p_release_to)
                diff = to_dt - from_dt
                form.p_days = diff.days + 1
    
    
    def submit(self):
        self.name = self.env['ir.sequence'].next_by_code('hr.form.seq')
        self.state = 'to_approve'
        
   
    def approved(self):
        self.state = 'approved'
        
    
    def returned(self):
        self.state = 'returned'
        
        
class hr_forms_incentive(models.Model):  
    _name = 'hr.forms.incentive'
    
    form_id = fields.Many2one('hr.forms', string='Form Id')
    details = fields.Char(string='Details')
    description = fields.Char(string='Description')
    date = fields.Date('Date')
    amount = fields.Float(string='Amount (AED)')
    
    
    
    

