
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError

class ApprovalMatrix(models.Model):
    
    _name = 'approval.matrix'
    _inherit = 'mail.thread'
    
    type = fields.Selection([('payslip', 'Payslip'),('advance','Advance'),('hr_request','HR Requests'),('leave_salary','Leave Salary'),('gratuity','Gratuity'),('resignation','Resignation')], string='Document Type', required=1)
    name = fields.Char(default='Approval Matrix')
    lines= fields.One2many('approval.matrix.line', 'matrix_id', string='Lines')
    
    
    def find_user(self, line, buyer, cost_center=None):
        """Finding approval user who based on approval line configuration"""
        if line.user_id:
            return line.user_id.id
        
        if line.requester_or_manager == "is_buyer":
            if buyer.user_id:
                return buyer.user_id.id
            else:
                raise UserError(_("Buyer's (%s) related user is not mapped in employee master" % buyer.name))
        
        if line.requester_or_manager == 'is_buyers_managers':
            if buyer.parent_id:
                if buyer.parent_id.user_id:
                    return buyer.parent_id.user_id.id
                else:
                    raise UserError(_("Manager's (%s) related user is not mapped in employee master" % buyer.parent_id.name))
            else:
                raise UserError(_("Buyer's (%s) manager mapped in employee master" % buyer.name))
        
        if line.requester_or_manager == 'cost_center_reponsible':
            if cost_center.responsible_department:
                if cost_center.responsible_department.manager_id:
                    if cost_center.responsible_department.manager_id.user_id:
                        return cost_center.responsible_department.manager_id.user_id.id
                    else:
                        raise UserError(_("Kindly link employee master and login id of %s" % cost_center.responsible_department.manager_id.name))
                else:
                    raise UserError(_("Kindly configure manger(Head) for department %s" % cost_center.responsible_department.name))
            else:
                raise UserError(_("Kindly configure responsible department for cost center %s" % cost_center.name))
        
        if line.job_id:
            employee_id = self.env['hr.employee'].search([('job_id', '=', line.job_id.id)])
            if len(employee_id) > 1:
                raise UserError(_("Multiple employees are under approving job position %s" % line.job_id.name))
            else:
                return employee_id.user_id.id
            
    
    
    
    def find_next_approver(self, type, amount, current_approval_order, buyer=None, cost_center=None):
        matrix = self.search([('type', '=', type)])
        if matrix and matrix.lines:
            matrix_lines = self.env['approval.matrix.line'].search([('approval_order', '>', current_approval_order), ('matrix_id', '=', matrix.id)], order='approval_order asc', limit=1)
            if matrix_lines:
                line = matrix_lines[0]
                if amount <= line.from_amount:
                    return (False, False)
            if not current_approval_order:
                approval_user = self.find_user(line, buyer, cost_center)
                return (approval_user, line.approval_order)
            
            if current_approval_order > 0:
                """ Checking next approval order """
                matrix_line = self.env['approval.matrix.line'].search([('matrix_id', '=', matrix.id),
                                ('from_amount', '<=', amount),
                                ('approval_order', '>', current_approval_order)], order='approval_order asc', limit=1)
                if not matrix_line:
                    """ Returning false when no further approval is required """
                    return (False, False)
                """ Returning next approval user and order """
                m_line = matrix_line[0]
                approval_user = self.find_user(m_line, buyer)
                return (approval_user, m_line.approval_order)
        return (False, False)
        
        
    
    
class ApprovalMatrixLine(models.Model):
    
    _name = 'approval.matrix.line'

    approval_order = fields.Float("Approval Order")
    from_amount = fields.Float("From Amount")
    is_buyer = fields.Boolean("Buyer/Requester")
    is_buyers_managers = fields.Boolean("Buyer's Manager")
    
    requester_or_manager = fields.Selection([('is_buyer', 'Requester'), 
                                             ('is_buyers_managers', "Requester's Manager"),
                                             ('cost_center_reponsible', "Cost Center Responsible")], string="Special Approving Persons")
    
    user_id = fields.Many2one("res.users", string='Approving User')
    job_id = fields.Many2one("hr.job", string='Approving Position')
    matrix_id = fields.Many2one("approval.matrix", string='Matrix')
    
    
class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    
    responsible_department = fields.Many2one('hr.department', string='Responsible Department')
    
    
