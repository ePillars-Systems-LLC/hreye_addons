from odoo import api, fields, models,_
import base64
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
class HrEmployeeRequest(models.Model):
    _name = "hr.employee.request"
    _inherit = 'mail.thread'

    @api.returns('self')
    def _default_employee_get(self):
        return self.env.user.employee_id

    def compute_show_approval(self):
        for req in self:
            if req.approval_required_from and req.approval_required_from == self.env.user:
                req.show_approval = True
            else:
                req.show_approval = False

    

    def compute_is_approver(self):
        for req in self:
            matrix_line = self.env['approval.matrix.line'].search(
                [('matrix_id.type', '=', 'hr_request'), ('user_id', '=', self.env.uid)])
            if matrix_line:
                req.is_approver = True
            else:
                req.is_approver = False
    name = fields.Char('Name')
    employee_id = fields.Many2one('hr.employee','Employee',default=_default_employee_get)
    request_type = fields.Selection([('noc','NOC Letter'),('salary_cert','Salary Certificate'),('asset_change','Asset Change'),('bank_letter','Bank Letter'),('general_request','General Request')],'Request Type',tracking=True)
    purpose = fields.Text('Purpose')
    request_date = fields.Date('Request Date',tracking=True,default=fields.Date.today())
    approved_date = fields.Date('Approved Date',tracking=True)
    state = fields.Selection([('draft','Draft'),('sent_for_approval','Sent For Approval'),('approved','Approved')],string='Status',track_visibility='onchange',default='draft',tracking=True)
    doc_attachment_id = fields.Many2many('ir.attachment', string="Attachment",
                                         help='You can attach the copy of your document', copy=False)

    to_address= fields.Char('To Address')
    name_of_bank = fields.Char('Name of bank')
    city = fields.Char('City')
    approved_user = fields.Many2one('hr.employee',string='Approved By')
    approval_required_from = fields.Many2one('res.users', string='Waiting for Approval from',track_visibility='onchange')
    show_approval = fields.Boolean(compute='compute_show_approval')
    approval_order = fields.Float("Approval Order")
    is_approver = fields.Boolean('Is approver', compute='compute_is_approver')
    

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('employee.request') or _('New')
        matrix = self.env['approval.matrix'].sudo().search([('type', '=', 'hr_request')])
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
        vals['state'] = 'sent_for_approval'
        res = super(HrEmployeeRequest, self).create(vals)

        return res

    def action_sent_for_approval(self):
        self.state = 'sent_for_approval'

    
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

    
    def action_approve(self):

        user, order = self.find_next_approver('hr_request', self.approval_required_from, self.approval_order)
        if not user:
            self.write({'state': 'approved'})
            self.approval_required_from = False
            approved_user = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
            if approved_user:
                self.approved_user = approved_user.id
            self.approved_date = datetime.today().date()
            if self.request_type == 'salary_cert':
                rpt = self.env.ref('UAE_HRMS.action_report_salary_certificate').render_qweb_pdf(self.ids)
                b64_pdf = base64.b64encode(rpt[0])
                file_name = self.employee_id.name + '_' + dict(self._fields['request_type'].selection).get(
                    self.request_type)
                attachment = self.env['ir.attachment'].create({
                    'name': file_name,
                    'type': 'binary',
                    'datas': b64_pdf,
                    'datas_fname': file_name,
                    'store_fname': file_name,
                    'res_model': self._name,
                    'res_id': self.id,
                    'mimetype': 'application/pdf'
                })
                self.doc_attachment_id = attachment.ids
                if self.doc_attachment_id:
                    self.state = 'approved'
            else:
                if not self.doc_attachment_id:
                    raise UserError("Please attach document!")
                else:
                    self.state = 'approved'

        else:
            self.write({'approval_required_from': user.id, 'approval_order': order})


