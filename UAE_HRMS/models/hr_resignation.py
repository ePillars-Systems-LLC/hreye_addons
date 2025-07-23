
# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import datetime
from datetime import datetime
date_format = "%Y-%m-%d"

class HrResignation(models.Model):
    _name = 'hr.resignation'
    _inherit = 'mail.thread'
    _rec_name = 'employee_id'

    @api.returns('self')
    def _default_employee_get(self):
        return self.env.user.employee_id

    
    def compute_show_approval(self):
        for adv in self:
            if adv.approval_required_from and adv.approval_required_from == self.env.user:
                adv.show_approval = True
            else:
                adv.show_approval = False

    
    def compute_is_approver(self):
        for adv in self:
            matrix_line = self.env['approval.matrix.line'].search(
                [('matrix_id.type', '=', 'advance'), ('user_id', '=', self.env.uid)])
            if matrix_line:
                adv.is_approver = True

    name = fields.Char(string='Order Reference', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', string="Employee", default=_default_employee_get,
                                  help='Name of the employee for whom the request is creating')
    department_id = fields.Many2one('hr.department', string="Department", related='employee_id.department_id',
                                    help='Department of the employee')
    expected_revealing_date = fields.Date(string="Relieving Date", required=True,
                                          help='Date on which he is revealing from the company')
    resignation_date = fields.Date('Date of Resignation',required=True)
    resign_confirm_date = fields.Date(string="Resign Request Approved date", help='Date on which the request is confirmed')
    date_of_join = fields.Date(string="Date of Joining", required=True,
                              help='Joining date of the employee')
    reason = fields.Text(string="Reason", help='Specify reason for leaving the company')
    notice_period = fields.Char(string="Notice Period")
    relieving_type = fields.Selection([
        ('resignation', 'Resignation '),
        ('termination', 'Termination'),
    ], string='Resignation/Termination', default='resignation')
    state = fields.Selection([('draft', 'Draft'),('to_approve','To Approve'), ('approved', 'Approved'), ('cancel', 'Cancel')],
                             string='Status', track_visibility='onchange',default='draft')
    approval_required_from = fields.Many2one('res.users', string='Waiting for Approval from',
                                             track_visibility='onchange')
    show_approval = fields.Boolean(compute='compute_show_approval')
    approval_order = fields.Float("Approval Order")
    is_approver = fields.Boolean('Is approver', compute='compute_is_approver')

    @api.model
    def create(self, vals):        
        vals['name'] = self.env['ir.sequence'].next_by_code('hr.resignation.number') or _('New')
        res = super(HrResignation, self).create(vals)
        return res

    
    def sent_for_approval(self):
        matrix = self.env['approval.matrix'].sudo().search([('type', '=', 'resignation')])
        user = False
        order = False
        if matrix:
            line = self.env['approval.matrix.line'].sudo().search([
                ('matrix_id', '=', matrix.id)], order='approval_order asc', limit=1)[0]
            user = line.user_id if line else False
            order = line.approval_order if line else False
            if user:
                # user_id = self.env['res.users'].browse(user)
                if user:
                    mail_content = "Please approve resignation request of %s" %self.employee_id.name


                    email_to =  "%s" % ';'.join(map(str, [user.email]))

                    main_content = {
                        'subject': _('Resignation Request-%s') % (self.employee_id.name),
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

    
    def confirm_resignation(self):

        user, order = self.find_next_approver('resignation', self.approval_required_from, self.approval_order)
        if not user:
            self.write({'state': 'approved','resign_confirm_date':str(datetime.now())})
            self.approval_required_from = False
        else:
            if user:
                user_id = self.env['res.users'].browse(user)
                if user_id:
                    mail_content = "Please approve resignation request of %s" %self.employee_id.name


                    email_to =  "%s" % ';'.join(map(str, [user.email]))

                    main_content = {
                        'subject': _('Resignation Request-%s') % (self.employee_id.name),
                        'author_id': self.env.user.partner_id.id,
                        'body_html': mail_content,
                        'email_to': email_to,
                    }
                    self.env['mail.mail'].create(main_content).send()
            self.write({'approval_required_from': user.id,'state':'to_approve', 'approval_order': order,'resign_confirm_date':str(datetime.now())})
        # for rec in self:
        #     rec.state = 'confirm'
        #     rec.resign_confirm_date = str(datetime.now())

    
    def cancel_resignation(self):
        for rec in self:
            rec.state = 'cancel'

    
    def reject_resignation(self):
        for rec in self:
            rec.state = 'rejected'

    
    def approve_resignation(self):
        for rec in self:
            if rec.expected_revealing_date:
                rec.state = 'approved'
                rec.resign_confirm_date = datetime.today().date()
            else:
                raise UserError("Please add the Relieving Date!")
    
    @api.onchange('employee_id')
    def set_join_date(self):
        self.date_of_join = self.employee_id.date_of_join if self.employee_id.date_of_join else ''

    
    @api.constrains('employee_id')
    def check_employee(self):
        # Checking whether the user is creating leave request of his/her own
        for rec in self:
            if not self.env.user.has_group('hr.group_hr_user'):
                if rec.employee_id.user_id.id and rec.employee_id.user_id.id != self.env.uid:
                    raise ValidationError(_('You cannot create request for other employees'))

    @api.constrains('date_of_join', 'expected_revealing_date')
    def _check_dates(self):        
        for rec in self:
            resignation_request = self.env['hr.resignation'].search([('employee_id', '=', rec.employee_id.id),
                                                                     ('state', 'in', ['confirm', 'approved'])])
            if resignation_request:
                raise ValidationError(_('There is a resignation request in confirmed or'
                                        ' approved state for this employee'))
            if rec.date_of_join >= rec.expected_revealing_date:
                raise ValidationError(_('Revealing date must be anterior to joining date'))
    
    @api.onchange('employee_id')
    @api.depends('employee_id')
    def check_request_existence(self):
        # Check whether any resignation request already exists
        for rec in self:
            if rec.employee_id:
                resignation_request = self.env['hr.resignation'].search([('employee_id', '=', rec.employee_id.id),
                                                                         ('state', 'in', ['confirm', 'approved'])])
                if resignation_request:
                    raise ValidationError(_('There is a resignation request in confirmed or'
                                            ' approved state for this employee'))
