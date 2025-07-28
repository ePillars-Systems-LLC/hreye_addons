{
    'name': 'HR Dashboard',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Advanced HR Dashboard with Employee and Manager Views',
    'description': """
        HR Dashboard Module for Odoo 18
        ================================
        
        Features:
        - Manager Dashboard: Leaves/Expenses approval, Employee statistics, Attendance overview
        - Employee Dashboard: Personal leaves/expenses, attendance tracking
        - Real-time data updates using OWL JS
        - Role-based access control
    """,
    'author': 'Your Company',
    'website': 'https://www.epillars.com',
    'depends': ['base', 'hr', 'hr_holidays', 'hr_expense', 'hr_attendance'],
    'data': [
        'views/hr_dashboard_views.xml',
        'views/hr_dashboard_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_employee_dashboard/static/src/js/hr_employee_dashboard.js',
            'hr_employee_dashboard/static/src/xml/hr_employee_dashboard.xml',
            'hr_employee_dashboard/static/src/css/hr_employee_dashboard.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
}
