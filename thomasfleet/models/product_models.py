from odoo import models, fields, api


class ThomasProduct(models.Model):

    _inherit = 'product.template'

    rate_type = fields.Selection([('monthly', 'Monthly'),
                                  ('weekly', 'Weekly'),
                                  ('daily', 'Daily'),
                                  ('biweekly', 'Bi-Weekly'),
                                  ('term', 'Term'),
                                  ('amd_daily_pu', 'AMD Daily Pickup'),
                                  ('amd_daily_cc', 'AMD Daily Crew Cab'),
                                  ('amd_daily_ts', 'AMD Daily Tandem Stake'),
                                  ('amd_daily_tr', 'AMD Daily Tractor'),
                                  ('amd_daily_ft', 'AMD Daily Flat Truck'),
                                  ('stelco_daily_van', 'Stelco Daily Van'),
                                  ('stelco_daily','Stelco Daily'),
                                  ('stelco_weekly','Stelco Weekly'),
                                  ('stelco_monthly','Stelco Monthly')
                                  ],
                                 'Rate Type', default='monthly',
                                 tracking=True)

    gp_tax_schedule_id = fields.Char(compute="_compute_tax_schedule_id")
    gp_uom = fields.Char(compute="_compute_uom")

    def _compute_tax_schedule_id(self):
        for rec in self:
            rec.gp_tax_schedule_id = 'HST ONT'

    def _compute_uom(self):
        for rec in self:
            rec.gp_uom = 'EACH'

