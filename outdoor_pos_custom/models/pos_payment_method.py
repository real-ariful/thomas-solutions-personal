# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    
    hide_method = fields.Boolean(string="Hide Method for Immediate Payment", default=False)