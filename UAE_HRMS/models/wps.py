
from datetime import datetime
from odoo import api, fields, models
import io
import base64
from odoo.tools import mute_logger, pycompat
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
# class res_currency(models.Model):
#     _inherit = "res.company"
#
#     employer_unique_id = fields.Char(string='Employer Unique ID (WPS)')
#     employer_bank_code = fields.Char(string='Employer Bank code (WPS)')

class payroll_wps(models.Model):
    _name = 'payroll.wps'
    _inherit = 'mail.thread'
    
    date = fields.Date('Date', required=True)
    batch_ids = fields.Many2many('hr.payslip.run',
                    'hr_payslip_run_wps_rel', 
                    'wps_id', 'hr_payslip_run_id' ,string="Batches")
    
    state= fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Generated'),
        ], string='Status', track_visibility='onchange', default='draft')
    file_name = fields.Char('File Name', size=256, readonly=True)
    file_download = fields.Binary('Download payroll', readonly=True)

    employer_unique_id = fields.Char(string='Employer Unique ID (WPS)')
    employer_bank_code = fields.Char(string='Employer Bank code (WPS)')

    def do_generate(self):
        if not self.batch_ids:
            return True

        output = io.BytesIO()
        writer = pycompat.csv_writer(output, quoting=1)

        employer_unique_id = ""
        employer_bank_code = ""
        data = []
        salary_month = ""
        count = 0
        total_amount = 0
        for batch in self.batch_ids:
            for payslip in batch.slip_ids:

                if payslip.state == 'done':
                    vals = []
                    count = count + 1
                    #A
                    vals.append('EDR')

                    #B
                    vals.append(payslip.employee_id.personal_identification_number)

                    #C
                    vals.append(payslip.employee_id.agent_id)

                    #D
                    vals.append(payslip.employee_id.bank_account_number)

                    #E
                    vals.append(payslip.date_from.strftime('%Y-%m-%d'))
                    salary_month = payslip.date_from.strftime('%m%Y')

                    #F
                    vals.append(payslip.date_from.strftime('%Y-%m-%d'))

                    #G
                    #find number of days
                    delta = payslip.date_to - payslip.date_from
                    vals.append(delta.days + 1)

                    #H
                    vals.append(payslip.contract_id.wage)

                    #I
                    vals.append(payslip.contract_id.wage)
                    total_amount = total_amount + payslip.contract_id.wage

                    #J
                    vals.append(payslip.unpaid_leave_count)

                    data.append(vals)
                    writer.writerow(vals)

        print("data ======>> ", data)
        #writer.writerow(data)

        vals = []

        #A
        vals.append("SCR")

        #B
        vals.append(self.employer_unique_id)

        #C
        vals.append(self.employer_bank_code)

        #D
        vals.append(datetime.today().strftime('%Y-%m-%d'))

        #E
        vals.append(datetime.today().strftime('%H%M'))

        #F
        vals.append(salary_month)

        #G
        vals.append(count)

        #H
        vals.append(total_amount)

        #I
        vals.append('AED')

        #J
        vals.append('SALARY')

        writer.writerow(vals)

        self.file_download = base64.b64encode(output.getvalue())
        self.file_name = "WPS.csv"
        self.state = 'done'

    
    
    
    @api.onchange('date')
    def get_last_working_date(self):
        self.batch_ids = False
        batches = self.env['hr.payslip.run'].search([('date_start', '=', self.date), 
                                                         ('state', '=', 'close')])
        
        print ("batches =============>>> ", batches)
        if batches:
            
            self.batch_ids = batches.ids
        
            
    
   
  
