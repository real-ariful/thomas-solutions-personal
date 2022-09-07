# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    def action_operation(self):
        self.ensure_one()
        state_id = self.env['res.country.state'].search([("name", '=', "Ontario")], limit=1)
        country_id = self.env['res.country'].search([("name", '=', "Canada")], limit=1)
        self.write({
            'name' : 'Thomas Solutions',
            'vat' : '102702354RT0001',
            'street' : '70 Beach Rd',
            'city' : 'Hamilton',
            'state_id' : state_id.id, 
            'country_id' : country_id.id, 
            'zip' : 'L8L 8K3',
            'report_header' : 'Work Trucks . Cartage . Manpower',
            'report_footer' : '''Make all cheques payable to Thomas Solutions. Terms: NET 30 - 1.5% per month'''
                                '''interest charged on overdue accounts.'''
                                '''Please make sure to indicate invoice number as reference when making payments.''',

            'website' : 'http://www.thomassolutions.ca',
            'phone' : '905-545-8808',
            'email' : '	ar@thomassolutions.ca',
        })
