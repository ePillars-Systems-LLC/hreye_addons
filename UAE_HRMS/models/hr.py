# -*- coding: utf-8 -*-

from odoo import api, fields, models,_
from odoo.tools.float_utils import float_round
from datetime import datetime
from datetime import timedelta
from collections import defaultdict
from odoo.tools import float_utils
from pytz import utc
# This will generate 16th of days
ROUNDING_FACTOR = 16

class HrExpense(models.Model):
    _inherit = "hr.expense"

    product_id = fields.Many2one(
        'product.product',
        string='Cost Type',
        readonly=True,  # Set as default readonly
        domain=[('can_be_expensed', '=', True)],
        required=True
    )
class Country(models.Model):
    _inherit = 'res.country'
    air_ticket_allowance = fields.Monetary('Air Ticket Allowance For Employees', digits=(16, 2))


class emergency_relation(models.Model):
    _name = 'emergency.relation'
    name = fields.Char('Name')


class division(models.Model):
    _name = 'division'
    name = fields.Char('Name')


class Employment_status(models.Model):
    _name = 'employment.status'
    name = fields.Char('Name')


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    @api.depends('employee_id.parent_id.user_id', 'overtime_status')
    def _compute_can_approve(self):
        logged_user = self.env.user.id
        for attendance in self:
            can_approve = False
            if attendance.employee_id and attendance.employee_id.parent_id:
                if attendance.employee_id.parent_id.user_id and attendance.employee_id.parent_id.user_id.id == logged_user:
                    if attendance.overtime_status == "to_approve":
                        can_approve = True
            attendance.can_approve = can_approve
    
    overtime_status = fields.Selection([('to_approve', 'To Approve'), ('approved', 'Approved')], string='Status',
                             default="to_approve")
    can_approve = fields.Boolean("Can Approve", compute='_compute_can_approve')
   
    def approve(self):
        for attendance in self:
            attendance.overtime_status = 'approved'

class Employee(models.Model):
    _inherit = "hr.employee"

    # @api.model
    # def _default_gm1_get(self):
    #     if self.env.ref('UAE_HRMS.group_gm1').users.ids:
    #         return self.env.ref('UAE_HRMS.group_gm1').users.ids[0]
    #     else:
    #         return False

    # @api.model
    # def _default_gm2_get(self):
    #     if self.env.ref('UAE_HRMS.group_gm2').users.ids:
    #         return self.env.ref('UAE_HRMS.group_gm2').users.ids[0]
    #     else:
    #         return False
    
    current_leave_state = fields.Selection(selection_add=[('validate2', 'Third Approval')],
                            compute='_compute_leave_status', string="Current Leave Status")
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city = fields.Char()
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict',
                               domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict')
    document_count = fields.Float('document_count')

    date_of_join = fields.Date('Date of Joining')
    religion = fields.Char('Religion')
    # asset_ids = fields.One2many('employee.asset','employee_id', string='Assets')
    asset_line_ids = fields.One2many('employee.asset.line', 'employee_id', string='Asset')
   

    personal_identification_number = fields.Char(string="Personal Identification Number")
    address_id = fields.Many2one('res.partner', required=True)
    employment_status = fields.Many2one('employment.status', 'Employment Status')
    employment_division = fields.Many2one('division', 'Division')
    emp_emergency_relation = fields.Many2one('emergency.relation', 'Emergency Relation')
    emp_emergency_email = fields.Char('Emergency Email')
    emp_emergency_detail_ids = fields.One2many('emergency.details', 'emp_id',string='Emergency Contact')
    probation_end_date = fields.Date('Probation End Date')
    payment_type = fields.Selection([('bank', 'Bank'), ('cash', 'Cash'), ('cheque', 'Cheque')], string='Payment Type')
    iban_no = fields.Char(string="IBAN No")

    # new fields added as per the employee master data sheet
    employment_status_date = fields.Date('Employment Status Date')
    job_info_date = fields.Date('Job Information Date')

    passport_start_date = fields.Date('Passport Start Date')
    passport_expiry_date = fields.Date('Passport Expiry Date')

    visa_no = fields.Char(string="Visa No")
    visa_start_date = fields.Date('Visa Start Date')
    visa_end_date = fields.Date('Visa End Date')

    labour_card_no = fields.Char(string="Labour Card No")
    labour_card_issue_date = fields.Date('Labour Card Issue Date')
    labour_card_expiry_date = fields.Date('Labour Card Expiry Date')

    health_card_no = fields.Char(string="Health Card No")
    health_card_issue_date = fields.Date('Health Card Issue Date')
    health_card_expiry_date = fields.Date('Health Card Expiry Date')

    emirates_id_no = fields.Char(string="Emirates Id No")
    emirates_id_expiry_date = fields.Date('Emirates Id expiry Date')
    contract_type = fields.Selection([('limited', 'Limited'), ('unlimited', 'Unlimited')], string='Contract Type')

    airticket_allowance = fields.Selection([('annual', 'Annual')], string='AirTicket Allowance', default="annual")
    airticket_allowance_amount = fields.Float('Amount')
    number_of_persons_eligible = fields.Integer(string="Number of persons eligible", default=1)

    pay_method = fields.Selection([('bank', 'Bank'), ('cash', 'Cash')], string='Pay Method')

    payslip_count = fields.Integer(compute='_compute_payslip_count', string='Payslip Count')
    payslip_count_num = fields.Integer(compute='_compute_payslip_count', string='Payslip Count')
    passport_id = fields.Char('Passport No', groups="hr.group_hr_user")

    agent_id = fields.Char(string="Agent ID")
    bank_account_number = fields.Char(string="Bank Account Number")
    # gm_id1 = fields.Many2one('res.users', default=_default_gm1_get)
    # gm_id2 = fields.Many2one('res.users', default=_default_gm2_get)

    attendance_checked_in = fields.Char('Checked In',compute='compute_check_in')

    # @api.depends('company_id')
    # def _compute_address_id(self):
    #     for employee in self:
    #         address = employee.company_id.partner_id.address_get(['default'])
    #         employee.address_id = address['default'] if address else False

   
    def compute_check_in(self):
        for employee in self:
            check_in = datetime.now().strftime('%Y-%m-%d 00:00:00')
            attendance = self.env['hr.attendance'].search([('employee_id', '=', employee.id),
                                                           ('check_in', '>=', check_in),
                                                           ],limit=1)
            if attendance and not attendance.check_out:
                employee.attendance_checked_in = 'check_in'
            else:
                employee.attendance_checked_in = 'check_out'

    def open_employee_expenses(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'My Expenses',
            'res_model': 'hr.expense',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {
                'default_employee_id': self.id,
            }
        }
    
    def _compute_payslip_count(self):
        for employee in self:
            employee.payslip_count = len(employee.slip_ids)
            employee.payslip_count_num = len(employee.slip_ids)
   
    # def name_search(self, name, args=None, operator='ilike', limit=100):
    #     if self._context.get('deactivated_employees'):
    #         new_args = ['|', ('active', '=', False), ('active', '=', True)]
    #         args = args + new_args
    #     return super(Employee, self).name_search(name, args=args, operator=operator, limit=limit)

   
    def _compute_leaves_count(self):
        all_leaves = self.env['hr.leave.report'].read_group([
            ('employee_id', 'in', self.ids),
            ('holiday_status_id.allocation_type', '!=', 'no'),
            ('state', '=', 'validate'),
            ('holiday_status_id.annual_leave', '=', True)
        ], fields=['number_of_days', 'employee_id'], groupby=['employee_id'])
        mapping = dict([(leave['employee_id'][0], leave['number_of_days']) for leave in all_leaves])
        for employee in self:
            employee.leaves_count = float_round(mapping.get(employee.id, 0), precision_digits=2)

class Contract(models.Model):
    _inherit = 'hr.contract'

    wage = fields.Monetary('Gross', digits=(16, 2), required=True, track_visibility="onchange",
                           help="Employee's monthly gross.")
    basic = fields.Monetary('Basic', digits=(16, 2), required=True, track_visibility="onchange",
                            help="Employee's monthly basic wage.")
    hra = fields.Monetary('Housing allowance', digits=(16, 2), required=True, track_visibility="onchange")
    transportation = fields.Monetary('Transportation', digits=(16, 2), required=True, track_visibility="onchange")
    other_allowance = fields.Monetary('Other Allowance', digits=(16, 2), required=True, track_visibility="onchange")

    @api.onchange('basic', 'hra', 'transportation','other_allowance')
    def onchange_salary(self):
        self.wage = self.basic + self.hra + self.transportation + self.other_allowance

    def get_all_structures(self):
        """
        @return: the structures linked to the given contracts, ordered by
        hierarchy (parent=False first,then first level children and so on)
        and without duplicate
        """
        structures = self.structure_type_id.default_struct_id.id
        if not structures:
            return []
        return structures
        # YTI TODO return browse records
        # return list(set(structures._get_parent_structure().ids))

    # def _get_parent_structure(self):
    #     """Function for getting Parent Structure"""
    #     parent = self.structure_type_id.default_struct_id
    #     if parent:
    #         parent = parent._get_parent_structure()
    #     return parent + self

class hr_job(models.Model):
    _inherit = "hr.job"

    parent_id = fields.Many2one('hr.job', string='Parent')


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    
    def _compute_can_approve(self):
        logged_user = self.env.user.id
        for attendance in self:
            can_approve = False
            if attendance.employee_id and attendance.employee_id.parent_id:
                if attendance.employee_id.parent_id.user_id and attendance.employee_id.parent_id.user_id.id == logged_user:
                    if attendance.state == "to_approve":
                        can_approve = True
            attendance.can_approve = can_approve

    state = fields.Selection([('to_approve', 'To Approve'), ('approved', 'Approved')], string='Status',
                             default="to_approve")
    can_approve = fields.Boolean("Can Approve", compute='_compute_can_approve')

   
    def approve(self):
        for attendance in self:
            attendance.state = 'approved'

class EmergencyDetails(models.Model):
    _name = 'emergency.details'

    name = fields.Char('Name')
    relation_id = fields.Many2one('emergency.relation', 'Relationship')
    email = fields.Char('Email')
    phone = fields.Char('Phone')
    emp_id = fields.Many2one('hr.employee','Employee')
    type = fields.Selection([('home', 'Home'), ('uae', 'UAE')], 'Home/UAE')


class ResourceMixin(models.AbstractModel):
    """Inherit resource_mixin for getting Worked Days"""
    _inherit = "resource.mixin"

    def get_work_days_data(self, from_datetime, to_datetime,
                           compute_leaves=True, calendar=None, domain=None):
        """
            By-default the resource calendar is used, but it can be
            changed using the `calendar` argument.

            `domain` is used in order to recognise the leaves to take,
            None means default value ('time_type', '=', 'leave')

            Returns a dict {'days': n, 'hours': h} containing the
            quantity of working time expressed as days and as hours.
        """
        resource = self.resource_id
        calendar = calendar or self.resource_calendar_id
        # naive datetime are made explicit in UTC
        if not from_datetime.tzinfo:
            from_datetime = from_datetime.replace(tzinfo=utc)
        if not to_datetime.tzinfo:
            to_datetime = to_datetime.replace(tzinfo=utc)
        # total hours per day: retrieve attendances with one extra day margin,
        # in order to compute the total hours on the first and last days
        from_full = from_datetime - timedelta(days=1)
        to_full = to_datetime + timedelta(days=1)
        intervals = calendar._attendance_intervals_batch(from_full, to_full,
                                                         resource)
        day_total = defaultdict(float)
        for start, stop, meta in intervals[resource.id]:
            day_total[start.date()] += (stop - start).total_seconds() / 3600
        # actual hours per day
        if compute_leaves:
            intervals = calendar._work_intervals_batch(from_datetime,
                                                       to_datetime, resource,
                                                       domain)
        else:
            intervals = calendar._attendance_intervals_batch(from_datetime,
                                                             to_datetime,
                                                             resource)
        day_hours = defaultdict(float)
        for start, stop, meta in intervals[resource.id]:
            day_hours[start.date()] += (stop - start).total_seconds() / 3600
        # compute number of days as quarters
        days = sum(
            float_utils.round(ROUNDING_FACTOR * day_hours[day] / day_total[
                day]) / ROUNDING_FACTOR
            for day in day_hours
        )
        return {
            'days': days,
            'hours': sum(day_hours.values()),
        }
