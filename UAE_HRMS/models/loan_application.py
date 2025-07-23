# # vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import  ValidationError,UserError



class loan_application(models.Model):
    _name = 'loan.application'
    _rec_name = 'loan_id'
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = 'Loan Application'

    
    def paid_button(self):
        if not self.employee_id.work_contact_id:
            raise ValidationError(_('Please set employee private address!'))
        if not self.payment_method_id:
            raise ValidationError(_('Please set advance payment method!'))

        payment_a = self.env['account.payment'].create({'payment_type': 'outbound',
            'amount': self.amount,
            'journal_id': self.payment_method_id.id,
            'company_id': self.env.ref('base.main_company').id,
            'partner_id': self.employee_id.work_contact_id.id,
            'payment_method_id': self.env.ref('account.account_payment_method_manual_out').id,
            'partner_type': 'supplier'})
        self.payment_id = payment_a.id
        self.write({'state': 'paid'})

        return

    def show_payment(self):
        form_id = self.env.ref('account.view_account_payment_form').id
        return {
            'name': _('Loan Payment'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_id':self.payment_id.id,
            'views': [(form_id, 'form')],
            'res_model': 'account.payment',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
        }
        
        
    
    def post_journal_entry(self):
        for application in self:
            if application.approval_required_from:
                raise UserError("Approval pending,You can post entries once the approval is done!")
            
            if not application.employee_id.work_contact_id:
                raise ValidationError(_('Please set employee private address!'))
            
            if not application.journal_id:
                raise ValidationError(_('Please correct journal for advances'))
            
            account_date = fields.Date.today()
            company_currency = application.company_id.currency_id
            account_dest = application.employee_id.work_contact_id.property_account_payable_id.id
             
            # move_line_name = application.employee_id.name + ': Advance'
            
            # move_lines = []
            # move_line_src = {
            #     'name': move_line_name,
            #     'quantity': 1,
            #     'debit': application.amount,
            #     'credit': 0,
            #     'amount_currency': 0.0,
            #     'account_id': application.journal_id.default_account_id.id,
            #     'product_id': False,
            #     'product_uom_id': False,
            #     'analytic_account_id': False,
            #     'analytic_tag_ids': False,
            #     'partner_id': application.employee_id.work_contact_id.id,
            #     'currency_id': False,
            # }
            # move_lines.append((0, 0, move_line_src))
            
            # move_line_dst = {
            #     'name': move_line_name,
            #     'debit': 0,
            #     'credit': application.amount,
            #     'account_id': account_dest,
            #     'date_maturity': account_date,
            #     'amount_currency': 0.0,
            #     'currency_id': False,
            #     'partner_id': application.employee_id.work_contact_id.id,
            # }
            # move_lines.append((0, 0, move_line_dst))
            
            
            # move_values = {
            #     'journal_id': application.journal_id.id,
            #     'company_id': application.company_id.id,
            #     'date': account_date,
            #     'ref': move_line_name,
            #     'name': '/',
            #     'line_ids' : move_lines,
            # }
            
            # move = self.env['account.move'].create(move_values)
            # move.post()
            # application.move_id = move.id
            application.state = "posted"
        
            

    
    def button_approved(self):

        user,order = self.find_next_approver('advance',self.approval_required_from,self.approval_order)
        if not user:
            self.write({'state': 'approved'})
            self.approval_required_from = False
        else:
            self.write({'approval_required_from' : user.id,'approval_order' : order})





    
    def unlink(self):
        for each_loan in self:
                raise ValidationError(_("You can't delete Loan."))
        return super(loan_application, self).unlink()

    
    def compute_payments_again(self):
        if self.amount != 0.00:
            date_list = []
            amount = self.amount
            months = self.term
            permonth_amount = amount/months
            balance_amt = self.amount
            for payment in range(months):
                date = self.start_date + relativedelta(months=payment)
                #date = date.replace(day=1)
                balance_amt = balance_amt - permonth_amount
                date_list.append((0, 0, {
                                'due_date': date,
                                'principal': permonth_amount,
                                'balance_amt': balance_amt
                }))
            payment_ids = self.env['loan.payment'].sudo().search([('loan_app_id' , '=', self.id)])
            payment_ids.sudo().unlink()
            self.write({'loan_payment_ids': date_list})

    
    def reset(self):
        self.write({'state': 'draft'})


    
    @api.depends('loan_payment_ids.state')
    def _check_loan_fully_paid(self):
        if self.loan_payment_ids:
            all_record = all ([x.state == 'paid' for x in self.loan_payment_ids if self.loan_payment_ids])
            if all_record:
                self.fully_paid = True
                self.state = 'close'

    
    
    def compute_show_approval(self):
        for adv in self:
            if adv.approval_required_from and adv.approval_required_from == self.env.user:
                adv.show_approval = True
            else:
                adv.show_approval = False
    
    def compute_is_approver(self):
        for adv in self:
            matrix_line = self.env['approval.matrix.line'].search([('matrix_id.type','=','advance'),('user_id','=',self.env.uid)])
            if matrix_line:
                adv.is_approver = True

    @api.returns('self')
    def _default_employee_get(self):
        return self.env.user.employee_id

    payment_id = fields.Many2one('account.payment', string='Payment')
    payment_method_id = fields.Many2one('account.journal', string='Payment Method', domain=[('type', 'in', ('bank', 'cash'))])
    journal_id = fields.Many2one('account.journal', string='Journal', domain=[('type', '=', 'general')])
    loan_id = fields.Char("Loan Number")
    employee_id = fields.Many2one('hr.employee', string="Employee",default=_default_employee_get)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id, store=True)
    amount = fields.Float("Amount")
    term = fields.Integer("No. Of Installment")
    loan_payment_ids = fields.One2many('loan.payment', 'loan_app_id', string="Loan Payment")
    state = fields.Selection([('draft', 'Draft'), ('approved', 'Approved'), ('close', 'Closed'),
                    ('cancel', 'Cancelled'),('posted','Posted'),('paid','Paid'), ('reset', 'Reset')], string="State", default='draft')
    start_date = fields.Datetime("Start Date", default=datetime.datetime.now())
    fully_paid = fields.Boolean(string="Fully Paid", compute='_check_loan_fully_paid', store=True)
    move_id = fields.Many2one('account.move', string='Journal Entry')
    approval_required_from = fields.Many2one('res.users', string='Waiting for Approval from',track_visibility='onchange')
    show_approval = fields.Boolean(compute='compute_show_approval')
    approval_order = fields.Float("Approval Order")
    is_approver = fields.Boolean('Is approver',compute='compute_is_approver')

    @api.model
    def create(self, vals):
        vals['loan_id'] = self.env['ir.sequence'].next_by_code('loan.application.number') or _('New')
        if vals.get('amount') <= 0.00:
            raise ValidationError(_('Please enter the requested loan amount.'))
        matrix = self.env['approval.matrix'].sudo().search([('type', '=', 'advance')])
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
        return super(loan_application, self).create(vals)

    
    def find_next_approver(self, type, current_approver, current_approval_order):
        matrix = self.env['approval.matrix'].sudo().search([('type', '=', type)])
        if matrix and matrix.lines:
            matrix_lines = self.env['approval.matrix.line'].sudo().search(
                [('approval_order', '>', current_approval_order), ('matrix_id', '=', matrix.id)],
                order='approval_order asc', limit=1)
            if matrix_lines:
                line = matrix_lines[0]
                approval_user = line.user_id
                approval_order = line.approval_order
                return (approval_user,approval_order)
        return (False, False)

class loan_payment(models.Model):
    _name = 'loan.payment'
    _description = 'Loan Payment'

    
    def paid_button(self):
        if self.loan_app_id.state != 'paid':
            raise ValidationError(_('Loan application is not approved.'))
        if self.state == 'draft':
            if not self.due_date:
                raise ValidationError(_('Please select the due date'))
            payment_rec = self.search([('loan_app_id', '=', self.loan_app_id.id), ('state', '=', 'paid')])
            if len(payment_rec) + 1 == self.loan_app_id.no_of_installment:
                self.loan_app_id.write({'state': 'close'})
            self.write({'state': 'paid'})

    due_date = fields.Date(string="Due Date")
    principal = fields.Float("Principal")
    balance_amt = fields.Float("Balance")
    loan_app_id = fields.Many2one('loan.application', string="Loan Application")
    employee_id = fields.Many2one('hr.employee', related='loan_app_id.employee_id', readonly=True, store=True)
    loan_state = fields.Selection(related="loan_app_id.state", store=True)
    
    state = fields.Selection([
                              ('draft', 'Draft'),
                              ('paid','Paid')], string="State", default='draft')
    payslip_id = fields.Many2one('hr.payslip', string="Payslip")





# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
