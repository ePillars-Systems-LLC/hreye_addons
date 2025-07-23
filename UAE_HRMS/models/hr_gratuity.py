# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: eP System
#    Copyright 2017 ePillars Systems LLC
#
##############################################################################

import re
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo import tools, _
from odoo.exceptions import UserError, ValidationError


#=====================================================
# Gratuity Settlement
#=====================================================
class hr_gratuity(models.Model):  
    _name = 'hr.gratuity'
    _rec_name = 'employee_id'
    _description = 'Gratuity Settlement'
    _inherit = ['mail.thread']
    
    @api.model
    def _get_employee_ids(self):
        employees=[]        
        hr_resignation_obj = self.env['hr.resignation'].search([],order='id desc')
        for record in hr_resignation_obj:
            employees.append(record.employee_id.id)
        return "[('id', 'in', %s)]" % (employees)
    
    def compute_show_approval(self):
        for rec in self:
            if rec.approval_required_from and rec.approval_required_from == self.env.user:
                rec.show_approval = True
            else:
                rec.show_approval = False
    
    def compute_is_approver(self):
        for rec in self:
            matrix_line = self.env['approval.matrix.line'].search([('matrix_id.type','=','grauity'),('user_id','=',self.env.uid)])
            if matrix_line:
                rec.is_approver = True
            else:
                rec.is_approver = False
    #=====================================================
    # Fields defined
    #=====================================================
    employee_id = fields.Many2one('hr.employee', string='Employee')
    last_working_date = fields.Date('Last Working Date')
    type= fields.Selection([('resignation', 'Resignation'),('termination','Termination')],string='Resignation/Termination')
    total_days= fields.Integer('Total Days')
    amount= fields.Integer('Amount')
    gratuity_line_ids= fields.One2many('hr.gratuity.line', 'gratuity_id', string='Gratuity Lines')
    gratuity_extra_lines= fields.One2many('hr.gratuity.extra', 'gratuity_id', string='Gratuity Additional Lines')
    contract_type = fields.Selection([('limited', 'Limited'),('unlimited','Unlimited')],string='Contract Type')
    date_of_join = fields.Date('Date of Joining')
    probation_end_date = fields.Date('Probation End Date')
    contract_id = fields.Many2one('hr.contract', string='Contract')
    benefits = fields.Selection([('with', 'With Benefit'),('without','Without Benefits')],string='Benefits')
    basic_salary= fields.Integer('Basic Salary')
    hra = fields.Integer('HRA')
    remaining_annual_leaves = fields.Float(string='Remaining Annual Leave')
    leave_salary= fields.Float('Leave Salary')
    unpaid_leaves = fields.Float('Unpaid Leaves', track_visibility='onchange')
    daily_salary = fields.Float('Daily (Basic Salary x 12/365)', track_visibility='onchange')
    total_days = fields.Float('Total Days (Joining Date - Last Working)', track_visibility='onchange')
    worked_days = fields.Float('Worked Days (Total Days - Unpaid Leaves)', track_visibility='onchange')
    worked_years = fields.Float('Worked Years (Worked Days/365)', track_visibility='onchange')
    
    gratuity_amount = fields.Float(compute='_get_values', string='Gratuity Amount')
    total_allowances = fields.Float(compute='_get_values', string='Allowances')
    total_deductions = fields.Float(compute='_get_values', string='Deductions')
    final_settlement_amount = fields.Float(compute='_get_values', string='Final Settlement Amount')
    
    #Accouting deatils
    expense_account_id = fields.Many2one('account.account', string="Expense Account")
    gratuity_account_id = fields.Many2one('account.account', string="Gratuity Account")
    journal_id = fields.Many2one('account.journal', string="Journal")
    move_id = fields.Many2one('account.move', string="Move")
    
    
    
    state= fields.Selection([
        ('draft', 'Draft'),
        ('to_approve','To Approve'),
        ('approved','Approved'),
        ('post', 'Posted'),
        ('rejected','Rejected'),
        ('cancelled', 'Cancelled'),
        ], string='Status', track_visibility='onchange',default='draft')
    approval_required_from = fields.Many2one('res.users', string='Waiting for Approval from',track_visibility='onchange')
    show_approval = fields.Boolean(compute='compute_show_approval')
    approval_order = fields.Float("Approval Order")
    is_approver = fields.Boolean('Is approver', compute='compute_is_approver')
    

    _sql_constraints = [
        ('employee_id_uniq', 'unique(employee_id)', "You cannot have multiple gratuity settlement records for the same Employee"),
    ]

    @api.onchange('employee_id')
    def get_last_working_date(self):
        resgination = self.env['hr.resignation'].search([('employee_id', '=', self.employee_id.id), 
                                                         ('state', '=', 'approved')], limit=1)
        if resgination:
            self.last_working_date = resgination.expected_revealing_date
            self.type = resgination.relieving_type
        else:
            self.type = 'termination'
        self.date_of_join = self.employee_id.date_of_join
        self.contract_type = self.employee_id.contract_type
        self.probation_end_date = self.employee_id.probation_end_date
        contract_ids = self.env['hr.contract'].search([('employee_id','=',self.employee_id.id)], order='date_start desc', limit=1)
        if contract_ids:
            self.contract_id = contract_ids[0].id
            self.basic_salary = contract_ids[0].basic
            self.hra = contract_ids[0].hra
        
    
    @api.onchange('gratuity_line_ids', 'gratuity_extra_lines')
    def _get_values(self):
        for record in self:
            gratuity_amount = 0.0
            other_allowances = 0.0
            other_deductions = 0.0
            if record.gratuity_line_ids:
                for lines1 in record.gratuity_line_ids:
                    gratuity_amount += lines1.amount
                    
            if record.gratuity_extra_lines:
                for lines2 in record.gratuity_extra_lines:
                    if lines2.type == "deduction":
                        other_deductions = other_deductions + lines2.amount
                    else:
                        other_allowances = other_allowances + lines2.amount
                        
                        
                      
            record.gratuity_amount = gratuity_amount
            record.total_allowances = other_allowances
            record.total_deductions = other_deductions
            record.final_settlement_amount = gratuity_amount + other_allowances - other_deductions
            
    def find_on_probation(self):
        if self.last_working_date > self.probation_end_date:
            return False
        return True
    
    def find_worked_years(self):
        from datetime import datetime
        from dateutil import relativedelta
        diff =  self.last_working_date - self.date_of_join
        days = diff.days + 1
        self.total_days = days
        if self.unpaid_leaves:
            days = days - self.unpaid_leaves
        self.worked_days = days
        years = days/365
        self.worked_years = years
        #years = round(years, 2)
        #years = years - years % 0.01
        return {'days' : days, 'years' : years}


    # @api.model
    # def create(self,vals):
    #     matrix = self.env['approval.matrix'].sudo().search([('type', '=', 'gratuity')])
    #     user = False
    #     order = False
    #     if matrix:
    #         line = self.env['approval.matrix.line'].sudo().search([
    #             ('matrix_id', '=', matrix.id)], order='approval_order asc', limit=1)[0]
    #         user = line.user_id.id if line else False
    #         order = line.approval_order if line else False
    #     else:
    #         raise UserError("Approval sequence not set, Please contact HR Manager!")
    #     vals['approval_required_from'] = user
    #     vals['approval_order'] = order
    #     vals['state'] = 'to_approve'
    #     res = super(hr_gratuity, self).create(vals)
    #     return res
    def sent_for_approval(self):
        matrix = self.env['approval.matrix'].sudo().search([('type', '=', 'gratuity')])
        user = False
        order = False
        if matrix:
            line = self.env['approval.matrix.line'].sudo().search([
                ('matrix_id', '=', matrix.id)], order='approval_order asc', limit=1)[0]
            user = line.user_id.id if line else False
            order = line.approval_order if line else False
            if user:
                # user_id = self.env['res.users'].browse(user)
                if user:
                    mail_content = "Please approve gratuity form %s" % self.employee_id.name
                    user_id = self.env['res.users'].browse(user)
                    email_to = "%s" % ';'.join(map(str, [user_id.email]))

                    main_content = {
                        'subject': _('Gratuity Form-%s') % (self.employee_id.name),
                        'author_id': self.env.user.partner_id.id,
                        'body_html': mail_content,
                        'email_to': email_to,
                    }
                    self.env['mail.mail'].create(main_content).send()
        else:
            raise UserError("Approval sequence not set, Please contact HR Manager!")
        self.approval_required_from = user
        self.approval_order = order
        self.state = 'to_approve'

    def find_next_approver(self, type, current_approver, current_approval_order):
        matrix = self.env['approval.matrix'].sudo().search([('type', '=', type)])
        if matrix and matrix.lines:
            matrix_lines = self.env['approval.matrix.line'].search(
                [('approval_order', '>', current_approval_order), ('matrix_id', '=', matrix.id)],
                order='approval_order asc', limit=1)
            if matrix_lines:
                line = matrix_lines[0]
                approval_user = line.user_id
                approval_order = line.approval_order
                return (approval_user, approval_order)
        return (False, False)

    def button_rejected(self):
        self.state = 'rejected'
        self.approval_required_from = False

    def set_to_draft(self):
        self.state = 'draft'
    
    def button_approved(self):

        user, order = self.find_next_approver('gratuity', self.approval_required_from, self.approval_order)
        if not user:
            self.write({'state': 'approved'})
            self.approval_required_from = False
        else:

            mail_content = "Please approve gratuity form %s" % self.employee_id.name
            # user_id = self.env['res.users'].browse(user)
            email_to = "%s" % ';'.join(map(str, [user.email]))

            main_content = {
                'subject': _('Gratuity Form-%s') % (self.employee_id.name),
                'author_id': self.env.user.partner_id.id,
                'body_html': mail_content,
                'email_to': email_to,
            }
            self.env['mail.mail'].create(main_content).send()
            self.write({'approval_required_from': user.id, 'approval_order': order})

    def calculate_gratuity_amount(self, days, years, type="full"):
        gratuity_amount = 0.00
        per_day_salary = self.daily_salary
        print("per_day_salary ==>> ", per_day_salary)
        print("days ==>> ", days)
        per_month_gratuity = per_day_salary * days
        print("per_month_gratuity ==>> ", per_month_gratuity)
        print("type ==>> ", type)
        
        if type == "full":
            per_month_gratuity = per_month_gratuity * 1
        
        if type == "1/3":
            per_month_gratuity = per_month_gratuity * 0.333333333
            
        if type == "2/3":
            per_month_gratuity = per_month_gratuity * 0.666666667
        
        
        gratuity_amount = per_month_gratuity * years
        print("years ==>> ", years)
        print("gratuity_amount ==>> ", gratuity_amount)


        
        return gratuity_amount
    
    def limited_resignation(self, on_probation, worked_days, worked_year, air_ticket):


        if on_probation:
            print ("No benefits")
            return {"gratuity_amount" : 0.00}
        
        if worked_year < 1.01:
            print ('''Employee is not entitled to any gratuity pay.
                      Annual leave salary of 2 days per month and Air Ticket Allowance will be provided.
                      Deduction of 1 month gross salary.''')
            extra_lines = [{'name' : 'Leave salary',
                            'amount' : self.leave_salary,
                            'type' : 'allowance'}]
            return {"gratuity_amount" : 0.00, 'extra_lines' : extra_lines}
        
        if worked_year > 1 and worked_year < 3.01:
            print ('''Employee is not entitled to any gratuity pay.
                        Annual leave salary of 2.5 days per month and Air Ticket Allowance will be provided.
                        Deduction of 1 month gross salary.''')
            gratuity_amount = self.calculate_gratuity_amount(21, worked_year, type="full")
            extra_lines = [{'name' : 'Leave salary',
                            'amount' : self.leave_salary,
                            'type' : 'allowance'}]
            return {"gratuity_amount" :gratuity_amount, 'extra_lines' : extra_lines}
            
        
        if worked_year > 3 and worked_year < 5.01:
            print (''' Employee is entitled to full gratuity pay based on 21 days salary for each year of work.
                        Annual leave salary of 2.5 days per month and Air Ticket Allowance will be provided.
                        Deduction of 1 month gross salary''')
            gratuity_amount = self.calculate_gratuity_amount(21, worked_year, type="full")
            extra_lines = [{'name' : 'Leave salary',
                            'amount' : self.leave_salary,
                            'type' : 'allowance'}]
            return {"gratuity_amount" : gratuity_amount, 'extra_lines' : extra_lines}
            
        if worked_year > 5:
            print ('''Employee is entitled to full gratuity pay based on 21 days for the first five years and 30 days for the remaining
                        years for each year of work.
                        Annual leave salary of 2.5 days per month and Air Ticket Allowance will be provided.
                        Deduction of 1 month gross salary''')
            
            gratuity_amount = self.calculate_gratuity_amount(21, 5.00, type="full")
            reamaing_years = worked_year - 5.00
            gratuity_amount = gratuity_amount + self.calculate_gratuity_amount(30, reamaing_years, type="full")
            extra_lines = [{'name' : 'Leave salary',
                            'amount' : self.leave_salary,
                            'type' : 'allowance'}]
            return {"gratuity_amount" : gratuity_amount, 'extra_lines' : extra_lines}
            
    
    def limited_termination_with_benefits(self, on_probation, worked_days, worked_year, air_ticket):
        if on_probation:
            print ("Airticket Allowance for One Way")
            extra_lines = []
            return {"gratuity_amount" : 0.00, 'extra_lines' : extra_lines}
        
        if worked_year < 1.01:
            print ('''Eligible for Leave Salary and Airticket Allowance. 
                      Employees are entitled to an annual leave of 2 days per month''')
            extra_lines = [ {'name' : 'Leave salary',
                            'amount' : self.leave_salary,
                            'type' : 'allowance'}]
            return {"gratuity_amount" : 0.00, 'extra_lines' : extra_lines}
        
        if worked_year > 1 and on_probation:
            print ("Then he will be entitled to Gratuity Pay + 1 month Gross Salary + Leave Salary and Air ticket.")
            gratuity_amount = self.calculate_gratuity_amount(21, worked_year, type="full")
            
            extra_lines = [{'name' : 'Leave salary',
                            'amount' : self.leave_salary,
                            'type' : 'allowance'}]
            return {"gratuity_amount" : gratuity_amount, 'extra_lines' : extra_lines}
            
        
        if worked_year > 1 and worked_year < 5.01:
            print ('''full gratuity pay based on 21 days salary for each year of work, 
                      one month salary + leave salary and Air ticket''')
            gratuity_amount = self.calculate_gratuity_amount(21, worked_year, type="full")
            
            
            extra_lines = [{'name' : 'Leave salary',
                            'amount' : self.leave_salary,
                            'type' : 'allowance'}]
            return {"gratuity_amount" : gratuity_amount, 'extra_lines' : extra_lines}
            
        if worked_year > 5:
            print ('''full gratuity of 21 days salary for the first five
                    years and 30 days' for the remaining years, leave salary, ticket and one month salary''')
            
            gratuity_amount = self.calculate_gratuity_amount(21, 5.00, type="full")
            reamaing_years = worked_year - 5.00
            gratuity_amount = gratuity_amount + self.calculate_gratuity_amount(30, reamaing_years, type="full")
            
            extra_lines = [{'name' : 'Leave salary',
                            'amount' : self.leave_salary,
                            'type' : 'allowance'}]
            return {"gratuity_amount" : gratuity_amount, 'extra_lines' : extra_lines}
        
    def limited_termination_without_benefits(self, on_probation, worked_days, worked_year, air_ticket):
        if on_probation:
            return {"gratuity_amount" : 0.00}
        
        if worked_year < 1.01:
            return {"gratuity_amount" : 0.00}
        
        if worked_year > 1 and on_probation:
            print ("Then he will be entitled to Gratuity Pay + 1 month Gross Salary")
            gratuity_amount = self.calculate_gratuity_amount(21, worked_year, type="full")
            return {"gratuity_amount" : gratuity_amount}
            
        
        if worked_year > 1 and worked_year < 5.01:
            print ('''full gratuity pay based on 21 days salary for each year of work, 
                      one month salary ''')
            gratuity_amount = self.calculate_gratuity_amount(21, worked_year, type="full")
            return {"gratuity_amount" : gratuity_amount}
            
        if worked_year > 5:
            print ('''full gratuity of 21 days salary for the first five
                    years and 30 days' for the remaining years and one month salary''')
            
            gratuity_amount = self.calculate_gratuity_amount(21, 5.00, type="full")
            reamaing_years = worked_year - 5.00
            gratuity_amount = gratuity_amount + self.calculate_gratuity_amount(30, reamaing_years, type="full")
            return {"gratuity_amount" : gratuity_amount}       
    
    
    def unlimited_termination(self, on_probation, worked_days, worked_year, air_ticket):    
        if on_probation:
            print ("Employee is not entitled to any benefits. Airticket Allowance can be provided for One way")
            extra_lines = []
            return {"gratuity_amount" : 0.00, 'extra_lines' : extra_lines}
        
        if worked_year < 1.01:
            print (''' If an employee has served for less than 1 year, he is not entitled to any gratuity pay.
                Eligible for Leave Salary and Airticket Allowance.
                Employees are entitled to an annual leave of 2 days per month, if they have completed six months of probation
                but not one year''')
            extra_lines = [{'name' : 'Leave salary',
                            'amount' : self.leave_salary,
                            'type' : 'allowance'}]
            return {"gratuity_amount" : 0.00, 'extra_lines' : extra_lines}
        
        
        
        if worked_year > 1 and worked_year < 5.01:
            print ('''If an employee has served more than 1 year but less than 5 years, 
                      he is entitled to 21 calendar days' basic salary
                      for each year of the first five years of work. Leave days and Air ticket ''')
            gratuity_amount = self.calculate_gratuity_amount(21, worked_year, type="full")
            extra_lines = [{'name' : 'Leave salary',
                            'amount' : self.leave_salary,
                            'type' : 'allowance'}]
            return {"gratuity_amount" : gratuity_amount, 'extra_lines' : extra_lines}
            
        if worked_year > 5:
            print ('''If an employee has served more than 5 years, he is entitled to 30 calendar days' 
                      basic salary for each additional year, provided the entire compensation 
                      does not exceed two years' pay. Leave days and AirTicket.''')
            
            gratuity_amount = self.calculate_gratuity_amount(21, 5.00, type="full")
            reamaing_years = worked_year - 5.00
            gratuity_amount = gratuity_amount + self.calculate_gratuity_amount(30, reamaing_years, type="full")
            extra_lines = [{'name' : 'Leave salary',
                            'amount' : self.leave_salary,
                            'type' : 'allowance'}]
            return {"gratuity_amount" : gratuity_amount, 'extra_lines' : extra_lines} 
        
    
    def unlimited_resignation(self, on_probation, worked_days, worked_year, air_ticket):    
        if on_probation:
            print ("Employee is not entitled to any benefits. Airticket Allowance can be provided for One way.")
            extra_lines = []
            return {"gratuity_amount" : 0.00, 'extra_lines' : extra_lines}
        
        if worked_year < 1.01:
            print (''' Leaving job before completing one year of service means employee is not entitled to any gratuity pay.
                        Eligible for Leave Salary and Airticket Allowance.
                        Employees are entitled to an annual leave of 2 days per month, if they have completed six months of probation
                        but not one year.''')
            extra_lines = [{'name' : 'Leave salary',
                            'amount' : self.leave_salary,
                            'type' : 'allowance'}]
            return {"gratuity_amount" : 0.00, 'extra_lines' : extra_lines}
        
        if worked_year > 1 and worked_year < 3.01:
            print ('''Employee is entitled to one third (1/3) of the 21-days gratuity pay, Leave Salary and Airticket.''')
            gratuity_amount = self.calculate_gratuity_amount(21, worked_year, type="1/3")
            extra_lines = [ {'name' : 'Leave salary',
                            'amount' : self.leave_salary,
                            'type' : 'allowance'}]
            return {"gratuity_amount" : gratuity_amount, 'extra_lines' : extra_lines} 
        
        if worked_year > 3 and worked_year < 5.01:
            print ('''Employee is entitled to two third (2/3) of the 21-days gratuity pay. Leave salary and Airticket''')
            gratuity_amount = self.calculate_gratuity_amount(21, worked_year, type="2/3")
            extra_lines = [{'name' : 'Leave salary',
                            'amount' : self.leave_salary,
                            'type' : 'allowance'}]
            return {"gratuity_amount" : gratuity_amount, 'extra_lines' : extra_lines} 
            
        if worked_year > 5.001:
            print ('''Employee is entitled to full 21-days gratuity pay. Leave and Airticket.''')
            #gratuity_amount = self.calculate_gratuity_amount(30, worked_year, type="full")
            gratuity_amount = self.calculate_gratuity_amount(21, 5.00, type="full")
            print("gratuity_amount1 =====>> ", gratuity_amount)
            reamaing_years = worked_year - 5.00
            print("reamaing_years ==>> ", reamaing_years)
            print("22============>> ", self.calculate_gratuity_amount(30, reamaing_years, type="full"))
            gratuity_amount = gratuity_amount + self.calculate_gratuity_amount(30, reamaing_years, type="full")
            extra_lines = [{'name' : 'Leave salary',
                            'amount' : self.leave_salary,
                            'type' : 'allowance'}]
            return {"gratuity_amount" : gratuity_amount, 'extra_lines' : extra_lines} 
#             gratuity_amount = self.calculate_gratuity_amount(21, 5.00, type="full")
#             reamaing_years = worked_year - 5.00
#             gratuity_amount = gratuity_amount + self.calculate_gratuity_amount(30, reamaing_years, type="full")
#             return {"gratuity_amount" : gratuity_amount}       


    def calculate_annual_leave(self):

        on_probation = self.find_on_probation()
        self.calculate_unpaid_leave_employees()
        worked_years = self.find_worked_years()

        #Compyting Daily Salary

        daily_salary = (self.basic_salary*12)/365
        # daily_salary = (self.basic_salary)/30
        daily_salary = round(daily_salary, 2)
        self.daily_salary = daily_salary



        if on_probation:
            self.remaining_annual_leaves = 0.00
            return
        if self.contract_type == "limited" and self.type == 'termination' and self.benefits == 'without':
            self.remaining_annual_leaves = 0.00
            return
        worked_year = self.worked_years

        if worked_year < 1.01:
            self._calculate_annual_leave('2')
        else:
            self._calculate_annual_leave('2.5')



    def calculate_unpaid_leave_employees(self):
        number_of_leaves_taken = 0
        number_of_leaves_allocated = 0
        unpaid_leave_types = self.env['hr.leave.type'].search([('unpaid', '=', True)])
        if not unpaid_leave_types:
            raise UserError(_('Unpaid leaves are not configured in system'))
        print("unpaid_leave_types ==>> ", unpaid_leave_types)
        leaves_taken = self.env['hr.leave.report'].search([('employee_id', '=', self.employee_id.id),
                                                           ('holiday_status_id', 'in', unpaid_leave_types.ids),
                                                           ('state', '=', 'validate'),
                                                           ('leave_type', '=', 'request')])
        print("leaves_taken ==>> ", leaves_taken)
        for lt in leaves_taken:
            number_of_days = lt.number_of_days if not lt.holiday_status_id.half_paid else 0.5
            if number_of_days < -0.01:
                number_of_days = number_of_days * -1
            number_of_leaves_taken = number_of_leaves_taken + number_of_days
        print("Number ==================================================",number_of_leaves_taken)
        self.unpaid_leaves = number_of_leaves_taken

    
    def post_move(self):
        if not self.expense_account_id:
            raise UserError('Please add Expense account!')
        if not self.gratuity_account_id:
            raise UserError('Please add Gratuity account!')
        if not  self.journal_id:
            raise UserError('Please add Journal!')

        gratuity = self.browse(self.id)
        move_line=[]

        additional_lines_dr = 0
        additional_lines_cr = 0

        for g_extra in gratuity.gratuity_extra_lines:

            if g_extra.account_id:

                if g_extra.type == 'allowance':

                    l1 = {
                        'name': g_extra.name,
                        'debit': g_extra.amount,
                        'credit': 0,
                        'account_id': g_extra.account_id.id,
                        'partner_id': gratuity.employee_id.address_home_id.id,
                        'journal_id': gratuity.journal_id.id,
                        'amount_currency': 0.0,
                    }
                    additional_lines_dr = additional_lines_dr + g_extra.amount
                    move_line.append((0, 0, l1))


                else:

                    l1 = {
                        'name': g_extra.name,
                        'debit': 0,
                        'credit': g_extra.amount,
                        'account_id': g_extra.account_id.id,
                        'partner_id': gratuity.employee_id.address_home_id.id,
                        'journal_id': gratuity.journal_id.id,
                        'amount_currency': 0.0,
                    }
                    additional_lines_cr = additional_lines_cr + g_extra.amount
                    move_line.append((0, 0, l1))



        print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXx")
        print("additional_lines_dr ===>> ", additional_lines_dr)
        print("additional_lines_cr ===>> ", additional_lines_cr)

        difference_amount = additional_lines_cr - additional_lines_dr

        print("difference_amount ====>> ", difference_amount)



        l1 = {
            'name': "gratuity for %s"%(gratuity.employee_id.name),
            'debit': gratuity.final_settlement_amount + difference_amount,
            'credit': 0,
            'account_id': gratuity.gratuity_account_id.id,
            'partner_id': gratuity.employee_id.address_home_id.id,
            'journal_id': gratuity.journal_id.id,
             'amount_currency': 0.0,
        }
        move_line.append((0, 0, l1))
        l2 = {
            'name': "gratuity for %s"%(gratuity.employee_id.name),
            'debit': 0.0,
            'credit': gratuity.final_settlement_amount,
            'account_id': gratuity.expense_account_id.id,
            'journal_id': gratuity.journal_id.id,
            'partner_id': gratuity.employee_id.address_home_id.id,
           
            'amount_currency': 0.0,
           
        }
        move_line.append((0, 0, l2))
        move_obj = self.env['account.move'].create({
            'ref': "gratuity for %s"%(gratuity.employee_id.name),
            'journal_id': self.journal_id.id,
            'line_ids': move_line,
                })


        move_obj.post()
        gratuity.write({'state': 'post', 'move_id' : move_obj.id})

        
        return True
    
    def _calculate_annual_leave(self, number_of_days_per_month = '2.5'):
        number_of_leaves_taken = 0
        number_of_leaves_allocated = 0
        annual_leave_types = self.env['hr.leave.type'].search([('annual_leave', '=', True)],order='id desc', limit=1)
        if not annual_leave_types:
            raise UserError(_('Annual leaves are not configured in system'))
        leaves_taken = self.env['hr.leave.report'].search([('employee_id', '=', self.employee_id.id), 
                                                           ('holiday_status_id', 'in', annual_leave_types.ids),
                                                           ('state', '=', 'validate'), ('leave_type', '=', 'request')])
        for lt in leaves_taken:
            number_of_leaves_taken = number_of_leaves_taken + lt.number_of_days
        if number_of_days_per_month == '2.5':
            leaves_allocated = self.env['hr.leave.report'].search([('employee_id', '=', self.employee_id.id), 
                                                           ('holiday_status_id', 'in', annual_leave_types.ids),
                                                           ('state', '=', 'validate'), ('leave_type', '=', 'allocation')])
            for la in leaves_allocated:
                number_of_leaves_allocated = number_of_leaves_allocated + la.number_of_days
                
        if number_of_days_per_month == '2':
            r = relativedelta(self.last_working_date, self.date_of_join)
            number_of_leaves_allocated = r.months * 2
            
        print ("leaves_taken ------>> ", number_of_leaves_taken)
        remaining_days = number_of_leaves_allocated + number_of_leaves_taken
        self.remaining_annual_leaves = remaining_days
        
    
    
    def calculate_end_of_service(self):
        total_days = total_amount = per_day_basic= 0        
        #Joining and Ending Dates
        if self.date_of_join:
            join_date = datetime.strptime(str(self.date_of_join),'%Y-%m-%d')            
        else:
            raise UserError(_('Please enter joining date for the employee !'))
        date_end = datetime.strptime(str(self.last_working_date), '%Y-%m-%d')        
        #Remove the existing gratuity lines while re-calculating
        gratuity_lines = []
        self.gratuity_line_ids.unlink()
        self.gratuity_extra_lines.unlink()
        
        if not self.contract_id:
            raise UserError(_('Employee Contract is not configured, Please go to Employees -> Contracts and create contract !'))
        
        if not self.employee_id.country_id:
            raise UserError(_('Employee nationality is not configured !'))
        if self.contract_id:
            on_probation = self.find_on_probation()
            #worked_years = self.find_worked_years()
            worked_years = {'days': self.worked_days, 'years': self.worked_years}
            vals = {}
            air_ticket = self.employee_id.country_id.air_ticket_allowance
            air_ticket = 0.00
            
            #Calculate Leave Salary
            #self.leave_salary = self.remaining_annual_leaves * ((self.basic_salary + self.hra) / 30.00)


            self.leave_salary = self.remaining_annual_leaves * self.daily_salary
            
            # Limited Contract, Resignation
            if self.contract_type == "limited" and self.type == 'resignation':
                vals = self.limited_resignation(on_probation, worked_years['days'], worked_years['years'], air_ticket)
            
            # Limited Contract with benefit, Termination
            if self.contract_type == "limited" and self.type == 'termination' and self.benefits == 'with':
                ###
                vals = self.limited_termination_with_benefits(on_probation, worked_years['days'], worked_years['years'], air_ticket)
                
            # Limited Contract without benefit, Termination
            if self.contract_type == "limited" and self.type == 'termination' and self.benefits == 'without':
                ###
                vals = self.limited_termination_without_benefits(on_probation, worked_years['days'], worked_years['years'], air_ticket)
            
            # Unlimited Contract, Termination
            if self.contract_type == "unlimited" and self.type == 'termination':
                vals = self.unlimited_termination(on_probation, worked_years['days'], worked_years['years'], air_ticket)
                
            # Unlimited Contract, Resignation
            if self.contract_type == "unlimited" and self.type == 'resignation':
                vals = self.unlimited_resignation(on_probation, worked_years['days'], worked_years['years'], air_ticket)
                
            
                
            vals = vals or {}
            if vals.get("gratuity_amount"):
                g_vals = {
                          'date_from' : self.date_of_join,
                          'date_to' : self.last_working_date,
                          'total_days' : worked_years['years'],
                          'amount' : vals["gratuity_amount"]}
                print("g_vals============================================================",g_vals)
                self.gratuity_line_ids = [(0, 0, g_vals)]
            print("self.gratuity_line_ids============================================================",vals.get("extra_lines")) 
            if vals.get("extra_lines"):
                self.gratuity_extra_lines = [(0, 0,vals.get("extra_lines")[0])]
                    
            
        return True            
    
  
    #===============================================================================
    # Class          :    hr_gratuity
    # Method         :    unlink
    # Description    :    Block deletion of records not in draft state
    #===============================================================================
    def unlink(self):
        for rec in self.browse(self.id):
            if rec.state != 'draft':
                raise UserError(_('You can only delete draft records!'))
        return super(hr_gratuity, self).unlink()
    


    
    #===============================================================================
    # Class          :    hr_gratuity
    # Method         :    button_paid (Button)
    # Description    :    Mark the record as Paid
    #===============================================================================
    def button_paid(self):        
        gratuity = self.browse(self.id)
        if gratuity.state != 'draft':
            raise UserError(_('Cannot Proceed!The record is Not in Draft state'))
        gratuity.write({'state': 'paid'})
        return True
    
    #===============================================================================
    # Class          :    hr_gratuity
    # Method         :    button_cancel (Button)
    # Description    :    Cancel the record
    #===============================================================================
    def button_cancel(self):        
        gratuity = self.browse(self.id)
        gratuity.write({'state': 'cancelled'})
        return True
    
    #===============================================================================
    # Class          :    hr_gratuity
    # Method         :    button_reset (Button)
    # Description    :    Reset the record to Draft
    #===============================================================================
    def button_reset(self):        
        gratuity = self.browse(self.id)
        gratuity.write({'state': 'draft'})
        return True
    

#=====================================================
# Gratuity split up details
#=====================================================
class hr_gratuity_line(models.Model):
    _name = 'hr.gratuity.line'    
 
    gratuity_id= fields.Many2one('hr.gratuity', string='Gratuity')
    contract_id= fields.Many2one('hr.contract', string='Contract')
    date_from= fields.Date('From Date')
    date_to= fields.Date('To Date')
    total_days= fields.Float(string='Total Years')
    amount= fields.Float(string='Amount')
     

# #=====================================================
# # Gratuity: Additional components
# #=====================================================
class hr_gratuity_extra(models.Model):
    _name = 'hr.gratuity.extra'   
    
    gratuity_id= fields.Many2one('hr.gratuity', string='Gratuity')
    name= fields.Text(string='Description')
    amount= fields.Float(string='Amount')
    type= fields.Selection([('allowance','Allowance'), ('deduction', 'Deduction')], string='Allowance/Deduction')
    account_id = fields.Many2one("account.account", string="Account")
        
