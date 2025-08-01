import base64
from datetime import datetime
from datetime import *
from io import BytesIO

import xlsxwriter
from odoo import fields, models, api, _
from xlsxwriter.utility import xl_rowcol_to_cell
from calendar import monthrange
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from calendar import monthrange

class HrPayslipRun(models.Model):

    _inherit = ['hr.payslip.run', 'mail.thread']
    _name = "hr.payslip.run"

    def _compute_can_approve(self):
        logged_user = self.env.user.id
        for run in self:
            can_approve = False
            if run.state == "to approve" and run.approval_required_from:
                if run.approval_required_from.id == logged_user:
                    can_approve = True
            run.can_approve = can_approve

    def _can_post_accouting_entry(self):
        for run in self:
            can_post_accouting_entry = False
            if run.state == "close" and not run.accouting_entry_posted and self.env.user.has_group(
                    'hr_payroll.group_hr_payroll_manager'):
                can_post_accouting_entry = True
            run.can_post_accouting_entry = can_post_accouting_entry

    def compute_show_approval(self):
        for run in self:
            if run.approval_required_from and run.approval_required_from == self.env.user:
                run.show_approval = True
            else:
                run.show_approval = False


    state = fields.Selection(selection_add=[('to approve', 'To Approve')])
    approval_required_from = fields.Many2one('res.users', string='Waiting for Approval from', readonly=True, copy=False)
    current_approval_amount = fields.Integer("Current Approval Amount", default=0, readonly=True, copy=False)
    file_name = fields.Char('File Name', size=256, readonly=True)
    file_download = fields.Binary('Download payroll', readonly=True)
    can_approve = fields.Boolean("Can Approve", compute='_compute_can_approve')
    can_post_accouting_entry = fields.Boolean("Can POST Entry", compute='_can_post_accouting_entry')
    accouting_entry_posted = fields.Boolean("Accouting_entry_posted")
    show_approval = fields.Boolean(compute='compute_show_approval')
    credit_note = fields.Boolean(string='Credit Note',
                                 help="If its checked, indicates that all"
                                      "payslips generated from here are refund"
                                      "payslips.")

    def find_next_approver(self):
        res = self.env['approval.matrix'].find_next_approver('payslip', 100, self.current_approval_amount)
        return res

    def close_payslip_run(self):
        for order in self:
            res = order.find_next_approver()
            if order.approval_required_from:
                if order.approval_required_from.id == self.env.uid:

                    if res[0]:
                        order.message_post(body=_('Approved'))
                        order.approval_required_from = res[0]
                        order.current_approval_amount = res[1]
                        order.state = 'to approve'

                        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        _url = '' + base_url + '/' + 'web?#id=%s&model=hr.payslip.run&view_type=form' % order.id
                        subject = 'Payroll Approval'
                        body = _("Dear %s, <br/> Kindly Check and approve Payroll of %s \
                                <br /><p><a href=%s class='btn btn-danger'>View Payroll</a><br></p>") \
                               % (order.approval_required_from.name, order.name, _url)
                        mail = self.env['mail.mail'].create({
                            'subject': subject,
                            'body_html': body,
                            'notification': True,
                            'state': 'outgoing',
                            'recipient_ids': [(4, order.approval_required_from.partner_id.id)]
                        })

                        return True
                    else:
                        order.message_post(body=_('Approved'))
                        order.approval_required_from = False
                        order.current_approval_amount = 0
                        return super(HrPayslipRun, order).close_payslip_run()
                else:

                    raise Warning(_(
                        'Sorry!!! You cannot Approve this Payroll, Waiting for approval from %s' % order.approval_required_from.name))

            else:
                if res[0]:
                    order.message_post(body=_('Submitted for approvals'))
                    order.approval_required_from = res[0]
                    order.current_approval_amount = res[1]
                    order.state = 'to approve'

                    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    _url = '' + base_url + '/' + 'web?#id=%s&model=hr.payslip.run&view_type=form' % order.id
                    subject = 'Payroll Approval'
                    body = _("Dear %s, <br/> Kindly Check and approve Payroll of %s \
                            <br /><p><a href=%s class='btn btn-danger'>View Payroll</a><br></p>") \
                           % (order.approval_required_from.name, order.name, _url)
                    mail = self.env['mail.mail'].create({
                        'subject': subject,
                        'body_html': body,
                        'notification': True,
                        'state': 'outgoing',
                        'recipient_ids': [(4, order.approval_required_from.partner_id.id)]
                    })

                    return True
                else:
                    order.approval_required_from = False
                    order.current_approval_amount = 0
                    #                     for slip in order.slip_ids:
                    #                         if slip.state == 'verify':
                    #                            slip.action_payslip_done()
                    return super(HrPayslipRun, order).close_payslip_run()

    # to get salary rules names
    def get_rules(self):
        structure = []
        for payslip in self.slip_ids:
            if payslip.struct_id not in structure:
                structure.append(payslip.struct_id)

        rule_ids = []
        for struct in structure:
            for struct_rule in struct.rule_ids:
                if struct_rule.id not in rule_ids:
                    rule_ids.append(struct_rule.id)

        vals = []
        heads = self.env['hr.salary.rule'].search([('active', 'in', (True, False)), ('id', 'in', rule_ids)],
                                                  order='sequence asc')
        for head in heads:
            list = [head.name, head.code]
            vals.append(list)
        return vals

    def post_account_entries(self):
        for run in self:
            for slip in run.slip_ids:
                if slip.state == 'verify':
                    slip.action_payslip_done()
            run.accouting_entry_posted = True

    def do_verify_all(self):
        for payslip_run in self:
            for payslip in payslip_run.slip_ids:
                payslip.action_payslip_verified()

    def generate_payroll(self):
        file_name = _('payroll report.xlsx')
        fp = BytesIO()

        workbook = xlsxwriter.Workbook(fp)
        heading_format = workbook.add_format({'align': 'center',
                                              'valign': 'vcenter',
                                              'bold': True, 'size': 14})
        cell_text_format_n = workbook.add_format({'align': 'center',
                                                  'bold': True, 'size': 9,
                                                  })
        cell_text_format = workbook.add_format({'align': 'left',
                                                'bold': True, 'size': 9,
                                                })

        cell_text_format.set_border()
        cell_text_format_new = workbook.add_format({'align': 'left',
                                                    'size': 9,
                                                    })
        cell_text_format_new.set_border()
        cell_number_format = workbook.add_format({'align': 'right',
                                                  'bold': False, 'size': 9,
                                                  'num_format': '#,###0.00'})
        cell_number_format.set_border()
        worksheet = workbook.add_worksheet('payroll report.xlsx')
        normal_num_bold = workbook.add_format({'bold': True, 'num_format': '#,###0.00', 'size': 9, })
        normal_num_bold.set_border()
        worksheet.set_column('A:A', 20)
        worksheet.set_column('B:B', 20)
        worksheet.set_column('C:C', 20)
        worksheet.set_column('D:D', 20)
        worksheet.set_column('E:E', 20)
        worksheet.set_column('F:F', 20)
        worksheet.set_column('G:G', 20)
        worksheet.set_column('H:H', 20)
        worksheet.set_column('I:I', 20)
        worksheet.set_column('J:J', 20)
        worksheet.set_column('K:K', 20)
        worksheet.set_column('L:L', 20)
        worksheet.set_column('M:M', 20)
        worksheet.set_column('N:N', 20)

        if self.date_start and self.date_end:

            date_2 = datetime.strftime(self.date_end, '%d-%m-%Y')
            date_1 = datetime.strftime(self.date_start, '%d-%m-%Y')
            payroll_month = self.date_start.strftime("%B")
            worksheet.merge_range('A1:F2', 'Payroll For %s %s' % (payroll_month, self.date_start.year), heading_format)
            company = self.env['res.company']._company_default_get()
            worksheet.merge_range('B4:D4', '%s' % (company.name), cell_text_format_n)
            row = 2
            column = 0
            worksheet.write(row + 1, 0, 'Company', cell_text_format_n)
            worksheet.write(row, 4, 'Date From', cell_text_format_n)
            worksheet.write(row, 5, date_1 or '')
            row += 1
            worksheet.write(row, 4, 'Date To', cell_text_format_n)
            worksheet.write(row, 5, date_2 or '')
            row += 2
            res = self.get_rules()

            worksheet.write(row, 0, 'Employee', cell_text_format)
            worksheet.write(row, 1, 'Employee ID', cell_text_format)

            row_set = row
            column = 2
            # to write salary rules names in the row
            for vals in res:
                worksheet.write(row, column, vals[0], cell_text_format)
                column += 1
            row += 1
            col = 0
            ro = row

            payslip_ids = self.env['hr.payslip'].sudo().search(
                [('payslip_run_id', '=', self.id), ('state', 'in', ['done', 'paid'])])
            if payslip_ids:

                for payslip in payslip_ids:
                    name = payslip.employee_id.name
                    id = payslip.employee_id.identification_id

                    worksheet.write(ro, col, name or '', cell_text_format_new)
                    worksheet.write(ro, col + 1, id or '', cell_text_format_new)

                    ro = ro + 1
            col = col + 2
            colm = col

            if payslip_ids:
                for payslip in payslip_ids:
                    for vals in res:

                        check = False
                        for line in payslip.line_ids:
                            if line.code == vals[1]:
                                check = True
                                r = line.total

                        if check == True:

                            worksheet.write(row, col, r, cell_number_format)


                        else:
                            worksheet.write(row, col, 0, cell_number_format)

                        col += 1
                    row += 1
                    col = colm
        worksheet.write(row, 0, 'Grand Total', cell_text_format)
        # calculating sum of columnn
        roww = row
        columnn = 2
        for vals in res:
            cell1 = xl_rowcol_to_cell(row_set + 1, columnn)

            cell2 = xl_rowcol_to_cell(row - 1, columnn)
            worksheet.write_formula(row, columnn, '{=SUM(%s:%s)}' % (cell1, cell2), normal_num_bold)
            columnn = columnn + 1

        worksheet.write(row, 1, '', cell_text_format)
        worksheet.write(row, 2, '', cell_text_format)

        workbook.close()
        file_download = base64.b64encode(fp.getvalue())
        fp.close()

        self.file_name = file_name
        self.file_download = file_download

        return True


class HrPayrollStructure(models.Model):
    
    _inherit = 'hr.payroll.structure'
    
    is_fixed_salary = fields.Boolean("Is Fixed Salary?")

class HrPayslipEmployees(models.TransientModel):
    
    _inherit = 'hr.payslip.employees'
    
    def compute_sheet_old(self):
        attendance_from = False
        attendance_to = False
        if self.env.context.get('active_id'):
            payslip_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))
            date_start = payslip_run.date_start
            date_end = payslip_run.date_end
            
            date_from_dt = fields.Datetime.from_string(date_start) - relativedelta(months=1)
            date_from_dt = date_from_dt.replace(day=26)
            
            date_to_dt = fields.Datetime.from_string(date_end)
            date_to_dt = date_to_dt.replace(day=25)
            
            attendance_from = date_from_dt.date()
            attendance_to = date_to_dt.date()
        
        return super(HrPayslipEmployees, self.with_context(attendance_from=attendance_from, attendance_to=attendance_to)).compute_sheet()

    # def compute_sheet(self):
    #     payslips = self.env['hr.payslip']
    #     [data] = self.read()
    #     active_id = self.env.context.get('active_id')
    #     if active_id:
    #         [run_data] = self.env['hr.payslip.run'].browse(active_id).read(['date_start', 'date_end', 'credit_note'])
    #     from_date = run_data.get('date_start')
    #     to_date = run_data.get('date_end')
    #     if not data['employee_ids']:
    #         raise UserError(_("You must select employee(s) to generate payslip(s)."))
    #     for employee in self.env['hr.employee'].browse(data['employee_ids']):
    #         slip_data = self.env['hr.payslip'].onchange_employee_id(from_date, to_date, employee.id, contract_id=False)
            
    #         date_from_dt = fields.Datetime.from_string(from_date) - relativedelta(months=1)
    #         date_from_dt = date_from_dt.replace(day=26)
    #         date_to_dt = fields.Datetime.from_string(to_date)
    #         date_to_dt = date_to_dt.replace(day=25)
    #         attendance_from = date_from_dt.date()
    #         attendance_to = date_to_dt.date()
    #         journal_id = self.env['hr.payslip.run'].browse(self.env.context.get('active_id')).journal_id.id
    #         res = {
    #             'employee_id': employee.id,
    #             'name': slip_data['value'].get('name'),
    #             'struct_id': slip_data['value'].get('struct_id'),
    #             'contract_id': slip_data['value'].get('contract_id'),
    #             'payslip_run_id': active_id,
    #             'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
    #             'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids')],
    #             'date_from': from_date,
    #             'date_to': to_date,
    #             'credit_note': run_data.get('credit_note'),
    #             'company_id': employee.company_id.id,
    #             'journal_id' : journal_id,
    #             'attendance_from' : attendance_from,
    #             'attendance_to' : attendance_to
    #         }
    #         payslips += self.env['hr.payslip'].create(res)
    #     payslips.compute_sheet()
    #     return {'type': 'ir.actions.act_window_close'}

class hr_payslip(models.Model):
    
    _inherit = 'hr.payslip'
    
    
    def compute_sheet(self):
        self._compute_employee_ot_hours()
        self._compute_loan()
        self._compute_unpaid_leave_amount()
        self._compute_loan()
        self.find_annual_leave()
        self.deduct_if_joining_date()
        return super(hr_payslip, self).compute_sheet()

    def deduct_if_joining_date(self):

        for payslip in self:

            if payslip.employee_id.date_of_join:
                date_of_join = payslip.employee_id.date_of_join
                if date_of_join > payslip.date_from:
                    date_from_dt = fields.Datetime.from_string(payslip.date_from)
                    date_to_dt = fields.Datetime.from_string(date_of_join)
                    date_diff = date_to_dt - date_from_dt
                    total_days_not_joinied = date_diff.days

                    print("total_days_not_joinied =========>> ", total_days_not_joinied)

                    date_from_dt = fields.Datetime.from_string(payslip.date_from)
                    date_to_dt = fields.Datetime.from_string(payslip.date_to)
                    date_diff = date_to_dt - date_from_dt
                    total_working_days = date_diff.days + 1

                    print("total_working_days ==> ", total_working_days)

                    basic = payslip.contract_id.basic
                    hra = payslip.contract_id.hra
                    transportation = payslip.contract_id.transportation
                    other_allowances = payslip.contract_id.other_allowance

                    basic = basic/total_working_days
                    print("basic/day =========>. ", basic)

                    payslip.basic_deduction = basic * total_days_not_joinied

                    hra = hra / total_working_days
                    payslip.hra_deduction = hra * total_days_not_joinied

                    transportation = transportation / total_working_days
                    payslip.transportation_deduction = transportation * total_days_not_joinied

                    other_allowances = other_allowances / total_working_days
                    payslip.other_allow_deduction = other_allowances * total_days_not_joinied









    
    def find_annual_leave(self):

        for payslip in self:

            # day_list = []
            # for working_hour in payslip.employee_id.resource_calendar_id.attendance_ids:
            #     if int(working_hour.dayofweek) not in day_list:
            #         day_list.append(int(working_hour.dayofweek))
            #
            # hr_hoilday_total = self.env['hr.leave'].search([
            #     ('employee_id', '=', payslip.employee_id.id),
            #     ('date_from', '>=', payslip.date_from),
            #     ('date_from', '<=', payslip.date_to),
            #     ('state', '=', 'validate')])
            # hr_hoilday_ids = hr_hoilday_total.ids
            #
            # hr_hoilday_total = self.env['hr.leave'].search([
            #     ('employee_id', '=', payslip.employee_id.id),
            #     ('date_to', '>=', payslip.date_from),
            #     ('date_to', '<=', payslip.date_to),
            #     ('state', '=', 'validate')])
            #
            # for holiday in hr_hoilday_total:
            #     if holiday.id not in hr_hoilday_ids:
            #         hr_hoilday_ids.append(holiday.id)
            #
            # hr_hoilday_total = self.env['hr.leave'].browse(hr_hoilday_ids)
            #
            #
            # halfpaid_days = 0
            # for halfpaid in hr_hoilday_total:
            #     if halfpaid.holiday_status_id.annual_leave:
            #         if halfpaid.date_from.date() < payslip.date_from:
            #             halfpaid_from_dt = fields.Datetime.from_string(payslip.date_from)
            #         else:
            #             halfpaid_from_dt = fields.Datetime.from_string(halfpaid.date_from)
            #
            #         if halfpaid.date_to.date() > payslip.date_to:
            #             halfpaid_to_dt = fields.Datetime.from_string(payslip.date_to)
            #         else:
            #             halfpaid_to_dt = fields.Datetime.from_string(halfpaid.date_to)
            #
            #         halfpaid_from_dt = halfpaid_from_dt.date()
            #         halfpaid_to_dt = halfpaid_to_dt.date()
            #
            #         halfpaid_diff = halfpaid_to_dt - halfpaid_from_dt
            #         for i in range(halfpaid_diff.days + 1):
            #             halfpaid_date = halfpaid_from_dt + timedelta(days=i)
            #             if halfpaid_date.weekday() in day_list:
            #                 halfpaid_days += 1
            # payslip.annual_leave_count = halfpaid_days

            if payslip.annual_leave_count > 0:
                date_from_dt = fields.Datetime.from_string(payslip.date_from)
                date_to_dt = fields.Datetime.from_string(payslip.date_to)
                date_diff = date_to_dt - date_from_dt
                total_days = date_diff.days + 1

                transportation = payslip.contract_id.transportation
                transportation = transportation / total_days
                payslip.annual_leave_deduction = transportation * payslip.annual_leave_count

                basic = payslip.contract_id.basic
                basic = basic / total_days
                payslip.basic_deduction = basic * payslip.annual_leave_count

                hra = payslip.contract_id.hra
                hra = hra / total_days
                payslip.hra_deduction = hra * payslip.annual_leave_count

                other_allowance = payslip.contract_id.other_allowance
                other_allowance = other_allowance / total_days
                payslip.other_allow_deduction = other_allowance * payslip.annual_leave_count







    
    
    def action_payslip_done(self):
        """Confirming the Loan/Advance amounts and Leave Salaries"""
        res = super(hr_payslip, self).action_payslip_done()
        for slip in self:
            if slip.loan_ids:
                for loan in slip.loan_ids:
                    loan.state = "paid"
            if slip.leave_salary_ids:
                for lv_s in slip.leave_salary_ids:
                    lv_s.state = 'paid'
        return res
        

    def _compute_employee_ot_hours(self):
        for payslip in self:
            if payslip.employee_id and payslip.date_from and payslip.date_to:

                # Getting standard working hours and Days
                day_from = datetime.combine(fields.Date.from_string(payslip.date_from), time.min)
                day_to = datetime.combine(fields.Date.from_string(payslip.date_to), time.max)
                work_data = payslip.employee_id.get_work_days_data(day_from, day_to, compute_leaves=False,
                                                                   calendar=payslip.contract_id.resource_calendar_id)
                payslip.standard_working_hours = work_data['hours']
                payslip.standard_working_days = work_data['days']

                # Getting Leave details
                total_actual_hours = 0
                leave_data = payslip.employee_id.list_leaves(day_from, day_to,
                                                             calendar=payslip.contract_id.resource_calendar_id)
                print("leave_data =============>> ",leave_data)
                unpaid_leaves = 0
                halfpaid_leaves = 0
                paid_leaves = 0
                annual_leave = 0
                date_time_data = []
                for ld in leave_data:                   

                    resource_calendar = ld[2]
                    if resource_calendar.holiday_id and ld[0] not in date_time_data:
                        holiday = resource_calendar.holiday_id
                        date_time_data.append(ld[0])
                        increment_by = 1
                        # if holiday.request_unit_half:
                        #     increment_by = 0.5

                        if holiday.holiday_status_id.unpaid:
                            unpaid_leaves = unpaid_leaves + increment_by
                        elif holiday.holiday_status_id.half_paid:
                            halfpaid_leaves = halfpaid_leaves + increment_by
                        elif holiday.holiday_status_id:
                            paid_leaves = paid_leaves + increment_by
                            total_actual_hours = total_actual_hours + ld[1]

                        if holiday.holiday_status_id.annual_leave:
                            annual_leave = annual_leave + increment_by

                payslip.annual_leave_count = annual_leave
                payslip.paid_leave_count = paid_leaves
                payslip.half_paid_leave_count = halfpaid_leaves
                payslip.unpaid_leave_count = unpaid_leaves

                # We are calculating leave hours by number of paid leaves * 8hours

                leave_hours = total_actual_hours

                # Getting attendance
                total_actual_hours = 0
                attendance_ids = self.env['hr.attendance'].search([('employee_id', '=', payslip.employee_id.id),
                                                                   ('check_in', '>=', payslip.date_from),
                                                                   ('check_in', '<=', payslip.date_to),
                                                                   ('state', '=', 'approved')])

                day_list = []
                for atten in attendance_ids:
                    total_actual_hours += atten.worked_hours
                    check_in_date = atten.check_in.date()
                    if check_in_date not in day_list:
                        day_list.append(check_in_date)

                payslip.total_worked_days = len(day_list)
                payslip.total_worked_hours = total_actual_hours

                # extra hours more than standard hours will be accounted as Lunch hours
                payslip.lunch_hours = len(day_list)

                # Calculating payable hours

                payable_hours = 0

                if (payslip.total_worked_hours - payslip.lunch_hours) > payslip.total_worked_days * 8:

                    payable_hours = payslip.total_worked_days * 8

                else:

                    payable_hours = payslip.total_worked_hours - payslip.lunch_hours

                payable_hours = payable_hours + leave_hours
                payslip.payable_hours = payable_hours

                return
 

        
    def _compute_leave_salary(self):
        leave_salary = self.env['leave.salary'].search([('employee_id', '=', self.employee_id.id),
                                                      ('leave_date', '>=', self.date_from),
                                                      ('leave_date', '<=', self.date_to),
                                                      ('state', '=', 'confirm'),
                                                      ('payment_mode', '=', 'with_payslip')])
        self.leave_salary_ids = leave_salary
        
        
    def _compute_loan(self):
        for payslip in self:
            loans = self.env['loan.payment'].search([('employee_id', '=', payslip.employee_id.id),
                                                          ('due_date', '>=', payslip.date_from),
                                                          ('due_date', '<=', payslip.date_to),
                                                          ('state', '=', 'draft'),
                                                          ('loan_state', '=', 'paid'),])
            payslip.loan_ids = loans
        
        

    def _compute_unpaid_leave_amount(self):

        for payslip in self:

            print("ABBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB")
            print(payslip.unpaid_leave_count, " :: payslip.unpaid_leave_count")

            if payslip.unpaid_leave_count > 0.01:
                date_from_dt = fields.Datetime.from_string(payslip.date_from)
                date_to_dt = fields.Datetime.from_string(payslip.date_to)
                date_diff = date_to_dt - date_from_dt
                total_days = date_diff.days + 1
                gross_salary = payslip.contract_id.wage
                unpaid_leave_amount = (gross_salary / total_days) * payslip.unpaid_leave_count
                payslip.unpaid_leave_amount = unpaid_leave_amount

            if payslip.half_paid_leave_count > 0.01:
                date_from_dt = fields.Datetime.from_string(payslip.date_from)
                date_to_dt = fields.Datetime.from_string(payslip.date_to)
                date_diff = date_to_dt - date_from_dt
                total_days = date_diff.days + 1
                gross_salary = payslip.contract_id.wage
                half_piad_leave_amount = (gross_salary / total_days)
                half_piad_leave_amount = half_piad_leave_amount / 2.00
                half_piad_leave_amount = half_piad_leave_amount * payslip.half_paid_leave_count
                payslip.half_piad_leave_amount = half_piad_leave_amount




    is_fixed_salary = fields.Boolean(related="struct_id.is_fixed_salary", string="Is Fixed Salary?")
    leave_salary_ids = fields.One2many('leave.salary', 'payslip_id', compute='_compute_leave_salary',
                                      string='Leave Salary', store=True)
    loan_ids = fields.One2many('loan.payment', 'payslip_id', string='Loan EMI')
    
    
#     total_hours = fields.Char(string="Total Hours", compute='_compute_employee_total_hours')
    standard_working_hours = fields.Float(string="Working Hours")
    standard_working_days = fields.Float(string="Working Days")

    total_worked_days = fields.Float(string="Total Worked Days")
    total_worked_hours = fields.Float(string="Total Worked Hours")
    
    total_ot_hours = fields.Float(string="Total Overtime Hours")

    paid_leave_count = fields.Float(string="Paid Leave")
    unpaid_leave_count = fields.Float(string="Unpaid Leave")
    unpaid_leave_amount = fields.Float(string="Unpaid Amount")

    half_paid_leave_count = fields.Float(string="Half Paid Leave")
    half_piad_leave_amount = fields.Float(string="Half paid Amount")
    
    date_of_join = fields.Date('Date of Joining')



    attendance_from = fields.Date('Attendance From')
    attendance_to = fields.Date('Attendance To')

    annual_leave_count = fields.Float(string="Annual Leave")
    annual_leave_deduction = fields.Float(string="Transportation Deduction.")
    basic_deduction = fields.Float(string="Basic Deduction")
    hra_deduction = fields.Float(string="HRA Deduction")

    transportation_deduction = fields.Float('Transportation Deduction')
    other_allow_deduction = fields.Float('Other Allowances Deduction')
    credit_note = fields.Boolean(string='Credit Note',
                                 help="Indicates this payslip has "
                                      "a refund of another")
    lunch_hours = fields.Float(string="Lunch Hours")
    payable_hours = fields.Float(string="Payable Hours")


    #Approval Mechnaism

    def get_slip_line_vals(self):

        for rec in self:
            for line in rec.line_ids:
                if rec.employee_id == line.employee_id:
                    if line.code == 'GROSS':
                        rec.gross = line.total
                    if line.code == 'NET':
                        rec.net_salary = line.total


    def _compute_can_approve(self):
        for paylsip in self:
            can_approve = False
            if paylsip.payslip_run_id and paylsip.state in ('draft', 'cancel'):
                can_approve = paylsip.payslip_run_id.can_approve
            paylsip.can_approve = can_approve

    def _compute_can_cancel(self):
        for paylsip in self:
            can_cancel = False
            if paylsip.payslip_run_id and paylsip.state in ('draft', 'verify'):
                can_cancel = paylsip.payslip_run_id.can_approve
            paylsip.can_cancel = can_cancel

    gross = fields.Float('Gross', compute='get_slip_line_vals')
    net_salary = fields.Float('Net Salary', compute='get_slip_line_vals')
    can_approve = fields.Boolean("Can Approve", compute='_compute_can_approve')
    can_cancel = fields.Boolean("Can Approve", compute='_compute_can_cancel')
    state = fields.Selection(selection_add=[('verify', 'Verified')])

    def action_payslip_verified(self):
        return self.write({'state': 'verify'})





# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
