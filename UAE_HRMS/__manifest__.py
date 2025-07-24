{
    'name': 'UAE HRMS',
    'version': '18.0',
    'category': 'Generic Modules/Human Resources',    
    'summary': 'Sign',
    'description': """UAE HRMS Localization""",
    'author': "ePillars Systems LLC",
    'website': 'https://www.epillars.com',
    'depends': [
       'hr','hr_contract','hr_holidays', 'hr_attendance','hr_expense','hr_payroll'
    ],
    'data': [
        'security/security_group.xml',
        'wizard/payroll_report_wiz.xml',
        # 'data/hr_payroll_data.xml',
        'views/hr_gratuity_view.xml',
        'views/hr_resignation_view.xml',
        'views/leave_salary_view.xml',  
        'views/hr_payroll_view.xml',  
        'views/wps_view.xml',     
        'views/employee_assets_view.xml',
        'views/hr_leave_type.xml',             
        'views/hr_view.xml',
        'views/hr_forms_view.xml',
        'views/loan_application_view.xml',
        'views/hr_employee_request_view.xml',
        'security/ir.model.access.csv',
        'views/approval_matrix_view.xml',
        'data/ir_sequence_data.xml'       
    ],
    'installable': True,
    'auto_install': False,   
    'application': True,
}
