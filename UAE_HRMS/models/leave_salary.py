# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo import tools, _
from odoo.exceptions import UserError, ValidationError


#=====================================================
# Annual Leave Salary
#=====================================================
class leave_salary(models.Model):  
    
    _name = 'leave.salary'
    _rec_name = 'employee_id'
    _inherit = ['mail.thread']


    def check_account_access(self):
        for lv in self:
            if lv.env.user.has_group('account.group_account_user'):
                lv.account_access = True
            else:
                lv.account_access = False

    def compute_show_approval(self):
        for req in self:
            if req.approval_required_from and req.approval_required_from == self.env.user:
                req.show_approval = True
            else:
                req.show_approval = False

    def compute_is_approver(self):
        for req in self:
            matrix_line = self.env['approval.matrix.line'].search(
                [('matrix_id.type', '=', 'leave_salary'), ('user_id', '=', self.env.uid)])
            if matrix_line:
                req.is_approver = True
    @api.depends('leave_salary_amount','air_ticket_amount')
    def compute_total(self):
        for sal in self:
            sal.total = sal.leave_salary_amount + sal.air_ticket_amount

    @api.returns('self')
    def _default_employee_get(self):
        return self.env.user.employee_id
    
    employee_id = fields.Many2one('hr.employee', string='Employee',default=_default_employee_get)
    leave_date = fields.Date('Date', default=fields.Date.context_today)
    basic_salary = fields.Float(string='Gross')
    leaves_balance = fields.Float(string='Leave Balance')
    leave_salary_amount = fields.Float(string='Leave Salary')
    air_ticket_amount = fields.Float(string='Air Ticket Amount')
    total = fields.Float("Total",compute = "compute_total")

    state= fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled'),
        ], string='Status', track_visibility='onchange',default='draft')
    payment_mode = fields.Selection([('with_payslip', 'With Payslip'),('separate','Separate')],string='Payment Mode')
    payslip_id = fields.Many2one('hr.payslip', string='Payslip')
    journal_id = fields.Many2one('account.journal', string="Journal")
    debit_id = fields.Many2one('account.account', string="Debit Account for Leave Salary")
    debit_airticket_id = fields.Many2one('account.account', string="Debit Account for Airticket")
    credit_id = fields.Many2one('account.account', string="Credit Account")
    move_id = fields.Many2one('account.move', string="Posted Entry")
    account_access = fields.Boolean(compute='check_account_access')
    approval_required_from = fields.Many2one('res.users', string='Waiting for Approval from',track_visibility='onchange')
    show_approval = fields.Boolean(compute='compute_show_approval')
    approval_order = fields.Float("Approval Order")
    is_approver = fields.Boolean('Is approver', compute='compute_is_approver')



    
    
    @api.onchange('basic_salary', 'leaves_balance', 'air_ticket_amount')
    def calculate_amount(self):
        if self.basic_salary > 0.01:
            daily_salary = self.basic_salary/30
            self.leave_salary_amount = self.leaves_balance * daily_salary
    
    
    
    @api.onchange('employee_id')
    def calculate_annual_leave(self):
        number_of_leaves_taken = 0
        number_of_leaves_allocated = 0
        annual_leave_types = self.env['hr.leave.type'].search([('annual_leave', '=', True)], limit=1)
        if not annual_leave_types:
            raise UserError(_('Annual leaves are not configured in system'))
        leaves_taken = self.env['hr.leave.report'].search([('employee_id', '=', self.employee_id.id), 
                                                           ('holiday_status_id', 'in', annual_leave_types.ids),
                                                           ('state', '=', 'validate')],order='date_from desc', limit=1)
        for lt in leaves_taken:
            number_of_leaves_taken = number_of_leaves_taken + lt.number_of_days
            
        
        leaves_allocated = self.env['hr.leave.report'].search([('employee_id', '=', self.employee_id.id), 
                                                       ('holiday_status_id', 'in', annual_leave_types.ids),
                                                       ('state', '=', 'validate')])
        for la in leaves_allocated:
            number_of_leaves_allocated = number_of_leaves_allocated + la.number_of_days
                
        remaining_days = number_of_leaves_allocated + number_of_leaves_taken
        self.leaves_balance = abs(number_of_leaves_taken)
        
        contract_ids = self.env['hr.contract'].search([('employee_id','=',self.employee_id.id),('state','=','open')], order='date_start desc', limit=1)
        if contract_ids:
            # self.basic_salary = contract_ids[0].basic + contract_ids[0].hra
            self.basic_salary = contract_ids[0].wage
    
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
                return (approval_user,approval_order)
        return (False, False)
    
    @api.model
    def create(self,vals):
        matrix = self.env['approval.matrix'].sudo().search([('type', '=', 'leave_salary')])
        user = False
        order = False
        if matrix:
            line = self.env['approval.matrix.line'].sudo().search([
                ('matrix_id', '=', matrix.id)], order='approval_order asc', limit=1)[0]
            user = line.user_id.id if line else False
            order = line.approval_order if line else False
        else:
            raise UserError("Approval sequence not set, Please contact HR Manager!")
        vals['approval_required_from'] = user
        vals['approval_order'] = order
        res = super(leave_salary, self).create(vals)
        return res
            
    def button_confirm(self):
        user, order = self.find_next_approver('leave_salary', self.approval_required_from, self.approval_order)
        if not user:
            self.write({'state': 'confirm'})
            self.approval_required_from = False
        else:
            self.write({'approval_required_from': user.id, 'approval_order': order})

        
        return True

    def button_post(self):
        if self.approval_required_from:
            raise UserError("Approval pending,You can post entries once the approval is done!")
        if not (self.debit_airticket_id and self.debit_id and self.credit_id and self.journal_id):
            raise UserError("Please fill all the accounting fields!!(Journal,Debit account,Credit account)")
        gratuity = self.browse(self.id)
        gratuity.write({'state': 'posted'})

        mv_vals = {

            'journal_id' : gratuity.journal_id.id,
            'ref' : 'Leave Salary ' + gratuity.employee_id.name,
            'date' : gratuity.leave_date
        }
        cr_line = {
             'account_id' : gratuity.credit_id.id,
             'credit' : gratuity.leave_salary_amount + gratuity.air_ticket_amount,
             'debit' : 0,
             'partner_id' : gratuity.employee_id.address_home_id.id
        }
        dr_line = {
            'account_id': gratuity.debit_id.id,
            'credit': 0,
            'debit': gratuity.leave_salary_amount,
            'partner_id': gratuity.employee_id.address_home_id.id
        }
        dr_line_air = {
            'account_id': gratuity.debit_airticket_id.id,
            'credit': 0,
            'debit': gratuity.air_ticket_amount,
            'partner_id': gratuity.employee_id.address_home_id.id
        }

        mv_vals['line_ids'] = [(0,0, cr_line), (0,0, dr_line), (0,0,dr_line_air)]
        move = self.env['account.move'].create(mv_vals)
        move.post()
        gratuity.move_id = move.id



        return True
    
    def button_cancel(self):        
        gratuity = self.browse(self.id)
        gratuity.write({'state': 'cancelled'})
        return True
    
    def button_reset(self):        
        gratuity = self.browse(self.id)
        gratuity.write({'state': 'draft'})
        return True
        
        
    
    
    
    
