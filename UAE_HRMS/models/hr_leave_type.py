# -*- coding: utf-8 -*-


from odoo import api, fields, models
from odoo import tools, _
from datetime import date
from dateutil.relativedelta import relativedelta

class HolidaysType(models.Model):
    
    _inherit = "hr.leave.type"
    
    half_paid = fields.Boolean('Half Paid', default=False)
    annual_leave = fields.Boolean('Annual Leave', default=False)
    
    exceptional_annual_leave = fields.Boolean('Exceptional Annual Leave', default=False)
    exceptional_sick_leave = fields.Boolean('Exceptional Sick Leave', default=False)

    first_approval_note = fields.Many2many('res.users',  'hr_leave_type_first_note_rel', 'leave_type_id', string="First Approval Notification")
    second_approval_note = fields.Many2many('res.users', 'hr_leave_type_second_approval_note', 'leave_type_id', string="Second Approval Notification")
    code = fields.Char(string="Code", help="Code for Time Off Type")
    
    # validation_type = fields.Selection(selection_add=[('manager_and_dep_manager', 'Employee Manager + Department Manager'),('dept_manager_and_gm_gm',('Department Manager + GM1 + GM2'))],
    #                                   default='hr', string='Validation By')

   
    



    def run_leave_allocation(self):

        leave_allocation = self.env['hr.leave.allocation'].search([('holiday_status_id.annual_leave', '=', True),
                                                                   ('state', '=', 'validate'),
                                                                   ('holiday_type', '=', 'employee')])
        for lv_alloc in leave_allocation:
            if not lv_alloc.employee_id.date_of_join:
                print ("Send email natification to hr")
                mail_content = "Please set Date of Join for employee " + lv_alloc.employee_id.name +\
                               ". Other wise leave accrual cannot be done." + "<br><br>Thank You."

                users = self.env.ref('wtc_user_access.group_wtc_hr').users
                email_to = set(u.email for u in users if u.email)

                main_content = {
                    'subject': _('Joining date is not set for employee %s ') % (lv_alloc.employee_id.name),
                    'author_id': self.env.user.partner_id.id,
                    'body_html': mail_content,
                    'email_to': email_to,
                }
                self.env['mail.mail'].create(main_content).send()
                continue

            if not lv_alloc.last_updated_date:
                lv_alloc.last_updated_date = lv_alloc.employee_id.date_of_join

            date_of_join = lv_alloc.employee_id.date_of_join
            last_updated_date = lv_alloc.last_updated_date

            #Check last update date
            today = date.today()

            #Skipping exceution since already excuted (Only onnce in a month)
            if last_updated_date.year == today.year:
                if last_updated_date.month >= today.month:
                    continue
            if last_updated_date.year > today.year:
                continue

            #check is he still under six months of joining date

            number_of_months = (today.year - last_updated_date.year) * 12 + today.month - last_updated_date.month

            if number_of_months < 1:
                continue

            for each_month in range(number_of_months):
                each_month = each_month + 1

                each_date = last_updated_date + relativedelta(months=+each_month)
                print(each_month, " : ", each_date)

                #finding number of months between joining date and each date
                months = (each_date.year - date_of_join.year) * 12 + each_date.month - date_of_join.month

                number_of_leaves = 0

                if months == 6:
                    number_of_leaves = 2*6
                if months > 6 and months <12:
                    number_of_leaves = 2
                if months == 12:
                    number_of_leaves = 11*.5 + 2.5
                if months > 12:
                    number_of_leaves = 2.5

                number_of_days = lv_alloc.number_of_days
                number_of_days = number_of_days + number_of_leaves
                # if number_of_days > 60:
                #    number_of_days = 60
                lv_alloc.number_of_days = number_of_days
                lv_alloc.last_updated_date = each_date



















