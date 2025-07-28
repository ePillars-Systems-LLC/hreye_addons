from odoo import http
from odoo.http import request
import json
import base64
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class HRDashboardController(http.Controller):

    @http.route('/hr_employee_dashboard/dashboard_employee_data', type='json', auth='user')
    def get_dashboard_employee_data(self, user_id=None):
        """Get dashboard data in the format expected by the frontend"""
        user = request.env.user
        is_manager = user.has_group('hr.group_hr_manager') or user.has_group('hr.group_hr_user')
        
        # Get employee record
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
        
        # Base data structure
        data = {
            'dash_employee_id': employee.id if employee else False,
            'dash_image': self._get_user_image(employee),
            'dash_job_name': employee.job_id.name if employee and employee.job_id else 'Employee',
            'dash_name': user.name,
            'dash_leaves_count': self._get_user_remaining_leaves(employee),
            'is_hr_manager': is_manager,
            'dash_holidays_filter_report_view_id': False,
            'dash_holidays_filter_view_id': False,
        }
        
        # Add demographic data
        data.update(self._get_demographic_data())
        
        # Add chart data
        data.update(self._get_chart_data())
        
        # Add role-specific data
        if is_manager:
            data.update(self._get_manager_specific_metrics())
            data.update({
                # Set employee metrics to 0 for managers
                'employee_own_leaves_to_approve': 0,
                'employee_own_expenses_to_approve': 0,
                'employee_own_leaves_approved': 0,
                'employee_own_expenses_approved': 0,
                'employee_own_attendance_status': 'N/A',
                'employee_own_check_in_time': False,
                'employee_own_check_out_time': False,
            })
        else:
            data.update(self._get_employee_specific_metrics(employee))
            data.update({
                # Set manager metrics to 0 for employees
                'manager_leaves_to_approve': 0,
                'manager_expenses_to_approve': 0,
                'manager_leaves_approved': 0,
                'manager_expenses_approved': 0,
                'manager_total_employees': 0,
                'manager_employees_checked_in': 0,
                'manager_employees_absent': 0,
            })
        
        # Add monthly statistics
        data.update(self._get_monthly_statistics())
        # Add contact information
        if employee:
            data.update({
                'dash_employee_phone': employee.work_phone or employee.mobile_phone or False,
                'dash_employee_mobile': employee.mobile_phone or employee.work_phone or False,
                'dash_employee_email': employee.work_email or user.email or False,
                'dash_employee_department_name': employee.department_id.name if employee.department_id else False,
                'dash_manager_name': employee.parent_id.name if employee.parent_id else False,
            })
        else:
            data.update({
                'dash_employee_phone': False,
                'dash_employee_mobile': False,
                'dash_employee_email': user.email or False,
                'dash_employee_department_name': False,
                'dash_manager_name': False,
            })
        return [data]  # Return as array to match expected format

    def _get_user_image(self, employee):
        """Get user's image as base64"""
        if employee and employee.image_1920:
            return employee.image_1920
        return False

    def _get_user_remaining_leaves(self, employee):
        """Get remaining leaves for user"""
        if not employee:
            return 0
        
        # Get current leave allocations
        allocations = request.env['hr.leave.allocation'].search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate')
        ])
        
        total_allocated = sum(allocations.mapped('number_of_days'))
        
        # Get used leaves
        used_leaves = request.env['hr.leave'].search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate')
        ])
        
        total_used = sum(used_leaves.mapped('number_of_days'))
        
        return max(0, total_allocated - total_used)

    def _get_demographic_data(self):
        """Get demographic breakdown data"""
        employees = request.env['hr.employee'].sudo().search([('active', '=', True)])
        
        # Gender counts
        male_count = len(employees.filtered(lambda e: e.gender == 'male'))
        female_count = len(employees.filtered(lambda e: e.gender == 'female'))
        
        # Age demographics
        today = datetime.now().date()
        age_data = {
            'dash_age_les_24_m': 0, 'dash_age_les_24_f': 0,
            'dash_age_25_34_m': 0, 'dash_age_25_34_f': 0,
            'dash_age_35_44_m': 0, 'dash_age_35_44_f': 0,
            'dash_age_45_54_m': 0, 'dash_age_45_54_f': 0,
            'dash_age_gre_54_m': 0, 'dash_age_gre_54_f': 0,
        }
        
        for employee in employees:
            if not employee.birthday:
                continue
                
            age = relativedelta(today, employee.birthday).years
            gender_suffix = '_m' if employee.gender == 'male' else '_f'
            
            if age < 25:
                age_data[f'dash_age_les_24{gender_suffix}'] += 1
            elif 25 <= age <= 34:
                age_data[f'dash_age_25_34{gender_suffix}'] += 1
            elif 35 <= age <= 44:
                age_data[f'dash_age_35_44{gender_suffix}'] += 1
            elif 45 <= age <= 54:
                age_data[f'dash_age_45_54{gender_suffix}'] += 1
            else:
                age_data[f'dash_age_gre_54{gender_suffix}'] += 1
        
        return {
            'dash_male_count': male_count,
            'dash_female_count': female_count,
            **age_data
        }

    def _get_chart_data(self):
        """Get data for charts"""
        employees = request.env['hr.employee'].sudo().search([('active', '=', True)])
        
        # Nationality data
        nationality_data = {}
        for employee in employees:
            country = employee.country_id.name if employee.country_id else 'Unknown'
            nationality_data[country] = nationality_data.get(country, 0) + 1
        
        # Sort and get top 5 nationalities
        top_nationalities = sorted(nationality_data.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Department data
        department_data = {}
        for employee in employees:
            dept = employee.department_id.name if employee.department_id else 'No Department'
            department_data[dept] = department_data.get(dept, 0) + 1
        
        # Sort departments by count (descending) and limit to top 10
        sorted_departments = sorted(department_data.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Extract names and counts as separate arrays
        department_names = [item[0] for item in sorted_departments] if sorted_departments else []
        department_counts = [item[1] for item in sorted_departments] if sorted_departments else []
        
        # Position data
        position_data = {}
        for employee in employees:
            job = employee.job_id.name if employee.job_id else 'No Position'
            position_data[job] = position_data.get(job, 0) + 1
        
        # Sort positions by count (descending) and limit to top 10
        sorted_positions = sorted(position_data.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Extract names and counts as separate arrays
        position_names = [item[0] for item in sorted_positions] if sorted_positions else []
        position_counts = [item[1] for item in sorted_positions] if sorted_positions else []
        
        # Attendance data for today
        today = datetime.now().date()
        total_employees = len(employees)
        
        # Get unique employees who checked in today
        today_attendances = request.env['hr.attendance'].search([
            ('check_in', '>=', today),
            ('employee_id', 'in', employees.ids)
        ])
        present_employees = len(set(today_attendances.mapped('employee_id.id')))
        
        return {
            'dash_top_nationalities': [item[0] for item in top_nationalities] if top_nationalities else [],
            'dash_top_nationalities_count': [item[1] for item in top_nationalities] if top_nationalities else [],
            'dash_department_name': department_names,
            'dash_department_count': department_counts,
            'dash_position_name': position_names,
            'dash_position_count': position_counts,
            'dash_headcount': total_employees,
            'dash_todays_attendance': present_employees,
        }

    def _get_manager_data(self):
        """Get manager-specific data"""
        today = datetime.now().date()
        
        return {
            'dash_leaves_to_approve': request.env['hr.leave'].search_count([('state', '=', 'confirm')]),
            'dash_allowcations_to_approve': request.env['hr.leave.allocation'].search_count([('state', '=', 'confirm')]),
            'dash_expenses_to_approve': request.env['hr.expense'].search_count([('state', '=', 'submit')]),
            'dash_expenses_approved': request.env['hr.expense'].search_count([
                ('state', '=', 'done'),
                ('create_date', '>=', today.replace(day=1))
            ]),
        }

    def _get_monthly_statistics(self):
        """Get monthly statistics for the last 6 months"""
        months = []
        leaves_data = []
        expenses_data = []
        
        for i in range(6):
            month_start = datetime.now().replace(day=1) - relativedelta(months=i)
            month_end = month_start + relativedelta(months=1) - timedelta(days=1)
            
            months.insert(0, month_start.strftime('%b %Y'))
            
            # Count approved leaves for this month
            leaves_count = request.env['hr.leave'].search_count([
                ('state', '=', 'validate'),
                ('create_date', '>=', month_start),
                ('create_date', '<=', month_end)
            ])
            leaves_data.insert(0, leaves_count)
            
            # Count approved expenses for this month
            expenses_count = request.env['hr.expense'].search_count([
                ('state', '=', 'done'),
                ('create_date', '>=', month_start),
                ('create_date', '<=', month_end)
            ])
            expenses_data.insert(0, expenses_count)
        
        return {
            'monthly_labels': months,
            'monthly_leaves_data': leaves_data,
            'monthly_expenses_data': expenses_data,
        }

    def _get_manager_specific_metrics(self):
        """Get manager-specific metrics"""
        today = datetime.now().date()
        first_day_month = today.replace(day=1)
        
        # Get all active employees
        all_employees = request.env['hr.employee'].sudo().search([('active', '=', True)])
        total_employees = len(all_employees)
        
        # Get attendance data for today
        today_attendances = request.env['hr.attendance'].search([
            ('check_in', '>=', today),
            ('employee_id', 'in', all_employees.ids)
        ])
        employees_checked_in = len(set(today_attendances.mapped('employee_id.id')))
        employees_absent = total_employees - employees_checked_in
        
        return {
            'manager_leaves_to_approve': request.env['hr.leave'].search_count([
                ('state', '=', 'confirm')
            ]),
            'manager_expenses_to_approve': request.env['hr.expense.sheet'].search_count([
                ('state', '=', 'submit')
            ]),
            'manager_leaves_approved': request.env['hr.leave'].search_count([
                ('state', '=', 'validate'),
                ('create_date', '>=', first_day_month)
            ]),
            'manager_expenses_approved': request.env['hr.expense'].search_count([
                ('state', '=', 'done'),
                ('create_date', '>=', first_day_month)
            ]),
            'manager_total_employees': total_employees,
            'manager_employees_checked_in': employees_checked_in,
            'manager_employees_absent': employees_absent,
        }

    def _get_employee_specific_metrics(self, employee):
        """Get employee-specific metrics"""
        if not employee:
            return {
                'employee_own_leaves_to_approve': 0,
                'employee_own_expenses_to_approve': 0,
                'employee_own_leaves_approved': 0,
                'employee_own_expenses_approved': 0,
                'employee_own_attendance_status': 'No Employee Record',
                'employee_own_check_in_time': False,
                'employee_own_check_out_time': False,
            }
    
        today = datetime.now().date()
        first_day_month = today.replace(day=1)
    
        # Get employee's own attendance for today
        attendance_today = request.env['hr.attendance'].search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', today)
        ], limit=1, order='check_in desc')
    
        attendance_status = 'Not Checked In'
        check_in_time = False
        check_out_time = False
    
        if attendance_today:
            if attendance_today.check_out:
                attendance_status = 'Checked Out'
                check_out_time = attendance_today.check_out.strftime('%H:%M')
            else:
                attendance_status = 'Checked In'
            check_in_time = attendance_today.check_in.strftime('%H:%M')
    
        return {
            'employee_own_leaves_to_approve': request.env['hr.leave'].search_count([
                ('employee_id', '=', employee.id),
                ('state', '=', 'confirm')
            ]),
            'employee_own_expenses_to_approve': request.env['hr.expense'].search_count([
                ('employee_id', '=', employee.id),
                ('state', '=', 'submit')
            ]),
            'employee_own_leaves_approved': request.env['hr.leave'].search_count([
                ('employee_id', '=', employee.id),
                ('state', '=', 'validate'),
                ('create_date', '>=', first_day_month)
            ]),
            'employee_own_expenses_approved': request.env['hr.expense'].search_count([
                ('employee_id', '=', employee.id),
                ('state', '=', 'done'),
                ('create_date', '>=', first_day_month)
            ]),
            'employee_own_attendance_status': attendance_status,
            'employee_own_check_in_time': check_in_time,
            'employee_own_check_out_time': check_out_time,
        }
