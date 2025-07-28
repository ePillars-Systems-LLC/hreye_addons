from odoo import models, fields, api
from datetime import datetime, timedelta

class HRDashboard(models.TransientModel):
    _name = 'hr.dashboard'
    _description = 'HR Dashboard Model'

    @api.model
    def get_dashboard_stats(self):
        """Get comprehensive dashboard statistics"""
        user = self.env.user
        is_manager = user.has_group('hr.group_hr_manager') or user.has_group('hr.group_hr_user')
        
        today = datetime.now().date()
        first_day_month = today.replace(day=1)
        
        stats = {
            'is_manager': is_manager,
            'current_date': today.strftime('%Y-%m-%d'),
        }
        
        if is_manager:
            # Manager statistics
            stats.update({
                'pending_leaves': self.env['hr.leave'].search_count([('state', '=', 'confirm')]),
                'pending_expenses': self.env['hr.expense'].search_count([('state', '=', 'submit')]),
                'approved_leaves_month': self.env['hr.leave'].search_count([
                    ('state', '=', 'validate'),
                    ('create_date', '>=', first_day_month)
                ]),
                'approved_expenses_month': self.env['hr.expense'].search_count([
                    ('state', '=', 'done'),
                    ('create_date', '>=', first_day_month)
                ]),
                'total_employees': self.env['hr.employee'].search_count([('active', '=', True)]),
                'present_today': self._get_present_employees_count(),
                'absent_today': self._get_absent_employees_count(),
            })
        else:
            # Employee statistics
            employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
            if employee:
                stats.update({
                    'employee_id': employee.id,
                    'employee_name': employee.name,
                    'my_pending_leaves': self.env['hr.leave'].search_count([
                        ('employee_id', '=', employee.id),
                        ('state', '=', 'confirm')
                    ]),
                    'my_pending_expenses': self.env['hr.expense'].search_count([
                        ('employee_id', '=', employee.id),
                        ('state', '=', 'submit')
                    ]),
                    'my_approved_leaves_month': self.env['hr.leave'].search_count([
                        ('employee_id', '=', employee.id),
                        ('state', '=', 'validate'),
                        ('create_date', '>=', first_day_month)
                    ]),
                    'my_approved_expenses_month': self.env['hr.expense'].search_count([
                        ('employee_id', '=', employee.id),
                        ('state', '=', 'done'),
                        ('create_date', '>=', first_day_month)
                    ]),
                    'attendance_today': self._get_employee_attendance_today(employee.id),
                })
        
        return stats

    def _get_present_employees_count(self):
        """Get count of employees present today"""
        today = datetime.now().date()
        present_employees = self.env['hr.attendance'].search([
            ('check_in', '>=', today),
            ('check_out', '=', False)
        ])
        return len(present_employees.mapped('employee_id'))

    def _get_absent_employees_count(self):
        """Get count of employees absent today"""
        today = datetime.now().date()
        all_employees = self.env['hr.employee'].search([('active', '=', True)])
        present_employee_ids = self.env['hr.attendance'].search([
            ('check_in', '>=', today)
        ]).mapped('employee_id.id')
        
        return len(all_employees) - len(set(present_employee_ids))

    def _get_employee_attendance_today(self, employee_id):
        """Get employee's attendance status for today"""
        today = datetime.now().date()
        attendance = self.env['hr.attendance'].search([
            ('employee_id', '=', employee_id),
            ('check_in', '>=', today)
        ], limit=1)
        
        if not attendance:
            return {'status': 'not_checked_in', 'check_in': None, 'check_out': None}
        
        return {
            'status': 'checked_in' if not attendance.check_out else 'checked_out',
            'check_in': attendance.check_in.strftime('%H:%M') if attendance.check_in else None,
            'check_out': attendance.check_out.strftime('%H:%M') if attendance.check_out else None,
        }
