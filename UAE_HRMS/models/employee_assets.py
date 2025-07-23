# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime

class employee_asset(models.Model):  
    _name = 'employee.asset'
    _description = 'Assets'
    _inherit = ['mail.thread']

    name = fields.Char('Name')
    date_of_purchase = fields.Date('Date of Purchase')
    active = fields.Boolean("Active", default=True)
    
    type = fields.Char('Type')
    brand = fields.Char('Brand')
    model = fields.Char('Model')
    serial_number = fields.Char('Serial Number')
    date_of_allocation = fields.Date('Date of Allocation',track_visibility='always')
    date_returned = fields.Date('Date Returned',track_visibility='always')
    employee_id = fields.Many2one('hr.employee','Employee',track_visibility='always')



class employee_asset_line(models.Model):
    _name = 'employee.asset.line'
    _description = 'Assets'
    _inherit = ['mail.thread']


    asset_id = fields.Many2one('employee.asset','Asset',required=True,domain=[('employee_id','=',False)])
    name = fields.Char(related='asset_id.name')
    date_of_allocation = fields.Date('Date of Allocation',required=True,default=fields.Date.today)
    date_returned = fields.Date('Date Returned',default=fields.Date.today)
    employee_id = fields.Many2one('hr.employee')
    state = fields.Selection([('not returned','Not Returned'),('returned','Returned')],default='not returned',string='Status')


    def update_asset(self,asset,employee_id,allocated_date):
        if asset and employee_id:
            asset.write({'employee_id':employee_id.id})
            if allocated_date:
                asset.write({'date_of_allocation':allocated_date})

    @api.model
    def create(self, vals_list):
              res=super(employee_asset_line, self).create(vals_list)
              if vals_list.get('asset_id') and vals_list.get('employee_id'):
                  asset = self.env['employee.asset'].browse(vals_list.get('asset_id'))
                  print("asset")
                  print(asset)
                  employee = self.env['hr.employee'].browse(vals_list.get('employee_id'))
                  if vals_list.get('date_of_allocation'):

                      allocation_date = vals_list.get('date_of_allocation')
                      self.update_asset(asset,employee,allocation_date)
                  else:
                      self.update_asset(asset,employee,False)
              return res

    @api.onchange('asset_id')
    def onchange_asset_id(self):
        if self.asset_id:
            if self.asset_id.employee_id:
                raise UserError(_("Asset already allocated to %s, please return it first" % self.asset_id.employee_id.name))




    def return_asset(self):
        self.state='returned'
        if not self.date_returned:
            self.date_returned=datetime.today().date()
        self.asset_id.write({'date_returned':self.date_returned,'employee_id':False})
