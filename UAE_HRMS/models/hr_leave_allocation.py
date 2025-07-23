# -*- coding: utf-8 -*-

from datetime import datetime, time
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.addons.resource.models.resource import HOURS_PER_DAY


class HolidaysAllocation(models.Model):
    
    _inherit = "hr.leave.allocation"
    
    interval_unit = fields.Selection([
        ('daily', 'Daily'),
        ('weeks', 'Week(s)'),
        ('months', 'Month(s)'),
        ('years', 'Year(s)')
        ], string="Unit of time between two intervals", default='daily', readonly=True, 
                states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    number_per_interval = fields.Float("Number of unit per interval", 
                                       readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, 
                                       default=1,
                                       digits=(4,4))
    number_of_days = fields.Float('Number of Days', track_visibility='onchange', digits=(4,4),
        help='Duration in days. Reference field to use when necessary.')
    number_of_days_display = fields.Float(
        'Duration (days)', compute='_compute_number_of_days_display',
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},  digits=(4,4),
        help="UX field allowing to see and modify the allocation duration, computed in days.")

    last_updated_date = fields.Date("Leave As Off", track_visibility='onchange')
    emp_joining_date = fields.Date('Joining Date',related="employee_id.date_of_join")

    @api.onchange('employee_id')
    def _onchange_employee(self):
       super(HolidaysAllocation, self)._onchange_employee()
       self.last_updated_date = False
    
    @api.model
    def _update_accrual(self):
        """
            Method called by the cron task in order to increment the number_of_days when
            necessary.
        """
        today = fields.Date.from_string(fields.Date.today())

        holidays = self.search([('accrual', '=', True), ('state', '=', 'validate'), ('holiday_type', '=', 'employee'),
                                '|', ('date_to', '=', False), ('date_to', '>', fields.Datetime.now()),
                                '|', ('nextcall', '=', False), ('nextcall', '<=', today)])

        for holiday in holidays:
            values = {}

            delta = relativedelta(days=0)
            if holiday.interval_unit == 'daily':
                delta = relativedelta(days=holiday.interval_number)
            if holiday.interval_unit == 'weeks':
                delta = relativedelta(weeks=holiday.interval_number)
            if holiday.interval_unit == 'months':
                delta = relativedelta(months=holiday.interval_number)
            if holiday.interval_unit == 'years':
                delta = relativedelta(years=holiday.interval_number)

            values['nextcall'] = (holiday.nextcall if holiday.nextcall else today) + delta

            period_start = datetime.combine(today, time(0, 0, 0)) - delta
            period_end = datetime.combine(today, time(0, 0, 0))

            # We have to check when the employee has been created
            # in order to not allocate him/her too much leaves
            start_date = holiday.employee_id._get_date_start_work()
            # If employee is created after the period, we cancel the computation
            if period_end <= start_date:
                holiday.write(values)
                continue

            # If employee created during the period, taking the date at which he has been created
            if period_start <= start_date:
                period_start = start_date

            worked = holiday.employee_id.get_work_days_data(period_start, period_end, domain=[('holiday_id.holiday_status_id.unpaid', '=', True), ('time_type', '=', 'leave')])['days']
            left = holiday.employee_id.get_leave_days_data(period_start, period_end, domain=[('holiday_id.holiday_status_id.unpaid', '=', True), ('time_type', '=', 'leave')])['days']
            prorata = worked / (left + worked) if worked else 0

            days_to_give = holiday.number_per_interval
            if holiday.unit_per_interval == 'hours':
                # As we encode everything in days in the database we need to convert
                # the number of hours into days for this we use the
                # mean number of hours set on the employee's calendar
                days_to_give = days_to_give / (holiday.employee_id.resource_calendar_id.hours_per_day or HOURS_PER_DAY)

            values['number_of_days'] = holiday.number_of_days + days_to_give * prorata
            if holiday.accrual_limit > 0:
                values['number_of_days'] = min(values['number_of_days'], holiday.accrual_limit)

            holiday.write(values)
            
            
    @api.multi
    @api.constrains('holiday_status_id')
    def _check_leave_type_validity(self):
        print ("pppp")
#         for allocation in self:
#             if allocation.holiday_status_id.validity_start and allocation.holiday_status_id.validity_stop:
#                 vstart = allocation.holiday_status_id.validity_start
#                 vstop = allocation.holiday_status_id.validity_stop
#                 today = fields.Date.today()
# 
#                 if vstart > today or vstop < today:
#                     raise UserError(_('You can allocate %s only between %s and %s') % (allocation.holiday_status_id.display_name,
#                                                                                   allocation.holiday_status_id.validity_start, allocation.holiday_status_id.validity_stop))
