# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    
    property_supplier_payment_term_name = fields.Char(compute='compute_property_supplier_payment_term')

    def compute_property_supplier_payment_term(self):
        for rec in self:
            rec.property_supplier_payment_term_name = rec.property_supplier_payment_term_id.name or ''

