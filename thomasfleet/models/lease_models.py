# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
from datetime import date, datetime, timedelta
from dateutil import relativedelta
import calendar
import math
import logging

_logger = logging.getLogger(__name__)


class ThomasLease(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _getLeaseDefault(self):
        return self.env['thomasfleet.lease_status'].search([('name', '=', 'Draft')], limit=1).id

    def _get_rate_type(self):
        for rec in self:
            rate_str = ''
            for lines in rec.lease_lines:
                if lines.product_id.rate_type:
                    for sel in lines.product_id._fields['rate_type'].base_field.selection:
                        if sel[0] == lines.product_id.rate_type:
                            the_str = sel[1]
                    if rate_str == '':
                        rate_str += str(the_str)
                    else:
                        rate_str += ', ' + str(the_str)
                else:
                    rate_str = 'NO SET'
            rec.rate_type = rate_str

    def _search_rate_type(self, operator, value):
        lease_ids = []
        records = self.env['thomaslease.lease'].search([])
        for rec in records:
            if 'not' in operator or '!' in operator:
                if not rec.rate_type:
                    lease_ids.append(rec.id)
                if rec.rate_type != value:
                    lease_ids.append(rec.id)
            else:
                if rec.rate_type:
                    if value:
                        if value in rec.rate_type:
                            lease_ids.append(rec.id)

        return [('id', 'in', lease_ids)]

    @api.onchange('vehicle_id')
    def _get_unit_odometer(self):
        self.mileage_at_lease = self.vehicle_id.odometer

    @api.constrains('run_initial_invoicing')
    def check_if_initial_invoicing_valid(self):
        for rec in self:
            if rec.rate_type == 'Bi-Weekly' and rec.run_initial_invoicing:
                rec.run_initial_invoicing = False
                raise models.ValidationError(
                    'You cannot run Initial Invoicing (Back Billing) for Bi-Weekly lease agreements ')

    @api.constrains('vehicle_id')
    def check_vehicle_is_available(self):
        for rec in self:
            if rec.vehicle_id.unit_no == '1719':
                return
            for lease_agreement in rec.vehicle_id.lease_agreements:
                if lease_agreement.state == 'active' and lease_agreement.id != rec.id:
                    raise models.ValidationError(
                        'Unit: ' + rec.vehicle_id.unit_no +
                        ' is currently associated with an Active lease agreement: ' + lease_agreement.lease_number)

                if lease_agreement.state == 'repairs_pending':
                    raise models.ValidationError(
                        'Unit: ' + rec.vehicle_id.unit_no +
                        ' is currently associated with an Repairs Pending lease agreement: ' + lease_agreement.lease_number)

    @api.onchange('customer_id')
    def _set_discount_rate_calc(self):
        for rec in self:
            if rec.customer_id:
                rec.discount_rate_calc = rec.customer_id.discount_rate_calc

    @api.onchange('customer_id')
    def _set_preferred_billing_default(self):
        for rec in self:
            if rec.preferred_payment == False:
                if rec.customer_id.preferred_payment == "customer":
                    rec.preferred_payment = False
                elif rec.customer_id.preferred_payment == "other":
                    rec.other_payment = rec.customer_id.other_payment
                    rec.preferred_payment = rec.customer_id.preferred_payment
                else:
                    rec.preferred_payment = rec.customer_id.preferred_payment

    @api.onchange("lease_start_date")
    def set_billing_start_date(self):
        print("Setting Billing Start Date")
        if not self.billing_start_date:
            self.billing_start_date = self.lease_start_date

    @api.onchange("lease_start_date")
    def set_invoice_dates(self):
        if self.lease_start_date:
            if not self.billing_start_date:
                self.billing_start_date = self.lease_start_date

            lease_start_date = datetime.strptime(self.billing_start_date, '%Y-%m-%d')

            today = date.today()
            last_day_lease_month = calendar.monthrange(lease_start_date.year, lease_start_date.month)[1]
            start_of_current_month = date(today.year, today.month, 1)
            rel_next_month = start_of_current_month + relativedelta.relativedelta(months=+1)
            start_of_next_month = rel_next_month  # date(lease_start_date.year, int(lease_start_date.month + 1), 1)
            tmp_invoice_to = None

            if (lease_start_date.month == today.month) and (lease_start_date.year == today.year):
                if not self.invoice_ids:
                    self.run_initial_invoicing = True
                    self.invoice_posting_date = date(today.year, today.month, last_day_lease_month)
                    self.invoice_from = lease_start_date
                    tmp_invoice_to = date(today.year, today.month, last_day_lease_month)
            else:
                self.run_initial_invoicing = False
                self.invoice_posting_date = date(today.year, today.month, 1)
                self.invoice_from = date(today.year, today.month, 1)
                last_day_lease_month = calendar.monthrange(today.year, today.month)[1]
                tmp_invoice_to = date(today.year, today.month, last_day_lease_month)

            self.invoice_generation_date = date.today()

            if self.lease_return_date:
                self.invoice_to = self.lease_return_date
                self.requires_manual_calculations = True
            else:
                self.invoice_to = tmp_invoice_to

    @api.model
    @api.onchange('customer_id')
    def set_contacts(self):
        ap_cons = []
        po_cons = []
        ops_cons = []
        for cons in self.customer_id.child_ids:
            if cons.ap_contact:
                ap_cons.append(cons.id)
            elif cons.po_contact:
                po_cons.append(cons.id)
            elif cons.ops_contact:
                ops_cons.append(cons.id)

        self.ap_contact_ids = [(6, 0, ap_cons)]
        self.po_contact_ids = [(6, 0, po_cons)]
        self.ops_contact_ids = [(6, 0, ops_cons)]

    @api.model
    @api.onchange('customer_id')
    def get_invoice_address(self):
        addr = self.customer_id.address_get(['invoice'])
        if addr:
            self.partner_invoice_id = addr.get('invoice')
        else:
            self.partner_invoice_id = addr.get('contact')

    @api.model
    @api.onchange('customer_id')
    def get_shipping_address(self):
        addr = self.customer_id.address_get(['delivery'])
        if addr:
            self.partner_shipping_id = addr.get('delivery')
        else:
            self.partner_shipping_id = addr.get('contact')


    @api.model
    def btn_validate(self):
        for rec in self:
            rec.state = 'active'

    @api.model
    def lease_print(self):
        """ Print the invoice and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        self.ensure_one()
        return self.env.ref('thomasfleet.lease_agreement').report_action(self)

    _name = 'thomaslease.lease'
    _description = 'Thomas Lease Lease'


    active = fields.Boolean('Active', default=True, tracking=True)
    lease_number = fields.Char('Rental ID', tracking=True)
    po_number = fields.Char("Purchase Order #", tracking=True)
    po_comments = fields.Char("Purchase Order Comments", tracking=True)
    contract_number = fields.Char("Contract #", tracking=True)
    invoice_ids = fields.Many2many('account.move', string='Invoices',
                                   relation='lease_agreement_account_invoice_rel', tracking=True)
    # lease_status = fields.Many2one('thomasfleet.lease_status', string='Lease Status', default=_getLeaseDefault)
    state = fields.Selection([('draft', 'Draft'), ('active', 'Active'),
                              ('repairs_pending', 'Repairs Pending'),
                              ('invoice_pending', 'Invoice Pending'),
                              ('both', 'Repairs and Invoice Pending'),
                              ('closed', 'Closed')], string="Status", default='draft', tracking=True)

    lease_start_date = fields.Date("Rent Start Date", tracking=True)  # , required=True)

    billing_start_date = fields.Date("Billing Start Date", tracking=True)

    invoice_from = fields.Date(string="Invoice From", tracking=True)
    invoice_to = fields.Date(string="Invoice To", tracking=True)
    last_invoice_to = fields.Date(string="Last Invoice Date Range", tracking=True)
    invoice_posting_date = fields.Date(string="Invoice Posting Date", tracking=True)
    invoice_generation_date = fields.Date(string="Invoice Generation Date", tracking=True)
    invoice_due_date = fields.Date(string="Invoice Due Date", tracking=True)

    run_initial_invoicing = fields.Boolean(string="Initial Invoice", default=False)
    preferred_payment = fields.Selection([('cheque', 'Cheque'),
                                          ('credit card', 'Credit Card'),
                                          ('eft', 'EFT'),
                                          ('pad2', 'PAD no Invoice Sent'),
                                          ('pad1', 'PAD with Invoice Sent'),
                                          ('other', 'Other')],
                                         string='Preferred Payment Method', tracking=True
                                         )
    discount_rate_calc = fields.Boolean("Rate Adjust by Duration", default=None, tracking=True)

    other_payment = fields.Char(string='Other Payment', tracking=True)

    lease_return_date = fields.Date("Unit Returned on", tracking=True)
    requires_manual_calculations = fields.Boolean("Exception", default=False,
                                                  tracking=True)
    billing_notes = fields.Char("Billing Notes", tracking=True)
    min_lease_end_date = fields.Date("Minimum Lease End Date", tracking=True)
    fuel_at_lease = fields.Selection([('one_quarter', '1/4'), ('half', '1/2'),
                                      ('three_quarter', '3/4'), ('full', 'Full')], default='full'
                                     , tracking=True)
    fuel_at_return = fields.Selection([('one_quarter', '1/4'), ('half', '1/2'),
                                       ('three_quarter', '3/4'), ('full', 'Full')],
                                      tracking=True)

    lease_out_odometer_id = fields.Many2one('fleet.vehicle.odometer', string="Odometer at Rent",
                                            domain="[('vehicle_id','=',vehicle_id), ('activity','=','lease_out')]",
                                            tracking=True)
    lease_return_odometer_id = fields.Many2one('fleet.vehicle.odometer', string="Odometer at Return",
                                               domain="[('vehicle_id','=',vehicle_id), ('activity','=','lease_in')]",
                                               tracking=True)
    mileage_at_lease = fields.Float(string='Rent Start Odometer', related='lease_out_odometer_id.value', readonly=True,
                                    tracking=True)

    mileage_at_return = fields.Float(string='Rent Return Odometer', related='lease_return_odometer_id.value',
                                     readonly=True, tracking=True)

    delivery_charge = fields.Float(string='Delivery Charge', tracking=True)
    pickup_charge = fields.Float(string='Pick up Charge', tracking=True)
    driver_id = fields.Many2one('res.partner', string='Driver', domain="[('parent_id','=',customer_id)]",
                                tracking=True)

    monthly_rate = fields.Float("Monthly Rate", change_default=True, tracking=True)
    weekly_rate = fields.Float("Weekly Rate", tracking=True)
    daily_rate = fields.Float("Daily Rate", tracking=True)
    monthly_tax = fields.Float("Tax(HST-13%)", tracking=True)
    monthly_total = fields.Float("Monthly Rent Total", tracking=True)
    monthly_mileage = fields.Integer("Mileage Allowance", default=3500, tracking=True)
    mileage_overage_rate = fields.Float("Additional Mileage Rate", default=0.14, tracking=True)

    customer_id = fields.Many2one("res.partner", "Customer", change_default=True,
                                  tracking=True, 
                                #   options="{'always_reload':true}",
                                  context="{'show_internal_division':True}")  # required=True)
    customer_name = fields.Char("Customer", related="customer_id.compound_name")
    partner_invoice_id = fields.Many2one('res.partner', string='Bill To', domain="[('parent_id','=',customer_id)]",
                                         tracking=True)
    partner_shipping_id = fields.Many2one('res.partner', string='Ship To', domain="[('parent_id','=',customer_id)]",
                                          tracking=True)
    vehicle_id = fields.Many2one("fleet.vehicle", string="Unit #", change_default=True,
                                 tracking=True)  # required=True)

    unit_slug = fields.Char("Unit", related="vehicle_id.unit_slug", readonly=True, tracking=True)
    lease_lines = fields.One2many('thomaslease.lease_line', 'lease_id', string='Lease Lines', change_default=True,
                                  copy=True, auto_join=True, tracking=True)
    # product_ids = fields.Many2many("product.product",relation='lease_agreeement_product_product_rel', string="Products")

    insurance_on_file = fields.Boolean(related='customer_id.insurance_on_file', string="Proof of Insurance on File",
                                       readonly=True, tracking=True)
    insurance_agent = fields.Char(related='customer_id.insurance_agent', string="Agent", readonly=True)
    insurance_underwriter = fields.Char(related='customer_id.insurance_underwriter', string="Underwriter",
                                        readonly=True, tracking=True)
    insurance_policy = fields.Char(related='customer_id.insurance_policy', string="Policy #", readonly=True,
                                   tracking=True)
    insurance_expiration = fields.Date(related='customer_id.insurance_expiration', string="Expiration Date",
                                       readonly=True, tracking=True)

    ap_contact_ids = fields.Many2many('res.partner', string='Accounts Payable Contacts',
                                      relation='lease_agreement_res_partner_ap_rel',
                                      domain="[('parent_id','=',customer_id)]", tracking=True)
    po_contact_ids = fields.Many2many('res.partner', string='Purchasing Contacts',
                                      relation='lease_agreement_res_partner_po_rel',
                                      domain="[('parent_id','=',customer_id)]", tracking=True)
    ops_contact_ids = fields.Many2many('res.partner', string='Operations Contacts',
                                       relation='lease_agreement_res_partner_ops_rel',
                                       domain="[('parent_id','=',customer_id)]", tracking=True)

    unit_no = fields.Char('Unit #', related="vehicle_id.unit_no", readonly=True, tracking=True)
    rate_type = fields.Char("Rate Type", compute='_get_rate_type', search='_search_rate_type', change_default=True,
                            tracking=True)
    inclusions = fields.Many2many(related="vehicle_id.inclusions", string="Inclusions", readonly=True,
                                  tracking=True)
    accessories = fields.One2many(related="vehicle_id.accessories", string="Accessories", readonly=True,
                                  tracking=True)
    # inclusions_base_rate = fields.Float(compute="_calcBaseIncRate", string="Inclusion List Rate")
    inclusions_discount = fields.Float('Inclusion Discount', tracking=True)
    lease_notes = fields.Text("Lease Notes", tracking=True)
    inspection_notes = fields.Text("Inspection Notes", tracking=True)
    additional_billing = fields.Char("Additional Notes", tracking=True)
    payment_method = fields.Char("Payment Method", tracking=True)
    last_invoice_date = fields.Date("Last Invoice On", tracking=True)
    additional_charges = fields.Boolean("Additional Charges", tracking=True)
    outgoing_inspector = fields.Many2one('hr.employee', string="Outgoing Inspector", tracking=True)
    incoming_inspector = fields.Many2one('hr.employee', string="Incoming Inspector", tracking=True)
    transponder_id = fields.Many2one('thomasfleet.accessory', string="407 Transponder",
                                     domain="[('type.name','=','407 Transponder')]", tracking=True)

    aggregation_id = fields.Char("Aggregate ID")
    rate_calc_description = fields.Char("Rate Note", compute='_compute_rate_calc_description')
    rate_calc_example = fields.Text("Rate Calculations", compute='_compute_rate_calc_example')
    rate_calc_example_for_report = fields.Html("Rate Calculations", compute='_compute_rate_calc_example_html')

    @api.depends('lease_lines')
    def _compute_rate_calc_description(self):
        for rec in self:
            rec.rate_calc_description = rec.rate_calc_description or ''
            for line in rec.lease_lines:
                if rec.rate_calc_description:
                    rec.rate_calc_description = str(rec.rate_calc_description) + str(
                        line.product_id.description) + '\r\n'
                else:
                    rec.rate_calc_description = str(line.product_id.description) + '\r\n'

    @api.depends('lease_lines')
    def _compute_rate_calc_example(self):
        for rec in self:
            rec.rate_calc_example = ''
            for line in rec.lease_lines:
                example = ''

                if line.product_id.rate_type == 'monthly' or line.product_id.rate_type == 'stelco_monthly':
                    example = '1-6 days: ${0:,.2f}'.format(line.daily_rate) + " per day\r\n" \
                              + '7-29 days: ${0:,.2f}'.format(line.weekly_rate / 7) + " per day, " + \
                              '${0:,.2f}'.format(line.weekly_rate) + " per week\r\n" \
                              + '30+ days: ${0:,.2f}'.format(line.monthly_rate / 30) + " per day, " + \
                              '${0:,.2f}'.format(line.monthly_rate) + " per month\r\n"

                elif line.product_id.rate_type == 'weekly' or line.product_id.rate_type == 'stelco_weekly':
                    example = '1-6 days: ${0:,.2f}'.format(line.daily_rate) + " per day\r\n" \
                              + '7-29 days: ${0:,.2f}'.format(line.weekly_rate / 7) + " per day, " + \
                              '${0:,.2f}'.format(line.weekly_rate) + " per week\r\n" \
                              + '30+ days: ${0:,.2f}'.format(line.monthly_rate / 30) + " per day, " + \
                              '${0:,.2f}'.format(line.monthly_rate) + " per month\r\n"

                elif line.product_id.rate_type == 'daily' or line.product_id.rate_type == 'stelco_daily':
                    example = '1-6 days: ${0:,.2f}'.format(line.daily_rate) + " per day\r\n" \
                              + '7-29 days: ${0:,.2f}'.format(line.weekly_rate / 7) + " per day, " + \
                              '${0:,.2f}'.format(line.weekly_rate) + " per week\r\n" \
                              + '30+ days: ${0:,.2f}'.format(line.monthly_rate / 30) + " per day, " + \
                              '${0:,.2f}'.format(line.monthly_rate) + " per month\r\n"
                elif line.product_id.rate_type == 'bi-weekly':
                    example = ''
                elif line.product_id.rate_type == 'term':
                    example = ''
                elif line.product_id.rate_type == 'stelco_daily_van':
                    example = ''
                else:
                    example = ''

                if rec.rate_calc_example:
                    rec.rate_calc_example = str(rec.rate_calc_example) + str(example)
                else:
                    rec.rate_calc_example = str(example)

    @api.depends('lease_lines')
    def _compute_rate_calc_example_html(self):
        for rec in self:
            for line in rec.lease_lines:
                example = ''

                if line.product_id.rate_type == 'monthly' or line.product_id.rate_type == 'stelco_monthly':
                    example = '1-6 days: ${0:,.2f}'.format(line.daily_rate) + " per day<br/>" \
                              + '7-29 days: ${0:,.2f}'.format(line.weekly_rate / 7) + " per day, " + \
                              '${0:,.2f}'.format(line.weekly_rate) + " per week<br/>" \
                              + '30+ days: ${0:,.2f}'.format(line.monthly_rate / 30) + " per day, " + \
                              '${0:,.2f}'.format(line.monthly_rate) + " per month<br/>"

                elif line.product_id.rate_type == 'weekly' or line.product_id.rate_type == 'stelco_weekly':
                    example = '1-6 days: ${0:,.2f}'.format(line.daily_rate) + " per day<br/>" \
                              + '7-29 days: ${0:,.2f}'.format(line.weekly_rate / 7) + " per day, " + \
                              '${0:,.2f}'.format(line.weekly_rate) + " per week<br/>" \
                              + '30+ days: ${0:,.2f}'.format(line.monthly_rate / 30) + " per day, " + \
                              '${0:,.2f}'.format(line.monthly_rate) + " per month<br/>"

                elif line.product_id.rate_type == 'daily' or line.product_id.rate_type == 'stelco_daily':
                    example = '1-6 days: ${0:,.2f}'.format(line.daily_rate) + " per day<br/>" \
                              + '7-29 days: ${0:,.2f}'.format(line.weekly_rate / 7) + " per day, " + \
                              '${0:,.2f}'.format(line.weekly_rate) + " per week<br/>" \
                              + '30+ days: ${0:,.2f}'.format(line.monthly_rate / 30) + " per day, " + \
                              '${0:,.2f}'.format(line.monthly_rate) + " per month<br/>"
                elif line.product_id.rate_type == 'bi-weekly':
                    example = ''
                elif line.product_id.rate_type == 'term':
                    example = ''
                elif line.product_id.rate_type == 'stelco_daily_van':
                    example = ''
                else:
                    example = ''

                if rec.rate_calc_example_for_report:
                    rec.rate_calc_example_for_report = str(rec.rate_calc_example) + str(example)
                else:
                    rec.rate_calc_example_for_report = str(example)

    # last_invoice_age = fields.Integer("Last Invoice Age", compute='calc_invoice_age')

    # inclusion_rate= fields.float(compute="_calIncRate",string='Inclusion Rate')
    # accessories_base_rate = fields.Float(compute="_calcBaseAccRate", string="Accessor List Rate")
    # accessory_discount=fields.float('Accessor Discount')
    # accessory_rate =fields.float(compute="_caclAccRate",string='Accessory Rate')
    @api.depends('last_invoice_date')
    def calc_invoice_age(self):
        for rec in self:
            if rec.last_invoice_date:
                age = datetime.now() - rec.last_invoice_date
                rec.last_invoice_age = age.days
            else:
                rec.last_invoice_age = 0

    @api.onchange('customer_id', 'lease_start_date', 'vehicle_id')
    def update_lease_number(self):
        Agreements = self.env['thomaslease.lease']
        aCount = 0

        if self.state == 'draft':
            if self.customer_id:
                aCount = Agreements.search_count([('customer_id', '=', self.customer_id.id)])

            self.lease_number = str(self.customer_id.name) + "_" + \
                                str(self.vehicle_id.unit_no) + "_" + \
                                str(self.lease_start_date) + "_" + str(aCount)

    @api.onchange("lease_lines")
    def update_totals(self):
        self.monthly_rate = 0
        tax = 0
        for line in self.lease_lines:
            self.monthly_rate = self.monthly_rate + line.price
            tax = tax + line.tax_amount

        self.monthly_tax = tax
        self.monthly_total = self.monthly_rate + self.monthly_tax
        # self.daily_rate = (self.monthy_rate * .125)
        # self.weekly_rate = (self.monthly_rate * .45)



    @api.model
    @api.depends('lease_number')
    def name_get(self):
        res = []
        for record in self:
            name = record.lease_number
            res.append((record.id, name))
        return res



class ThomasFleetLeaseLine(models.Model):
    _name = 'thomaslease.lease_line'
    _description = 'Thomas Fleet Lease Line'


    @api.depends('product_id')
    def default_description(self):
        return self.product_id.description_sale

    @api.depends('product_id')
    def default_price(self):
        return self.product_id.list_price

    @api.depends('product_id')
    def default_taxes(self):
        return self.product_id.taxes_id

    @api.depends('price')
    def calc_daily_rate(self):
        amt = False
        r_type = self.product_id.rate_type
        if r_type == 'monthly' or r_type == 'stelco_monthly':
            amt = round(self.price * .125, 2)
        elif r_type == 'weekly' or r_type == 'stelco_weekly':
            amt = round((self.price / .45) * .125, 2)
        elif r_type == 'daily' or r_type == 'stelco_daily':
            amt = round(self.price, 2)
        elif r_type == 'amd_daily_pu':
            amt = 31.90
        elif r_type == 'amd_daily_cc':
            amt = 35.50
        elif r_type == 'amd_daily_ts':
            amt = 95
        elif r_type == 'amd_daily_tr':
            amt = 135
        elif r_type == 'amd_daily_ft':
            amt = 0
        return amt

    @api.depends('price')
    def calc_weekly_rate(self):
        amt = False
        r_type = self.product_id.rate_type
        if r_type == 'monthly' or r_type == 'stelco_monthly':
            amt = round(self.price * .45, 2)
        elif r_type == 'weekly' or r_type == 'stelco_weekly':
            amt = round(self.price, 2)
        elif r_type == 'daily' or r_type == 'stelco_daily':
            amt = round((self.price / .125) * .45, 2)
        elif r_type == 'amd_daily_pu':
            amt = 140.00
        elif r_type == 'amd_daily_cc':
            amt = 200.00
        elif r_type == 'amd_daily_ts':
            amt = 475
        elif r_type == 'amd_daily_tr':
            amt = 575
        elif r_type == 'amd_daily_ft':
            amt = 0
        return amt

    @api.depends('price')
    def calc_monthly_rate(self):
        amt = False
        r_type = self.product_id.rate_type
        if r_type == 'monthly' or r_type == 'stelco_monthly':
            amt = round(self.price, 2)
        elif r_type == 'weekly' or r_type == 'stelco_weekly':
            amt = round(self.price / .45, 2)
        elif r_type == 'daily' or r_type == 'stelco_daily':
            amt = round(self.price / .125, 2)
        elif r_type == 'amd_daily_pu':
            amt = 663.00
        elif r_type == 'amd_daily_cc':
            amt = 664.00
        elif r_type == 'amd_daily_ts':
            amt = 0
        elif r_type == 'amd_daily_tr':
            amt = 0
        elif r_type == 'amd_daily_ft':
            amt = 2350.00
        return amt

    @api.depends('price', 'tax')
    def default_total(self):
        return self.price * (1 + (float(self.tax) / 100))

    lease_id = fields.Many2one('thomaslease.lease', string='Lease Reference', required=True, ondelete='cascade',
                               index=True, copy=False)
    vehicle_id = fields.Many2one('fleet.vehicle', string="Unit #", related='lease_id.vehicle_id')
    product_id = fields.Many2one('product.product', string='Product', change_default=True, ondelete='restrict',
                                 required=True)
    description = fields.Char(string="Description", default=default_description)
    tax_id = fields.Many2one('account.tax', string='Tax')
    # fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    tax_ids = fields.Many2many('account.tax', string='Taxes',
                               domain=['|', ('active', '=', False), ('active', '=', True)])
    price = fields.Float(string="Price", default=default_price)
    tax = fields.Char(string="Tax Rate %", default="13")
    tax_amount = fields.Float(string="Tax Amount")
    daily_rate = fields.Float(string="Daily Rate", default=calc_daily_rate)
    weekly_rate = fields.Float(string="Weekly Rate", default=calc_weekly_rate)
    monthly_rate = fields.Float(string="Monthly Rate", default=calc_monthly_rate)

    total = fields.Float(string="Total", default=default_total)

    @api.onchange('product_id')
    def update_product(self):
        self.description = self.product_id.description_sale
        self.price = self.product_id.list_price
        self.tax_amount = self.product_id.list_price * (float(self.tax_id.amount) / 100)
        self.total = self.price * (1 + (float(self.tax_id.amount) / 100))
        self.tax_ids = self.product_id.taxes_id
        if self.product_id.taxes_id:
            self.tax_id = self.product_id.taxes_id[0]

    @api.onchange('price', 'tax')
    def update_total(self):
        self.tax_amount = self.price * (float(self.tax_id.amount) / 100)
        self.total = self.price * (1 + (float(self.tax_id.amount) / 100))
        self.weekly_rate = self.calc_weekly_rate()
        self.monthly_rate = self.calc_monthly_rate()
        self.daily_rate = self.calc_daily_rate()


class ThomasFleetReturnWizard(models.TransientModel):
    _name = 'thomaslease.lease.return.wizard'
    _description = 'Thomas Fleet Return Wizard'

    def _default_lease_ids(self):
        # for the_id in self.env.context.get('active_ids'):
        #    print(the_id.name)
        return self.env.context.get('active_ids')

    def _default_return_date(self):
        return datetime.now()

    lease_ids = fields.Many2many('thomaslease.lease', string="Lease", default=_default_lease_ids)
    invoice_pending = fields.Boolean("Invoice Pending")
    repairs_pending = fields.Boolean("Repairs Pending")
    lease_return_date = fields.Date("Return Date", default=_default_return_date)

    @api.model
    def record_return(self):
        for lease in self.lease_ids:
            if self.invoice_pending & self.repairs_pending:
                lease.state = 'both'
            elif self.invoice_pending:
                lease.state = 'invoice_pending'
            elif self.repairs_pending:
                lease.state = 'repairs_pending'
            else:
                lease.state = 'closed'
            lease.lease_return_date = self.lease_return_date


class ThomasFleetLeaseInvoiceWizard(models.TransientModel):
    _name = 'thomaslease.lease.invoice.wizard'
    _description = 'Thomas Fleet Lease Invoice Wizard'

    lease_records = []

    def _default_lease_ids(self):
        # for the_id in self.env.context.get('active_ids'):
        #    print(the_id.name)
        leases_ids = self.env.context.get('active_ids', [])
        the_leases = self.env['thomaslease.lease'].browse(leases_ids)
        for a_lease in self.web_progress_iter(the_leases, msg="Processing Agreements"):
            # a_lease = self.env['thomaslease.lease'].browse(lease)
            # print("Validating Lease: "+ a_lease.lease_number)
            if not a_lease.lease_lines:
                raise models.ValidationError(
                    'Lease for Unit #' + a_lease.unit_no + ' needs a line item product before it can be invoiced')
            if a_lease.state == 'closed':
                raise models.ValidationError('Lease for Unit #' + a_lease.unit_no + ' is Closed and cannot be invoiced')
            else:
                # print("Setting Dates " + a_lease.lease_number)
                vals = self.get_invoice_dates(a_lease, False)
                a_lease.with_context(tracking_disable=True).write(vals)

                #a_lease.update(vals)
            # self.lease_records.append(a_lease)
        return leases_ids

    def _default_lease_ids_old(self):
        # for the_id in self.env.context.get('active_ids'):
        #    print(the_id.name)
        leases_ids = self.env.context.get('active_ids', [])
        updated_leases = []
        trans = []
        for lease in leases_ids:
            a_lease = self.env['thomaslease.lease'].browse(lease)
            print("Validating Lease: " + a_lease.lease_number)
            if not a_lease.lease_lines:
                raise models.ValidationError(
                    'Lease for Unit #' + a_lease.unit_no + ' needs a line item product before it can be invoiced')
            if a_lease.state == 'closed':
                raise models.ValidationError('Lease for Unit #' + a_lease.unit_no + ' is Closed and cannot be invoiced')
            else:
                print("Setting Invoice Date " + a_lease.lease_number)
                self.set_invoice_dates(a_lease, False)
            self.lease_records.append(a_lease)
        return leases_ids

    def get_invoice_dates(self, lease, dt_in):
        # inv_date = self.invoice_date
        billing_strt_date = lease.billing_start_date

        if not dt_in:
            dt = datetime.now()
        else:
            dt = dt_in

        inv_due_date = dt + relativedelta.relativedelta(days=+30)

        l_rdt = False
        if lease.lease_return_date:
            l_rdt = datetime.strptime(lease.lease_return_date, '%Y-%m-%d')

        if lease.billing_start_date:
            l_sdt = datetime.strptime(lease.billing_start_date, '%Y-%m-%d')
        elif lease.lease_start_date:
            l_sdt = datetime.strptime(lease.lease_start_date, '%Y-%m-%d')
            # lease.billing_start_date = lease.lease_start_date
            billing_strt_date = lease.lease_start_date
        else:
            raise models.UserError('Lease Start Date or Billing Date Not set for: ' + lease.lease_number)

        if "Dofasco" in lease.customer_id.name:
            i_from = datetime(dt.year, dt.month, 1)
            days_in_month = calendar.monthrange(dt.year, dt.month)[1]
            i_to = datetime(dt.year, dt.month, days_in_month)
            # lease.invoice_date = i_to
            inv_date = i_to
            inv_due_date = i_to + relativedelta.relativedelta(days=+30)

        else:
            i_from = datetime(dt.year, dt.month, 1)
            days_in_month = calendar.monthrange(dt.year, dt.month)[1]
            i_to = datetime(dt.year, dt.month, days_in_month)

        # if start date - handled by initial invoicing
        # if return date
        if lease.run_initial_invoicing:
            if l_rdt:
                if i_to.month == l_rdt.month and i_to.year == l_rdt.year:
                    if l_rdt.day < i_to.day:
                        i_to = l_rdt

            if l_sdt > i_from:
                i_from = lease.billing_start_date

            # i_to = datetime(dt.year, dt.month, days_in_month)


        # handles the scenario where lease is returned the month prior to billing..ie.  leased from dec1 to dec25
        # billing on Jan 1, paid in Feb
        else:
            if l_rdt:
                i_to = l_rdt
                if i_to < i_from:
                    i_from = datetime(i_to.year, i_to.month, 1)
                    if l_sdt > i_from:
                        i_from = lease.billing_start_date

        return {
            'billing_start_date': billing_strt_date,
            'invoice_from': i_from,
            'invoice_to': i_to,
            'invoice_due_date': inv_due_date,
            'invoice_generation_date': dt,
            'invoice_posting_date': dt
        }

        # lease.invoice_from = i_from
        # lease.invoice_to = i_to
        # lease.invoice_due_date = inv_due_date
        # lease.invoice_generation_date = dt
        # lease.invoice_posting_date = dt

    def set_invoice_dates(self, lease, dt_in):
        # inv_date = self.invoice_date
        billing_strt_date = lease.billing_start_date

        if not dt_in:
            dt = datetime.now()
        else:
            dt = dt_in

        inv_due_date = dt + relativedelta.relativedelta(days=+30)

        l_rdt = False
        if lease.lease_return_date:
            l_rdt = datetime.strptime(lease.lease_return_date, '%Y-%m-%d')

        if lease.billing_start_date:
            l_sdt = datetime.strptime(lease.billing_start_date, '%Y-%m-%d')
        elif lease.lease_start_date:
            l_sdt = datetime.strptime(lease.lease_start_date, '%Y-%m-%d')
            # lease.billing_start_date = lease.lease_start_date
            billing_strt_date = lease.lease_start_date
        else:
            raise models.UserError('Lease Start Date or Billing Date Not set for: ' + lease.lease_number)

        if "Dofasco" in lease.customer_id.name:
            i_from = datetime(dt.year, dt.month, 1)
            days_in_month = calendar.monthrange(dt.year, dt.month)[1]
            i_to = datetime(dt.year, dt.month, days_in_month)
            # lease.invoice_date = i_to
            inv_date = i_to
            inv_due_date = i_to + relativedelta.relativedelta(days=+30)

        else:
            i_from = datetime(dt.year, dt.month, 1)
            days_in_month = calendar.monthrange(dt.year, dt.month)[1]
            i_to = datetime(dt.year, dt.month, days_in_month)

        # if start date - handled by initial invoicing
        # if return date
        if lease.run_initial_invoicing:
            if l_rdt:
                if i_to.month == l_rdt.month and i_to.year == l_rdt.year:
                    if l_rdt.day < i_to.day:
                        i_to = l_rdt

            if l_sdt > i_from:
                i_from = lease.billing_start_date

            # i_to = datetime(dt.year, dt.month, days_in_month)


        # handles the scenario where lease is returned the month prior to billing..ie.  leased from dec1 to dec25
        # billing on Jan 1, paid in Feb
        else:
            if l_rdt:
                i_to = l_rdt
                if i_to < i_from:
                    i_from = datetime(i_to.year, i_to.month, 1)
                    if l_sdt > i_from:
                        i_from = lease.billing_start_date
        
        lease['billing_start_date'] = billing_strt_date
        lease['invoice_from'] = i_from
        lease['invoice_to'] = i_to
        lease['invoice_due_date'] = inv_due_date
        lease['invoice_generation_date'] = dt
        lease['invoice_posting_date'] = dt

        # lease.invoice_from = i_from
        # lease.invoice_to = i_to
        # lease.invoice_due_date = inv_due_date
        # lease.invoice_generation_date = dt
        # lease.invoice_posting_date = dt

    def _default_invoice_date(self):
        return datetime.now()

    def _default_invoice_due_date(self):
        df = datetime.now()
        dt2 = df + relativedelta.relativedelta(days=+30)
        return dt2

    def _default_invoice_posting_date(self):
        dt2 = datetime.now()
        dfm = dt2 - relativedelta.relativedelta(months=-1)
        dt = date(dfm.year, dfm.month, 1)
        return dt

    def _default_invoice_start_date(self):
        df = datetime.now()
        dfm = df - relativedelta.relativedelta(months=-1)
        dt2 = date(dfm.year, dfm.month, 1)
        return dt2

    def _default_invoice_end_date(self):
        df = datetime.now()
        dfm = df - relativedelta.relativedelta(months=-1)
        days_in_month = calendar.monthrange(dfm.year, dfm.month)[1]
        dt2 = date(dfm.year, dfm.month, days_in_month)
        return dt2

    @api.onchange("invoice_date")
    def set_dates(self):
        dt = datetime.strptime(self.invoice_date, '%Y-%m-%d')
        dt2 = dt + relativedelta.relativedelta(days=+30)
        end_of_month = calendar.monthrange(dt.year, dt.month)[1]
        self.invoice_due_date = dt2
        for lease in self.lease_ids:
            self.set_invoice_dates(lease, dt)
        #    lease.invoice_due_date = dt2
        #    lease.invoice_from = date(dt.year, dt.month, 1)
        #    lease.invoice_to = date(dt.year, dt.month, end_of_month)
        # todo: add non-amd calc..
        # if not amd invoice is for the current of the invoice date..
        # else amd is previous month.
        # todo: posting date same invoice date
        # todo: update lease agreement table to include from and to and invoice date and due date (30 days from invoice date)
        # todo: posting date can be removed

        # todo:  initialInvoice...only invoice if it's retured
        # todo: otherwise invoice for it in the next month cycle..or when returned
        '''
        dt = datetime.strptime(self.invoice_date, '%Y-%m-%d')
        end_of_month = calendar.monthrange(dt.year, dt.month)[1]
        end_of_prev_month = calendar.monthrange(dt.year, dt.month-1)[1]
        self.invoice_posting_date = date(dt.year,dt.month,end_of_month)
        self.invoice_due_date = date(dt.year, dt.month,end_of_month)
        self.invoice_start_date = date(dt.year, dt.month-1,1)
        self.invoice_end_date = date(dt.year,dt.month-1,end_of_prev_month)
        '''

    def calc_biweekly_lease(self, biweekly_rate, lease):
        # calculate invoice for 4 weeks from last date.
        if lease.last_invoice_to:
            last_to_date = datetime.strptime(lease.last_invoice_to, '%Y-%m-%d')
        elif lease.billing_start_date:
            last_to_date = datetime.strptime(lease.billing_start_date, '%Y-%m-%d')
        else:
            last_to_date = datetime.strptime(lease.lease_start_date, '%Y-%m-%d')
        start_date = last_to_date
        if lease.lease_return_date:
            end_date = datetime.strptime(lease.lease_return_date, '%Y-%m-%d')
        else:
            end_date = start_date + relativedelta.relativedelta(weeks=+4)

        num_days = (end_date - start_date).days
        daily_rate = (biweekly_rate * 2) / num_days
        amount = daily_rate * num_days

        return amount

    def calc_rate_monthly_lease(self, monthly_total, start_date, end_date, lease):

        '''
        Takes the montlhy amount and detemines daily and weekly rates
        Doesn't discount the rate but rather charges a premium if the lease is held less than 1 month
        :param monthly_total:
        :param start_date:
        :param end_date:
        :param lease:
        :return:
        '''
        start_d = datetime.strptime(start_date, '%Y-%m-%d')
        end_d = datetime.strptime(end_date, '%Y-%m-%d')
        lease_start = datetime.strptime(lease.lease_start_date, '%Y-%m-%d')
        date_delta = relativedelta.relativedelta(end_d, start_d)

        just_days = (end_d - start_d).days + 1
        days_in_end_month = calendar.monthrange(end_d.year, end_d.month)[1]

        cost_per_day_d_rate = round((monthly_total * .125), 2)
        cost_per_day_w_rate = round(((monthly_total * .45) / 7), 2)
        cost_per_day_m_rate = round((monthly_total / 30), 2)
        rate = cost_per_day_m_rate
        num_days = date_delta.days + 1  # assumes current day for billing

        # unit has been returned...determine if rates are adjusted
        if lease.lease_return_date:
            lease_end = datetime.strptime(lease.lease_return_date, '%Y-%m-%d')
            days_in_lease = (lease_end - lease_start).days + 1
            if end_d.month == start_d.month and just_days == days_in_end_month:
                amount = monthly_total
                rate = monthly_total
                formula = '${0:,.2f}'.format(amount) + " - per month \r\n"
            elif days_in_lease < 7:
                amount = cost_per_day_d_rate * just_days
                rate = cost_per_day_d_rate
                formula = '${0:,.2f}'.format(amount) + " - " + str(just_days) + " days @ " + '{0:,.2f}'.format(
                    cost_per_day_d_rate) + " (12.5 % of ${0:,.2f}".format(
                    monthly_total) + ", monthly rate, per day) \r\n"
            elif days_in_lease >= 7 and days_in_lease < 30:
                amount = cost_per_day_w_rate * just_days
                rate = cost_per_day_w_rate
                formula = '${0:,.2f}'.format(amount) + " - " + str(just_days) + " days @ " + '{0:,.2f}'.format(
                    cost_per_day_w_rate) + " (45% of ${0:,.2f}".format(
                    monthly_total) + ", monthly rate, per week, per day) \r\n"
            elif days_in_lease >= 30:
                amount = cost_per_day_m_rate * just_days
                formula = '${0:,.2f}'.format(amount) + " - " + str(just_days) + " days @ " + '{0:,.2f}'.format(
                    cost_per_day_m_rate) + " (${0:,.2f}".format(monthly_total) + ", monthly rate, per day) \r\n"
        else:  # unit is not returned assumes monthly rate even if it's a short duration
            if end_d.month == start_d.month and just_days == days_in_end_month:
                amount = monthly_total
                rate = monthly_total
                formula = '${0:,.2f}'.format(amount) + " - per month \r\n"
            else:
                amount = cost_per_day_m_rate * just_days
                formula = '${0:,.2f}'.format(amount) + " - " + str(just_days) + " days @ " + '{0:,.2f}'.format(
                    cost_per_day_m_rate) + " (${0:,.2f}".format(monthly_total) + ", monthly rate, per day) \r\n"

        return {"amount": amount, "formula": formula, "rate": rate}

    def calc_rate_monthly_lease_old(self, monthly_total, start_date, end_date):

        start_d = datetime.strptime(start_date, '%Y-%m-%d')
        end_d = datetime.strptime(end_date, '%Y-%m-%d')

        date_delta = relativedelta.relativedelta(end_d, start_d)
        num_days = date_delta.days + 1  # assumes current day for billing

        num_days_span = date_delta.days
        num_months = date_delta.months
        num_weeks = date_delta.weeks
        # bal_weeks = num_days % num_weeks
        # bal_days = bal_weeks % 7
        daily_rate = (monthly_total * 12.5) / 100
        weekly_rate = (monthly_total * 45) / 100
        year_amount = (date_delta.years * 12) * monthly_total
        month_amount = (num_months * monthly_total)
        week_amount = (num_weeks * weekly_rate)
        day_amount = (num_days * daily_rate)
        g_total = year_amount + month_amount + week_amount + day_amount
        daily_str = ''
        weekly_str = ''
        monthly_str = ''
        days_in_month = calendar.monthrange(end_d.year, end_d.month)[1]
        amount = monthly_total
        # future value add
        formula = ''
        if day_amount > 0:
            daily_str = '${0:,.2f}'.format(day_amount) + " - " + str(num_days) + " days @ " + '{0:,.2f}'.format(
                daily_rate) + " (monthly prorated daily rate) \r\n"

        if week_amount > 0:
            weekly_str = '${0:,.2f}'.format(week_amount) + " - " + str(num_weeks) + " weeks @ " + '{0:,.2f}'.format(
                weekly_rate) + " (monthly prorated weekly rate) \r\n"

        if (month_amount + year_amount) > 0:
            monthly_str = '${0:,.2f}'.format(month_amount + year_amount) + " - " + str(
                ((date_delta.years * 12) + date_delta.months)) + " months @ " + str(monthly_total) + " (monthly rate)"

        if num_days < 7 and num_months == 0:
            amount = num_days * daily_rate
            formula = daily_str
        elif num_days >= 7 and num_months == 0 and num_days < days_in_month:
            days = num_days % 7
            week_day_amount = ((days / 7) * weekly_rate)
            week_days_str = ''
            if days > 0:
                week_days_str = '${0:,.2f}'.format(week_day_amount) + " - " + "(" + str(
                    days) + " / 7 days) @ " + '{0:,.2f}'.format(weekly_rate) + \
                                " (monthly prorated weekly rate) \r\n"
            weeks = math.floor(num_days / 7)
            amount = week_day_amount + (weeks * weekly_rate)
            formula = week_days_str + weekly_str
        elif num_months == 0 and (num_days_span + 1) == days_in_month:
            amount = monthly_total
            formula = 'Rate Calculation:\r\n' + "Monthly Rate"
        else:
            amount = g_total
            formula = daily_str + weekly_str + monthly_str
            if len(formula) > 0:
                formula = 'Rate Calculation:\r\n' + formula

        return {"amount": amount, "formula": formula}

    def calc_rate_monthly_lease_older(self, monthly_total, start_date, end_date):

        start_d = datetime.strptime(start_date, '%Y-%m-%d')
        end_d = datetime.strptime(end_date, '%Y-%m-%d')

        date_delta = relativedelta.relativedelta(end_d, start_d)
        num_days = date_delta.days + 1  # assumes current day for billing

        num_days_span = date_delta.days
        num_months = date_delta.months
        num_weeks = date_delta.weeks
        # bal_weeks = num_days % num_weeks
        # bal_days = bal_weeks % 7
        daily_rate = (monthly_total * 12.5) / 100
        weekly_rate = (monthly_total * 45) / 100
        year_amount = (date_delta.years * 12) * monthly_total
        month_amount = (num_months * monthly_total)
        week_amount = (num_weeks * weekly_rate)
        day_amount = (num_days * daily_rate)
        g_total = year_amount + month_amount + week_amount + day_amount
        daily_str = ''
        weekly_str = ''
        monthly_str = ''
        days_in_month = calendar.monthrange(end_d.year, end_d.month)[1]
        amount = monthly_total
        # future value add
        formula = ''
        if day_amount > 0:
            daily_str = '{0:,.2f}'.format(day_amount) + " - " + str(num_days) + " days @ " + '{0:,.2f}'.format(
                daily_rate) + " (monthly prorated daily rate) \r\n"

        if week_amount > 0:
            weekly_str = '{0:,.2f}'.format(week_amount) + " - " + str(num_weeks) + " weeks @ " + '{0:,.2f}'.format(
                weekly_rate) + " (monthly prorated weekly rate) \r\n"

        if (month_amount + year_amount) > 0:
            monthly_str = '{0:,.2f}'.format(month_amount + year_amount) + " - " + str(
                ((date_delta.years * 12) + date_delta.months)) + " months @ " + str(monthly_total) + " (monthly rate)"

        if num_days < 7 and num_months == 0:
            amount = num_days * daily_rate
            formula = daily_str
        elif num_days >= 7 and num_months == 0 and num_days < days_in_month:
            days = num_days % 7
            weeks = math.floor(num_days / 7)
            amount = (days * daily_rate) + (weeks * weekly_rate)
            formula = daily_str + weekly_str

            if amount > monthly_total:
                amount = monthly_total
                formula = 'Rate Calculation:\r\n' + "Monthly Rate"
        elif num_months == 0 and (num_days_span + 1) == days_in_month:
            amount = monthly_total
            formula = 'Rate Calculation:\r\n' + "Monthly Rate"
        else:
            amount = g_total
            formula = daily_str + weekly_str + monthly_str
            if len(formula) > 0:
                formula = 'Rate Calculation:\r\n' + formula
            '''
            formula = '{0:,.2f}'.format(day_amount) + " - " + str(num_days) + " days @" + str(
                daily_rate) + "(monthly prorated daily rate) \r\n" + "+ " + str(week_amount) + " - " + str(
                num_weeks) + " weeks @" + str(
                weekly_rate) + "(monthly prorated weekly rate) \r\n" + "+ " + '{0:,.2f}'.format(
                month_amount + year_amount) + " - " + str(
                ((date_delta.years * 12) + date_delta.months)) + " months @" + str(monthly_total) + " (monthly rate)"
            '''
        return {"amount": amount, "formula": formula}

    def calc_rate_weekly_lease(self, discount, weekly_rate, start_date, end_date):

        start_d = datetime.strptime(start_date, '%Y-%m-%d')
        end_d = datetime.strptime(end_date, '%Y-%m-%d')
        date_delta = relativedelta.relativedelta(end_d, start_d)

        just_days = (end_d - start_d).days + 1

        cost_per_day_d_rate = round(((weekly_rate * .125) / .45), 2)
        cost_per_day_w_rate = round((weekly_rate / 7), 2)
        rate = cost_per_day_w_rate
        cost_per_day_m_rate = round((weekly_rate / .45) / 30, 2)
        num_days = date_delta.days + 1  # assumes current day for billing

        if not discount:
            amount = cost_per_day_w_rate * just_days
            formula = '${0:,.2f}'.format(amount) + " - " + str(just_days) + " days @ " + '{0:,.2f}'.format(
                cost_per_day_w_rate) + " (weekly rate) \r\n"
        else:
            if just_days < 7:
                amount = cost_per_day_d_rate * just_days
                rate = cost_per_day_d_rate
                formula = '${0:,.2f}'.format(amount) + " - " + str(just_days) + " days @ " + '{0:,.2f}'.format(
                    cost_per_day_d_rate) + " (prorated weekly rate) \r\n"
            elif just_days >= 7 and just_days < 30:
                amount = cost_per_day_w_rate * just_days
                formula = '${0:,.2f}'.format(amount) + " - " + str(just_days) + " days @ " + '{0:,.2f}'.format(
                    cost_per_day_w_rate) + " (weekly rate) \r\n"
            elif just_days >= 30:
                amount = cost_per_day_m_rate * just_days
                rate = cost_per_day_m_rate
                formula = '${0:,.2f}'.format(amount) + " - " + str(just_days) + " days @ " + '{0:,.2f}'.format(
                    cost_per_day_m_rate) + " (prorated monthly rate) \r\n"

        return {"amount": amount, "formula": formula, "rate": rate}

    def calc_rate_daily_lease(self, discount, daily_rate, start_date, end_date):
        start_d = datetime.strptime(start_date, '%Y-%m-%d')
        end_d = datetime.strptime(end_date, '%Y-%m-%d')
        date_delta = relativedelta.relativedelta(end_d, start_d)

        just_days = (end_d - start_d).days + 1

        cost_per_day_d_rate = round(daily_rate, 2)
        rate = daily_rate
        cost_per_day_w_rate = round(((daily_rate / .125) * .45) / 7, 2)
        cost_per_day_m_rate = round((((daily_rate / .125) * .45) / .45) / 30, 2)
        num_days = date_delta.days + 1  # assumes current day for billing

        if not discount:
            amount = cost_per_day_d_rate * just_days
            formula = '${0:,.2f}'.format(amount) + " - " + str(just_days) + " days @ " + '{0:,.2f}'.format(
                cost_per_day_d_rate) + " (daily rate) \r\n"
        else:
            if just_days < 7:
                amount = cost_per_day_d_rate * just_days
                formula = '${0:,.2f}'.format(amount) + " - " + str(just_days) + " days @ " + '{0:,.2f}'.format(
                    cost_per_day_d_rate) + " (daily rate) \r\n"
            elif just_days >= 7 and just_days < 30:
                amount = cost_per_day_w_rate * just_days
                formula = '${0:,.2f}'.format(amount) + " - " + str(just_days) + " days @ " + '{0:,.2f}'.format(
                    cost_per_day_w_rate) + " (weekly rate) \r\n"
                rate = cost_per_day_w_rate
            elif just_days >= 30:
                amount = cost_per_day_m_rate * just_days
                formula = '${0:,.2f}'.format(amount) + " - " + str(just_days) + " days @ " + '{0:,.2f}'.format(
                    cost_per_day_m_rate) + " (prorated monthly rate) \r\n"
                rate = cost_per_day_m_rate

        return {"amount": amount, "formula": formula, "rate": rate}

    def calc_rate_weekly_lease_old(self, weekly_rate, start_date, end_date):

        start_d = datetime.strptime(start_date, '%Y-%m-%d')
        end_d = datetime.strptime(end_date, '%Y-%m-%d')
        date_delta = relativedelta.relativedelta(end_d, start_d)

        just_days = (end_d - start_d).days + 1

        cost_per_day_d_rate = ((weekly_rate * .125) / .45)
        cost_per_day_w_rate = (weekly_rate / 7)
        cost_per_day_m_rate = (weekly_rate / .45) / 30
        num_days = date_delta.days + 1  # assumes current day for billing

        if just_days < 7:
            amount = cost_per_day_d_rate * just_days
            formula = '${0:,.2f}'.format(amount) + " - " + str(just_days) + " days @ " + '{0:,.2f}'.format(
                cost_per_day_d_rate) + " (prorated weekly rate) \r\n"

        elif just_days >= 7 and just_days < 30:
            amount = cost_per_day_w_rate * just_days
            formula = '${0:,.2f}'.format(amount) + " - " + str(just_days) + " days @ " + '{0:,.2f}'.format(
                cost_per_day_w_rate) + " (weekly rate) \r\n"

        elif just_days <= 30:
            amount = cost_per_day_m_rate * just_days
            formula = '${0:,.2f}'.format(amount) + " - " + str(just_days) + " days @ " + '{0:,.2f}'.format(
                cost_per_day_m_rate) + " (prorated monthly rate) \r\n"

        num_days_span = date_delta.days
        num_months = date_delta.months
        num_weeks = date_delta.weeks

        daily_rate = ((weekly_rate * .125) / .45)
        monthly_rate = weekly_rate / .45
        year_amount = (date_delta.years * 12) * monthly_rate
        month_amount = (num_months * monthly_rate)
        week_amount = (num_weeks * weekly_rate)
        day_amount = (num_days * daily_rate)
        g_total = year_amount + month_amount + week_amount + day_amount

        days_in_month = calendar.monthrange(end_d.year, end_d.month)[1]
        # monthly_rate = (days_in_month * daily_rate)
        amount = monthly_rate
        formula = ''
        if day_amount > 0:
            daily_str = '${0:,.2f}'.format(day_amount) + " - " + str(num_days) + " days @ " + '{0:,.2f}'.format(
                daily_rate) + " (prorated weekly rate) \r\n"

        if week_amount > 0:
            weekly_str = '${0:,.2f}'.format(week_amount) + " - " + str(num_weeks) + " weeks @ " + '{0:,.2f}'.format(
                weekly_rate) + " (weekly rate) \r\n"

        if (month_amount + year_amount) > 0:
            monthly_str = '${0:,.2f}'.format(month_amount + year_amount) + " - " + str(
                ((date_delta.years * 12) + date_delta.months)) + " months @ " + str(monthly_rate) + " (monthly rate)"

        if just_days < 7:
            amount = num_days * daily_rate
            formula = '${0:,.2f}'.format(day_amount) + " - " + str(num_days) + " days @ " + '{0:,.2f}'.format(
                daily_rate) + " (prorated weekly rate) \r\n"

        # need to handle the case only if it's more than 30 days..
        # rules are basic...if over 30 days..then use monthly rate basis and prorated accordingly
        # ie.  42 days should switch to monthly rate and then prorate for: monthly_rate /30 * 12..
        elif num_days >= 7 and num_days < 30:
            days = num_days % 7
            weeks = math.floor(num_days / 7)
            week_day_amount = days * daily_rate
            amount = week_day_amount + (weeks * weekly_rate)
            week_days_str = ''
            if days > 0:
                week_days_str = '${0:,.2f}'.format(week_day_amount) + " - " + str(
                    days) + " days @ " + '{0:,.2f}'.format(daily_rate) + \
                                " (prorated weekly rate) \r\n"

            formula = week_days_str + '${0:,.2f}'.format(week_amount) + " - " + str(
                weeks) + " weeks @ " + '{0:,.2f}'.format(
                weekly_rate) + " (weekly rate) \r\n"

            if amount > monthly_rate:
                formula = 'Rate Calculation:\r\n' + "Monthly Rate"
                amount = monthly_rate

        elif num_months == 0 and (num_days_span + 1) == days_in_month:
            amount = monthly_rate
            formula = 'Rate Calculation:\r\n' + "Monthly Rate"
        else:
            amount = g_total
            formula = daily_str + weekly_str + monthly_str
            if len(formula) > 0:
                formula = 'Rate Calculation:\r\n' + formula

        return {"amount": amount, "formula": formula}

    def calc_rate_daily_lease_old(self, daily_total, start_date, end_date):

        start_d = datetime.strptime(start_date, '%Y-%m-%d')
        end_d = datetime.strptime(end_date, '%Y-%m-%d')
        num_days = (end_d - start_d).days + 1

        days_in_month = calendar.monthrange(end_d.year, end_d.month)[1]
        monthly_rate = (days_in_month * daily_total)
        weekly_rate = (daily_total * 7)
        amount = monthly_rate

        if num_days < 7:
            amount = num_days * daily_total
        elif num_days >= 7 and num_days < days_in_month:
            days = num_days % 7
            weeks = math.floor(num_days / 7)
            amount = (days * daily_total) + (weeks * weekly_rate)
            if amount > monthly_rate:
                amount = monthly_rate

        return amount

    # add weekly, add day, add term
    # todo figure out how to go from daily to weekly to monthly

    def calc_amd_rate(self, rate_type, line, line_amount, start_date, end_date):

        '''
        pu_monthly = 663.00
        pu_weekly = 140.00
        pu_daily = 31.90

        cc_monthly = 664.00
        cc_weekly = 200.00
        cc_daily = 35.50

        ts_weekly = 475.00
        ts_daily = 95.00

        tr_weekly = 575.00
        tr_daily = 135.00

        ft_monthly = 2350.00
        '''

        start_d = datetime.strptime(start_date, '%Y-%m-%d')
        end_d = datetime.strptime(end_date, '%Y-%m-%d')
        num_days = (end_d - start_d).days + 1  # should be +1
        days_in_month = calendar.monthrange(end_d.year, end_d.month)[1]
        amount = 0
        rate = line_amount
        if rate_type == 'amd_daily_pu':
            pu_monthly = line.monthly_rate
            pu_weekly = line.weekly_rate
            pu_daily = line.daily_rate
            if num_days < 7:
                amount = num_days * pu_daily
                rate = pu_daily
                if amount > pu_weekly:
                    amount = pu_weekly
                    rate = pu_weekly / 7
            elif num_days >= 7 and num_days < days_in_month:
                amount = num_days * (pu_weekly / 7)
                rate = pu_weekly / 7
                if amount > pu_monthly:
                    amount = pu_monthly
                    rate = pu_monthly / 30
            elif num_days == days_in_month:
                amount = pu_monthly
                rate = pu_monthly / days_in_month
            elif num_days > days_in_month:
                amount = num_days * (pu_monthly / 30)
                rate = pu_monthly / 30

        if rate_type == 'amd_daily_cc':
            cc_monthly = line.monthly_rate
            cc_weekly = line.weekly_rate
            cc_daily = line.daily_rate

            if num_days < 7:
                amount = num_days * cc_daily
                rate = cc_daily
                if amount > cc_weekly:
                    amount = cc_weekly
                    rate = cc_weekly / 7
            elif num_days >= 7 and num_days < days_in_month:
                amount = num_days * (cc_weekly / 7)
                rate = cc_weekly / 7
                if amount > cc_monthly:
                    amount = cc_monthly
                    rate = cc_monthly / 30
            elif num_days == days_in_month:
                amount = cc_monthly
                rate = cc_monthly / days_in_month
            elif num_days > days_in_month:
                amount = num_days * (cc_monthly / 30)
                rate = cc_monthly / 30

        if rate_type == 'amd_daily_ts':
            ts_weekly = line.weekly_rate
            ts_daily = line.daily_rate

            if num_days < 7:
                amount = num_days * ts_daily
                rate = ts_daily
                if amount > ts_weekly:
                    amount = ts_weekly
                    rate = ts_weekly / 7
            else:
                amount = num_days * (ts_weekly / 7)
                rate = ts_weekly / 7
        if rate_type == 'amd_daily_tr':
            tr_weekly = line.weekly_rate
            tr_daily = line.daily_rate

            if num_days < 7:
                amount = num_days * tr_daily
                rate = tr_daily

                if amount > tr_weekly:
                    amount = tr_weekly
                    rate = tr_weekly / 7
            else:
                amount = num_days * (tr_weekly / 7)
                rate = tr_weekly / 7

        if rate_type == 'amd_daily_ft':
            ft_monthly = line.monthly_rate

            amount = num_days * (ft_monthly / 30)
            rate = ft_monthly / 30

        return {'amount': amount, 'formula': '', 'rate': rate}

    def calc_stelco_rate(self, rate_type, line_amount, start_date, end_date):
        start_d = datetime.strptime(start_date, '%Y-%m-%d')
        end_d = datetime.strptime(end_date, '%Y-%m-%d')
        date_delta = relativedelta.relativedelta(end_d, start_d)
        num_days = date_delta.days + 1  # assumes current day for billing
        days_in_month = calendar.monthrange(end_d.year, end_d.month)[1]
        the_amount = line_amount
        the_formula = ''
        res = {'amount': the_amount, 'formula': the_formula}

        amount = line_amount
        if rate_type == 'stelco_daily':
            amount = num_days * line_amount
        elif rate_type == 'stelco_monthly':
            daily_rate = (line_amount * 12.5) / 100
            weekly_rate = (line_amount * 45) / 100

            if num_days < 7:
                amount = num_days * daily_rate
            # elif num_days >= 7 and num_days < days_in_month:
            #   amount = (num_days * daily_rate) + (weeks * weekly_rate)

        return amount

    def calculate_line_amount(self, product, line, line_amount, start_date, end_date, lease):

        print("CALC AMOUNT FOR : " + product.categ_id.name)
        the_amount = line_amount
        the_formula = ''
        res = {'amount': the_amount, 'formula': the_formula, 'rate': ''}
        if lease.lease_return_date:
            end_date = lease.lease_return_date

        if product.rate_type == 'monthly' or product.rate_type == 'stelco_monthly':
            # future value add
            the_dict = self.calc_rate_monthly_lease(line_amount, start_date, end_date, lease)
            res['amount'] = the_dict['amount']
            res['formula'] = the_dict['formula']
            res['rate'] = the_dict['rate']
        elif product.rate_type == 'weekly' or product.rate_type == 'stelco_weekly':
            the_dict = self.calc_rate_weekly_lease(lease.discount_rate_calc, line_amount, start_date, end_date)
            res['amount'] = the_dict['amount']
            res['formula'] = the_dict['formula']
            res['rate'] = the_dict['rate']
        elif product.rate_type == 'daily' or product.rate_type == 'stelco_daily':
            the_dict = self.calc_rate_daily_lease(lease.discount_rate_calc, line_amount, start_date, end_date)
            res['amount'] = the_dict['amount']
            res['formula'] = the_dict['formula']
            res['rate'] = the_dict['rate']
        elif product.rate_type == 'stelco_daily_van':
            the_dict = self.calc_rate_daily_lease(False, line_amount, start_date, end_date)
            res['amount'] = the_dict['amount']
            res['formula'] = the_dict['formula']
            res['rate'] = the_dict['rate']
        elif product.rate_type == 'biweekly':
            res['amount'] = self.calc_biweekly_lease(line_amount, lease)
        elif 'amd' in product.rate_type:
            the_dict = self.calc_amd_rate(product.rate_type, line, line_amount, start_date, end_date)
            res['amount'] = the_dict['amount']
            res['formula'] = the_dict['formula']
            res['rate'] = the_dict['rate']
        # elif 'stelco' in product.rate_type:
        #    res['amount'] = self.calc_stelco_rate(product.rate_type, line_amount, start_date, end_date)

        return res

    lease_ids = fields.Many2many('thomaslease.lease', string="Lease", default=_default_lease_ids)
    invoice_date = fields.Date(string="Invoice Date", default=_default_invoice_date)
    invoice_due_date = fields.Date(string="Invoice Due Date", default=_default_invoice_due_date)
    invoice_posting_date = fields.Date(string="Invoice Posting Date", default=_default_invoice_posting_date)
    invoice_start_date = fields.Date(string="Invoice From", default=_default_invoice_start_date)
    invoice_end_date = fields.Date(string="Invoice To", default=_default_invoice_end_date)

    def aggregate_lease_selected(self, a_lease):
        resp = False
        for lease in self.lease_ids:
            if a_lease.id == lease.id:
                resp = True
        return resp

    def determine_last_invoice_to(self, lease):
        last_to_date = datetime.strptime(lease.invoice_to, '%Y-%m-%d')
        end_date = last_to_date + relativedelta.relativedelta(months=+1)
        if lease.lease_return_date:
            end_date = datetime.strptime(lease.lease_return_date, '%Y-%m-%d')
        elif lease.rate_type == 'Bi-Weekly':
            end_date = last_to_date + relativedelta.relativedelta(weeks=+4)

        return end_date


    def create_dofasco_monthly_invoice_line_description(self, lease):
        month_amd = datetime.strptime(lease.invoice_from, '%Y-%m-%d').strftime('%b')
        year_amd = datetime.strptime(lease.invoice_from, '%Y-%m-%d').strftime('%Y')
        if lease.vehicle_id.unit_no:
            description = month_amd + ' ' + year_amd + ' - Monthly Lease: for Unit # ' + lease.vehicle_id.unit_no
        else:
            description = month_amd + ' ' + year_amd + ' - Monthly Lease'

        return description

    def create_monthly_invoice_line_description(self, start_d, end_d, month, year, lease):
        just_days = (end_d - start_d).days + 1
        days_in_end_month = calendar.monthrange(end_d.year, end_d.month)[1]
        unit_str = ''
        if lease.vehicle_id.unit_no:
            unit_str = lease.vehicle_id.unit_no

        if end_d.month == start_d.month and just_days == days_in_end_month:
            description = month + ' ' + year + ' - Monthly Lease: for Unit # ' + unit_str
        else:
            start_d_str = start_d.strftime('%b %d')
            end_d_str = end_d.strftime('%b %d')
            year_end_str = end_d.strftime('%Y')
            year_start_str = ''

            if end_d.year != start_d.year:
                year_start_str = ' ' + start_d.strftime('%Y')

            description = start_d_str + year_start_str + ' - ' + end_d_str + ' (' + str(just_days) + ' days) ' \
                          + year_end_str + ' - Lease: for Unit # ' + unit_str

        return description

    def create_daily_invoice_line_description(self, start_date, end_date, lease):
        start_date_str = start_date.strftime('%b %d')
        end_date_str = end_date.strftime('%b %d')
        year = end_date.strftime('%Y')

        if lease.vehicle_id.unit_no:
            description = start_date_str + ' - ' + end_date_str + ' ' + year + ' - Daily Lease: for Unit # ' + lease.vehicle_id.unit_no
        else:
            description = start_date_str + ' - ' + end_date_str + ' ' + year + ' - Daily Lease'

        return description

    @api.model
    def record_normal_invoice2(self, the_lease):
        accounting_invoice = self.env['account.move']

        line_ids = []
        next_month_line_ids = []
        new_invoices = []
        lease_invoices = the_lease.id.invoice_ids.ids
        unit_invoices = the_lease.id.vehicle_id.lease_invoice_ids.ids
        month = datetime.strptime(the_lease.id.invoice_from, '%Y-%m-%d').strftime('%b')
        year = datetime.strptime(the_lease.id.invoice_from, '%Y-%m-%d').strftime('%Y')
        dt_inv_to = datetime.strptime(the_lease.id.invoice_to, '%Y-%m-%d')
        end_of_month = calendar.monthrange(dt_inv_to.year, dt_inv_to.month)[1]
        inv_date = self.invoice_date

        if the_lease.id.run_initial_invoicing:
            last_to_date = datetime.strptime(the_lease.id.invoice_to, '%Y-%m-%d')
            last_from_date = datetime.strptime(the_lease.id.invoice_from, '%Y-%m-%d')

            prev_relative_month = last_to_date + relativedelta.relativedelta(months=-1)

            prev_month_from = datetime.strptime(the_lease.id.billing_start_date, '%Y-%m-%d')
            prev_month_days = calendar.monthrange(prev_relative_month.year, prev_relative_month.month)[1]
            prev_month_to = last_from_date + relativedelta.relativedelta(days=-1)
            prev_days_quantity = relativedelta.relativedelta(prev_month_to, prev_month_from).days + 1
            # datetime(prev_relative_month.year, prev_relative_month.month, prev_month_days)
            prev_month = prev_month_from.strftime('%b')
            prev_year = prev_month_from.strftime('%Y')

            if "Dofasco" in the_lease.id.customer_id.name:
                inv_date = datetime(last_to_date.year, last_to_date.month, 1)

        for line in the_lease.id.lease_lines:
            product = line.product_id
            invoice_line = self.env['account.move.line']
            res = self.calculate_line_amount(
                product, line, line.price, the_lease.id.invoice_from, the_lease.id.invoice_to, the_lease.id)
            line_amount = res['amount']
            start_date = datetime.strptime(the_lease.id.invoice_from, '%Y-%m-%d').date()

            if the_lease.id.lease_return_date:
                end_date = datetime.strptime(the_lease.id.lease_return_date, '%Y-%m-%d').date()
            else:
                end_date = datetime.strptime(the_lease.id.invoice_to, '%Y-%m-%d').date()

            num_days = relativedelta.relativedelta(end_date, start_date).days + 1
            pro_rated = ''
            quantity = 1

            unit_str = ''
            if the_lease.id.vehicle_id.unit_no:
                unit_str = "Unit # " + str(the_lease.id.vehicle_id.unit_no)
            else:
                unit_str = str(product.name)

            if num_days < end_of_month and not the_lease.id.rate_type == 'Bi-Weekly' \
                    and not the_lease.id.rate_type == 'Monthly' and not the_lease.id.rate_type == 'Stelco Monthly':

                description = self.create_daily_invoice_line_description(start_date, end_date, the_lease.id)
                quantity = num_days
                line_amount = res['rate']
                # start_date_str + ' to ' + end_date_str + ' ' + year + 'Lease for Unit # for ' + the_lease.id.vehicle_id.unit_no

            elif the_lease.id.rate_type == 'Bi-Weekly':
                if not the_lease.id.last_invoice_to:
                    last_to_date = datetime.strptime(the_lease.id.billing_start_date, '%Y-%m-%d')
                else:
                    last_to_date = datetime.strptime(the_lease.id.last_invoice_to, '%Y-%m-%d')
                # changing description model
                last_to_date = datetime.strptime(the_lease.id.invoice_from, '%Y-%m-%d')
                # end
                start_date = last_to_date  # + relativedelta.relativedelta(days=+1)

                if the_lease.id.lease_return_date:
                    end_date = datetime.strptime(the_lease.id.lease_return_date, '%Y-%m-%d')
                # else:
                #     end_date = last_to_date + relativedelta.relativedelta(weeks=+4)

                start_date_str = start_date.strftime('%b %d')
                end_date_str = end_date.strftime('%b %d')
                description = 'Bi Weekly Lease for ' + unit_str + ' - ' + \
                              start_date_str + ' to ' + end_date_str + ', ' + year
                line_amount = line.price
                rel_days = relativedelta.relativedelta(end_date, start_date).days
                rel_weeks = relativedelta.relativedelta(end_date, start_date).weeks
                quantity = '{0:,.2f}'.format((rel_days + 1) / 14)
                # (rel_weeks + (rel_days - (rel_weeks*7))/7)/ 2
                # (3 + ((rel_days - (rel_weeks * 7)) / 7)) / 2
            elif the_lease.id.rate_type == 'Daily' or the_lease.id.rate_type == 'Stelco Daily':
                quantity = num_days
                line_amount = res['rate']  # line.price

                description = self.create_daily_invoice_line_description(start_date, end_date, the_lease.id)
                # \Daily Lease for Unit # ' + the_lease.id.vehicle_id.unit_no + ' - '+ \
                # start_date_str + ' to ' + end_date_str + ' ' + year

            elif the_lease.id.rate_type == 'Weekly' or the_lease.id.rate_type == 'Stelco Weekly':
                days = num_days % 7
                weeks = math.floor(num_days / 7)
                t_quantity = str(weeks) + " weeks " + str(days) + " days "
                line_amount = res["rate"]  # line.price / 7
                quantity = num_days  # (weeks*7) + days
                description = month + ' ' + year + ' - ' + t_quantity + 'Lease: for Unit # ' + the_lease.id.vehicle_id.unit_no
            elif the_lease.id.rate_type == 'Monthly' or the_lease.id.rate_type == 'Stelco Monthly':
                # if "Dofasco" in the_lease.id.customer_id.name:
                #    description = self.create_dofasco_monthly_invoice_line_description(the_lease.id)
                # else:
                #    description = self.create_monthly_invoice_line_description(start_date, end_date, month, year,
                #                                                               the_lease.id)
                description = self.create_monthly_invoice_line_description(start_date, end_date, month, year,
                                                                           the_lease.id)
            else:
                description = line.description

            line_id = invoice_line.create({
                'product_id': product.id,
                'lease_line_id': line.id,
                'vehicle_id': line.vehicle_id.id,
                'price_unit': line_amount,
                'quantity': quantity,
                'name': description,
                'invoice_line_tax_ids': [(6, 0, line.product_id.taxes_id.ids)],
                'account_id': line.product_id.property_account_income_id.id
            })
            # call set taxes to set them...otherwise the relationships aren't set properly
            # line_id._set_taxes()
            line_id.price_unit = line_amount
            line_ids.append(line_id.id)

        comment = ''
        if len(the_lease.id.lease_lines) == 1:
            comment = res['formula']

        # TODO: move this out of the line for loop since I think it would create multiple invoice per lease line
        a_invoice = accounting_invoice.create({
            'partner_id': the_lease.id.customer_id.id,
            'vehicle_id': the_lease.id.vehicle_id.id,
            'comment': comment,
            'invoice_date': inv_date,  # self.invoice_date,#the_lease.id.invoice_generation_date,
            'invoice_date_due': the_lease.id.invoice_due_date,
            'invoice_from': the_lease.id.invoice_from,
            'invoice_to': the_lease.id.invoice_to,
            'invoice_posting_date': the_lease.id.invoice_posting_date,
            'invoice_generation_date': the_lease.id.invoice_generation_date,
            'type': 'out_invoice',
            # 'account_id': product.property_account_income_id.id,
            'state': 'draft',
            'po_number': the_lease.id.po_number,
            'partner_shipping_id': the_lease.id.partner_shipping_id.id,
            'requires_manual_calculations': the_lease.id.requires_manual_calculations,
            'invoice_line_ids': [(6, 0, line_ids)]
        })
        lease_invoices.append(a_invoice.id)
        new_invoices.append(a_invoice)
        unit_invoices.append(a_invoice.id)
        if the_lease.id.run_initial_invoicing:
            resp = {}
            for next_line in the_lease.id.lease_lines:
                product = next_line.product_id
                taxes = next_line.product_id.taxes_id.id
                res = self.calculate_line_amount(product, next_line, next_line.price, prev_month_from.strftime(
                    '%Y-%m-%d'), prev_month_to.strftime('%Y-%m-%d'), the_lease.id)
                next_line_amount = res['amount']
                num_days = relativedelta.relativedelta(prev_month_to, prev_month_from).days + 1

                pro_rated = prev_month + ' ' + prev_year
                quantity = 1

                unit_str = ''
                if the_lease.id.vehicle_id.unit_no:
                    unit_str = "Unit # " + str(the_lease.id.vehicle_id.unit_no)
                else:
                    unit_str = str(product.name)

                if num_days < prev_month_days and not the_lease.id.rate_type == 'Bi-Weekly' \
                        and not the_lease.id.rate_type == 'Monthly':

                    description = self.create_daily_invoice_line_description(prev_month_from, prev_month_to,
                                                                             the_lease.id)
                    quantity = prev_days_quantity
                    next_line_amount = res['rate']

                elif the_lease.id.rate_type == 'Bi-Weekly':  # need to determine what to do here
                    if not the_lease.id.last_invoice_to:
                        last_to_date = datetime.strptime(the_lease.id.billing_start_date, '%Y-%m-%d')
                    else:
                        last_to_date = datetime.strptime(the_lease.id.last_invoice_to, '%Y-%m-%d')

                    # changing description model
                    # changing description model
                    last_to_date = datetime.strptime(prev_month_from, '%Y-%m-%d')
                    # end

                    start_date = last_to_date  # + relativedelta.relativedelta(days=+1)

                    if the_lease.id.lease_return_date:
                        end_date = datetime.strptime(the_lease.id.lease_return_date, '%Y-%m-%d')

                    start_date_str = start_date.strftime('%b %d')
                    end_date_str = end_date.strftime('%b %d')
                    description = 'Bi Weekly Lease for ' + unit_str + ' - ' + \
                                  start_date_str + ' to ' + end_date_str + ', ' + year
                    next_line_amount = next_line.price
                    rel_days = relativedelta.relativedelta(end_date, start_date).days
                    rel_weeks = relativedelta.relativedelta(end_date, start_date).weeks
                    quantity = '{0:,.2f}'.format((rel_days + 1) / 14)
                elif the_lease.id.rate_type == 'Daily' or the_lease.id.rate_type == 'stelco_daily':
                    quantity = num_days  # prev_days_quantity
                    next_line_amount = res["rate"]  # next_line.price

                    description = self.create_daily_invoice_line_description(prev_month_from, prev_month_to,
                                                                             the_lease.id)
                    # description = start_date_str + ' - ' + end_date_str + ' ' + year + ' - Lease: for Unit # ' + the_lease.id.vehicle_id.unit_no

                elif the_lease.id.rate_type == 'Weekly' or the_lease.id.rate_type == 'stelco_weekly':
                    days = prev_month_days % 7
                    weeks = math.floor(prev_month_days / 7)
                    next_line_amount = res["rate"]  # next_line.price / 7
                    quantity = num_days  # (weeks * 7) + days
                    t_quantity = str(weeks) + " weeks " + str(days) + " days "

                    description = month + ' ' + year + ' - ' + t_quantity + 'Lease: for Unit # ' + the_lease.id.vehicle_id.unit_no
                elif the_lease.id.rate_type == 'Monthly' or the_lease.id.rate_type == 'stelco_monthly':
                    # if "Dofasco" in the_lease.id.customer_id.name:
                    #     description = self.create_dofasco_monthly_invoice_line_description(the_lease.id)
                    # else:
                    #     description = self.create_monthly_invoice_line_description(prev_month_from, prev_month_to,
                    #                                                                prev_month, prev_year,
                    #                                                                the_lease.id)
                    description = self.create_monthly_invoice_line_description(prev_month_from, prev_month_to,
                                                                               prev_month, prev_year,
                                                                               the_lease.id)
                else:
                    description = next_line.description

                next_month_line_id = invoice_line.create({
                    'product_id': next_line.product_id.id,
                    'lease_line_id': next_line.id,
                    'vehicle_id': next_line.vehicle_id.id,
                    'price_unit': next_line_amount,
                    'quantity': quantity,
                    'name': description,
                    'invoice_line_tax_ids': [(6, 0, next_line.product_id.taxes_id.ids)],
                    'account_id': next_line.product_id.property_account_income_id.id
                })

                # next_month_line_id._set_taxes()
                next_month_line_id.price_unit = next_line_amount

                next_month_line_ids.append(next_month_line_id.id)

            # moved this in the loop...test initial invoicing again
            comment = ''
            if len(the_lease.id.lease_lines) == 1:
                comment = res['formula']
            a_next_invoice = accounting_invoice.create({
                'partner_id': the_lease.id.customer_id.id,
                'vehicle_id': the_lease.id.vehicle_id.id,
                'comment': comment,
                'invoice_date': self.invoice_date,  # the_lease.id.invoice_generation_date,
                'invoice_date_due': the_lease.id.invoice_due_date,
                'invoice_from': prev_month_from,
                'invoice_to': prev_month_to,
                'invoice_posting_date': the_lease.id.invoice_generation_date,
                'invoice_generation_date': the_lease.id.invoice_generation_date,
                'type': 'out_invoice',
                # 'account_id': product.property_account_income_id.id,
                'state': 'draft',
                'po_number': the_lease.id.po_number,
                # 'partner_invoice_id': the_lease.id.partner_invoice_id.id,
                'partner_shipping_id': the_lease.id.partner_shipping_id.id,
                'requires_manual_calculations': the_lease.id.requires_manual_calculations,
                'invoice_line_ids': [(6, 0, next_month_line_ids)]

            })

            lease_invoices.append(a_next_invoice.id)
            new_invoices.append(a_next_invoice)

            unit_invoices.append(a_next_invoice.id)

        the_lease.id.invoice_ids = [(6, 0, lease_invoices)]
        the_lease.id.vehicle_id.with_context(skip_update=True).lease_invoice_ids = [(6, 0, unit_invoices)]
        the_lease.id.run_initial_invoicing = False
        the_lease.id.last_invoice_to = self.determine_last_invoice_to(the_lease.id)
        return new_invoices

    @api.model
    def record_aggregate_invoice_tbd(self, customers, the_wizard):
        new_invoices = []
        for customer in customers:
            accounting_invoice = self.env['account.move']
            po_numbers = []
            ap_groups = []
            aggregation_ids = []

            month = datetime.strptime(the_wizard.invoice_date, '%Y-%m-%d').strftime('%b')
            year = datetime.strptime(the_wizard.invoice_date, '%Y-%m-%d').strftime('%Y')
            inv_date = the_wizard.invoice_date

            for lease in self.web_progress_iter(customer.lease_agreements, msg="Processing Aggregate Customers"):
                lease.aggregation_id = 'False'  # cleanse any dirty agg ids
                if self.aggregate_lease_selected(lease):
                    if lease.po_number:
                        lease.aggregation_id = lease.po_number
                        po_numbers.append(lease.po_number)
                        aggregation_ids.append(lease.aggregation_id)
                    else:
                        if lease.ap_contact_ids:
                            ag_id = ''
                            for ap_id in lease.ap_contact_ids:
                                ag_id += str(ap_id.id)
                            lease.aggregation_id = ag_id
                            ap_groups.append(lease.ap_contact_ids)
                            aggregation_ids.append(ag_id)

                        else:
                            raise models.ValidationError(
                                'Lease agreement issue: Customer is marked for Aggregate '
                                'invoicing but lease agreement does not contain a PO or AP Contact '
                                'Agreement: ' + lease.lease_number + "Customer: " + lease.customer_id.name
                            )

            # make po_number list unique
            po_numbers = list(dict.fromkeys(po_numbers))
            aggregation_ids = list(dict.fromkeys(aggregation_ids))
            # find leases by PO
            for ags_id in self.web_progress_iter(aggregation_ids, msg="Locating Aggregate IDs"):
                line_ids = []
                next_month_line_ids = []
                lease_invoices = []
                initial_lease_ids = []
                initial_lease_invoices = []
                initial_unit_invoices = []
                unit_invoices = []
                l_resp = {}
                n_resp = {}
                leases = self.env['thomaslease.lease'].search(
                    [('aggregation_id', '=', ags_id), ('customer_id', '=', customer.id)])

                for lease in self.web_progress_iter(leases, msg="Generating Aggregate Invoice"):
                    if self.aggregate_lease_selected(lease):
                        print("==========aggregate lease agreement loop===================")
                        dt_inv_to = datetime.strptime(lease.invoice_to, '%Y-%m-%d')
                        end_of_month = calendar.monthrange(dt_inv_to.year, dt_inv_to.month)[1]

                        if lease.run_initial_invoicing:
                            last_to_date = datetime.strptime(lease.invoice_to, '%Y-%m-%d')
                            last_from_date = datetime.strptime(lease.invoice_from, '%Y-%m-%d')

                            prev_relative_month = last_to_date + relativedelta.relativedelta(months=-1)

                            prev_month_from = datetime.strptime(lease.billing_start_date, '%Y-%m-%d')
                            prev_month_days = calendar.monthrange(prev_relative_month.year, prev_relative_month.month)[
                                1]
                            prev_month_to = last_from_date + relativedelta.relativedelta(days=-1)
                            # datetime(prev_relative_month.year, prev_relative_month.month,prev_month_days)
                            prev_month = prev_month_from.strftime('%b')
                            prev_year = prev_month_from.strftime('%Y')

                        for line in lease.lease_lines:
                            product = line.product_id
                            invoice_line = self.env['account.move.line']
                            l_resp = self.calculate_line_amount(
                                product, line, line.price, lease.invoice_from, lease.invoice_to, lease)
                            line_amount = l_resp['amount']
                            start_date = datetime.strptime(lease.invoice_from, '%Y-%m-%d').date()
                            end_date = datetime.strptime(lease.invoice_to, '%Y-%m-%d').date()

                            num_days = (end_date - start_date).days + 1
                            quantity = 1
                            unit_str = ''
                            if lease.vehicle_id.unit_no:
                                unit_str = 'Unit # ' + str(lease.vehicle_id.unit_no)
                            else:
                                unit_str = str(product.name)

                            if num_days < end_of_month and not lease.rate_type == 'Bi-Weekly' \
                                    and not lease.rate_type == 'Monthly' and not lease.rate_type == 'Stelco Monthly':

                                description = self.create_daily_invoice_line_description(start_date, end_date,
                                                                                         lease)
                                quantity = num_days
                                line_amount = l_resp['rate']

                            elif lease.rate_type == 'Bi-Weekly':
                                if not lease.last_invoice_to:
                                    last_to_date = datetime.strptime(lease.billing_start_date, '%Y-%m-%d')
                                else:
                                    last_to_date = datetime.strptime(lease.last_invoice_to, '%Y-%m-%d')

                                # changing description model
                                last_to_date = datetime.strptime(lease.invoice_from, '%Y-%m-%d')
                                # end

                                start_date = last_to_date  # + relativedelta.relativedelta(days=+1)

                                if lease.lease_return_date:
                                    end_date = datetime.strptime(lease.lease_return_date, '%Y-%m-%d')
                                # else:
                                #    end_date = last_to_date + relativedelta.relativedelta(weeks=+4)

                                start_date_str = start_date.strftime('%b %d')
                                end_date_str = end_date.strftime('%b %d')
                                description = 'Bi Weekly Lease for ' + unit_str + ' - ' + \
                                              start_date_str + ' to ' + end_date_str + ', ' + year
                                line_amount = line.price
                                rel_days = relativedelta.relativedelta(end_date, start_date).days
                                rel_weeks = relativedelta.relativedelta(end_date, start_date).weeks
                                quantity = '{0:,.2f}'.format(
                                    (rel_days + 1) / 14)  # (rel_weeks + (rel_days - (rel_weeks * 7)) / 7) / 2

                            elif lease.rate_type == 'Daily' or lease.rate_type == 'Stelco Daily':
                                quantity = num_days
                                line_amount = l_resp['rate']  # line.price

                                description = self.create_daily_invoice_line_description(start_date, end_date, lease)
                                # start_date_str + ' - ' + end_date_str + ' ' + year + ' - Lease: for Unit # ' + the_lease.id.vehicle_id.unit_no

                            elif lease.rate_type == 'Weekly' or lease.rate_type == 'Stelco Weekly':
                                days = num_days % 7
                                weeks = math.floor(num_days / 7)
                                line_amount = l_resp["rate"]  # line.price / 7
                                quantity = (weeks * 7) + days
                                t_quantity = str(weeks) + " weeks " + str(days) + " days "
                                description = month + ' ' + year + ' - ' + t_quantity + 'Lease: for Unit # ' + lease.vehicle_id.unit_no
                            elif lease.rate_type == 'Monthly' or lease.rate_type == 'Stelco Monthly':
                                description = self.create_monthly_invoice_line_description(start_date, end_date, month,
                                                                                           year, lease)
                            else:
                                description = line.description

                            # create the invoice line
                            line_id = invoice_line.create({
                                'product_id': product.id,
                                'lease_line_id': line.id,
                                'vehicle_id': line.vehicle_id.id,
                                'price_unit': line_amount,
                                'quantity': quantity,
                                'name': description,
                                'invoice_line_tax_ids': [(6, 0, product.taxes_id.ids)],
                                'account_id': product.property_account_income_id.id
                            })

                            # call set taxes to set them...otherwise the relationships aren't set properly
                            # line_id._set_taxes()
                            line_id.price_unit = line_amount
                            line_ids.append(line_id.id)
                            if lease.invoice_ids:
                                lease_invoices.extend(lease.invoice_ids.ids)

                            for l_id in lease.vehicle_id.lease_invoice_ids:
                                if l_id.id not in unit_invoices:
                                    unit_invoices.append(l_id.id)
                            # if lease.vehicle_id.lease_invoice_ids:
                            #    if lease.vehicle_id.lease_invoice_ids.ids not in unit_invoices:
                            #        unit_invoices.extend(lease.vehicle_id.lease_invoice_ids.ids)

                        if lease.run_initial_invoicing:
                            for next_line in lease.lease_lines:
                                n_resp = self.calculate_line_amount(product, next_line, next_line.price,
                                                                    prev_month_from.strftime(
                                                                        '%Y-%m-%d'), prev_month_to.strftime('%Y-%m-%d'),
                                                                    lease)
                                next_line_amount = n_resp['amount']
                                num_days = (prev_month_to - prev_month_from).days + 1
                                date_delta = relativedelta.relativedelta(prev_month_from, prev_month_to)
                                num_months = date_delta.months
                                num_years = date_delta.years

                                pro_rated = prev_month + ' ' + prev_year
                                quantity = 1
                                if num_days < prev_month_days and not lease.rate_type == 'Bi-Weekly' \
                                        and not lease.rate_type == 'Monthly':
                                    description = self.create_daily_invoice_line_description(prev_month_from,
                                                                                             prev_month_to,
                                                                                             lease)
                                    quantity = num_days
                                    next_line_amount = n_resp['rate']

                                elif lease.rate_type == 'Bi-Weekly':  # need to determine what to do here
                                    if not lease.last_invoice_to:
                                        last_to_date = datetime.strptime(lease.billing_start_date, '%Y-%m-%d')
                                    else:
                                        last_to_date = datetime.strptime(lease.last_invoice_to, '%Y-%m-%d')

                                    start_date = last_to_date + relativedelta.relativedelta(days=+1)

                                    if lease.lease_return_date:
                                        end_date = datetime.strptime(lease.lease_return_date, '%Y-%m-%d')
                                    else:
                                        end_date = last_to_date + relativedelta.relativedelta(weeks=+4)

                                    start_date_str = start_date.strftime('%b %d')
                                    end_date_str = end_date.strftime('%b %d')
                                    description = 'Bi Weekly Lease for Unit # ' + lease.vehicle_id.unit_no + ' - ' + \
                                                  start_date_str + ' to ' + end_date_str + ', ' + year
                                    next_line_amount = next_line.price
                                    rel_days = relativedelta.relativedelta(end_date, start_date).days
                                    rel_weeks = relativedelta.relativedelta(end_date, start_date).weeks
                                    quantity = '{0:,.2f}'.format((rel_days + 1) / 14)
                                    # (rel_weeks + (rel_days - (rel_weeks * 7)) / 7) / 2
                                elif lease.rate_type == 'Daily' or lease.rate_type == 'stelco_daily':
                                    quantity = num_days
                                    next_line_amount = n_resp["rate"]  # next_line.price
                                    description = self.create_daily_invoice_line_description(prev_month_from,
                                                                                             prev_month_to, lease)
                                elif lease.rate_type == 'Weekly' or lease.rate_type == 'stelco_weekly':
                                    days = prev_month_days % 7
                                    weeks = math.floor(prev_month_days / 7)
                                    next_line_amount = n_resp["rate"]  # next_line.price / 7
                                    quantity = (weeks * 7) + days
                                    t_quantity = str(weeks) + " week " + str(days) + " days "
                                    description = month + ' ' + year + ' - ' + t_quantity + 'Lease: for Unit # ' + lease.vehicle_id.unit_no
                                elif lease.rate_type == 'Monthly' or lease.rate_type == 'stelco_monthly':
                                    # if "Dofasco" in lease.customer_id.name:
                                    #     description = self.create_dofasco_monthly_invoice_line_description(lease)
                                    # else:
                                    #     description = self.create_monthly_invoice_line_description(prev_month_from,
                                    #                                                                prev_month_to,
                                    #                                                                prev_month,
                                    #                                                                prev_year, lease)
                                    description = self.create_monthly_invoice_line_description(prev_month_from,
                                                                                               prev_month_to,
                                                                                               prev_month,
                                                                                               prev_year, lease)
                                else:
                                    description = next_line.description

                                next_month_line_id = invoice_line.create({
                                    'product_id': product.id,
                                    'lease_line_id': next_line.id,
                                    'vehicle_id': next_line.vehicle_id.id,
                                    'price_unit': next_line_amount,
                                    'quantity': quantity,
                                    'name': description,
                                    'invoice_line_tax_ids': [(6, 0, product.taxes_id.ids)],
                                    'account_id': product.property_account_income_id.id
                                })

                                # next_month_line_id._set_taxes()
                                next_month_line_id.price_unit = next_line_amount

                                next_month_line_ids.append(next_month_line_id.id)
                                if lease.invoice_ids:
                                    initial_lease_invoices.extend(lease.invoice_ids.ids)
                                if lease.vehicle_id.lease_invoice_ids:
                                    initial_unit_invoices.extend(lease.vehicle_id.lease_invoice_ids.ids)

                            if "Dofasco" in lease.customer_id.name:
                                inv_date = datetime(last_to_date.year, last_to_date.month, 1)
                            comment = ''
                            if len(leases) == 1 and len(lease.lease_lines) == 1:
                                comment = n_resp['formula']
                            initial_lease_ids.append(lease.id)
                            a_next_invoice = accounting_invoice.create({
                                'partner_id': lease.customer_id.id,
                                'vehicle_id': lease.vehicle_id.id,
                                'comment': comment,
                                'invoice_date': inv_date,  # lease.invoice_generation_date,
                                'invoice_date_due': lease.invoice_due_date,
                                'invoice_from': prev_month_from,
                                'invoice_to': prev_month_to,
                                'invoice_posting_date': lease.invoice_generation_date,
                                'invoice_generation_date': lease.invoice_generation_date,
                                'type': 'out_invoice',
                                'initial_invoice': True,
                                'state': 'draft',
                                'po_number': lease.po_number,
                                # 'partner_invoice_id': lease.partner_invoice_id.id,
                                'partner_shipping_id': lease.partner_shipping_id.id,
                                'requires_manual_calculations': lease.requires_manual_calculations,
                                'invoice_line_ids': [(6, 0, next_month_line_ids)]
                            })

                            # lease_invoices.append(a_next_invoice.id)
                            initial_lease_invoices.append(a_next_invoice.id)
                            new_invoices.append(a_next_invoice)
                            # unit_invoices.append(a_next_invoice.id)
                            initial_unit_invoices.append(a_next_invoice.id)
                            lease.aggregation_id = False
                # lease.run_initial_invoicing = False
                # TODO: move this out of the line for loop since I think it would create multiple invoice per lease line
                comment = ''
                if len(leases) == 1 and len(lease.lease_lines) == 1:
                    comment = l_resp['formula']
                a_invoice = accounting_invoice.create({
                    'partner_id': lease.customer_id.id,
                    'vehicle_id': lease.vehicle_id.id,
                    'comment': comment,
                    'invoice_date': the_wizard.invoice_date,  # lease.invoice_generation_date,
                    'invoice_date_due': lease.invoice_due_date,
                    'invoice_from': lease.invoice_from,
                    'invoice_to': lease.invoice_to,
                    'invoice_posting_date': lease.invoice_posting_date,
                    'invoice_generation_date': lease.invoice_generation_date,
                    'type': 'out_invoice',
                    'state': 'draft',
                    'po_number': lease.po_number,
                    # 'partner_invoice_id': lease.partner_invoice_id.id,
                    'partner_shipping_id': lease.partner_shipping_id.id,
                    'requires_manual_calculations': lease.requires_manual_calculations,
                    'invoice_line_ids': [(6, 0, line_ids)]
                })

                lease_invoices.append(a_invoice.id)
                new_invoices.append(a_invoice)
                if a_invoice.id not in unit_invoices:
                    unit_invoices.append(a_invoice.id)
                lease.aggregation_id = False
                # set the invoice ids for the lease agreement
                for lease in self.web_progress_iter(leases, msg="Updating Units"):
                    if self.aggregate_lease_selected(lease):
                        if lease.id in initial_lease_ids:
                            if lease.invoice_ids:
                                initial_lease_invoices.extend(lease.invoice_ids.ids)
                            if lease_invoices:
                                initial_lease_invoices.extend(lease_invoices)
                            lease.invoice_ids = [(6, 0, initial_lease_invoices)]
                            # lease.last_invoice_to = self.determine_last_invoice_to(lease)
                            # unit_invoices.extend(initial_unit_invoices)
                            # lease_invoices.extend(initial_lease_invoices)
                            if lease.vehicle_id.lease_invoice_ids:
                                initial_unit_invoices.extend(lease.vehicle_id.lease_invoice_ids.ids)
                            if unit_invoices:
                                initial_unit_invoices.extend(unit_invoices)
                            for vehicle in lease.vehicle_id:
                                vehicle.with_context(skip_update=True).lease_invoice_ids = [
                                    (6, 0, initial_unit_invoices)]
                            initial_lease_ids.remove(lease.id)
                            # if lease.invoice_ids:
                            #    lease_invoices.extend(lease.invoice_ids.ids)
                            # if lease.vehicle_id.lease_invoice_ids:
                            #   unit_invoices.extend(lease.vehicle_id.lease_invoice_ids.ids)
                            # lease.invoice_ids = [(6, 0, lease_invoices)]
                            #

                            lease.run_initial_invoicing = False
                            lease.last_invoice_to = self.determine_last_invoice_to(lease)

                            # for vehicle in lease.vehicle_id:
                            #    vehicle.with_context(skip_update=True).lease_invoice_ids = [(6, 0, unit_invoices)]

                        else:
                            if lease.invoice_ids:
                                lease_invoices.extend(lease.invoice_ids.ids)

                            for llid in lease.vehicle_id.lease_invoice_ids:
                                if llid.id not in unit_invoices:
                                    unit_invoices.append(llid.id)
                            # if lease.vehicle_id.lease_invoice_ids:
                            #    if lease.vehicle_id.lease_invoice_ids.ids not in unit_invoices:
                            #        unit_invoices.extend(lease.vehicle_id.lease_invoice_ids.ids)
                            lease.invoice_ids = [(6, 0, lease_invoices)]
                            # lease.run_initial_invoicing = False
                            lease.last_invoice_to = self.determine_last_invoice_to(lease)

                            for vehicle in lease.vehicle_id:
                                vehicle.with_context(skip_update=True).lease_invoice_ids = [(6, 0, unit_invoices)]

        return new_invoices

    @api.model
    def record_aggregate_invoice(self, customers, the_wizard):
        new_invoices = []
        for customer in customers:
            accounting_invoice = self.env['account.move']
            po_numbers = []
            ap_groups = []
            aggregation_ids = []

            month = datetime.strptime(the_wizard.invoice_date, '%Y-%m-%d').strftime('%b')
            year = datetime.strptime(the_wizard.invoice_date, '%Y-%m-%d').strftime('%Y')
            inv_date = the_wizard.invoice_date

            for lease in self.web_progress_iter(customer.lease_agreements, msg="Processing Aggregate Customers"):
                lease.aggregation_id = 'False'  # cleanse any dirty agg ids
                if self.aggregate_lease_selected(lease):
                    if lease.po_number:
                        lease.aggregation_id = lease.po_number
                        po_numbers.append(lease.po_number)
                        aggregation_ids.append(lease.aggregation_id)
                    else:
                        if lease.ap_contact_ids:
                            ag_id = ''
                            for ap_id in lease.ap_contact_ids:
                                ag_id += str(ap_id.id)
                            lease.aggregation_id = ag_id
                            ap_groups.append(lease.ap_contact_ids)
                            aggregation_ids.append(ag_id)

                        else:
                            raise models.ValidationError(
                                'Lease agreement issue: Customer is marked for Aggregate '
                                'invoicing but lease agreement does not contain a PO or AP Contact '
                                'Agreement: ' + lease.lease_number + "Customer: " + lease.customer_id.name
                            )

            # make po_number list unique
            po_numbers = list(dict.fromkeys(po_numbers))
            aggregation_ids = list(dict.fromkeys(aggregation_ids))
            # find leases by PO
            for ags_id in self.web_progress_iter(aggregation_ids, msg="Locating Aggregate IDs"):
                line_ids = []
                next_month_line_ids = []
                lease_invoices = []
                initial_lease_ids = []
                initial_lease_invoices = []
                initial_unit_invoices = []
                unit_invoices = []
                l_resp = {}
                n_resp = {}
                leases = self.env['thomaslease.lease'].search(
                    [('aggregation_id', '=', ags_id), ('customer_id', '=', customer.id)])

                for lease in self.web_progress_iter(leases, msg="Generating Aggregate Invoice"):
                    if self.aggregate_lease_selected(lease):
                        print("==========aggregate lease agreement loop===================")
                        dt_inv_to = datetime.strptime(lease.invoice_to, '%Y-%m-%d')
                        end_of_month = calendar.monthrange(dt_inv_to.year, dt_inv_to.month)[1]

                        if lease.run_initial_invoicing:
                            last_to_date = datetime.strptime(lease.invoice_to, '%Y-%m-%d')
                            last_from_date = datetime.strptime(lease.invoice_from, '%Y-%m-%d')

                            prev_relative_month = last_to_date + relativedelta.relativedelta(months=-1)

                            prev_month_from = datetime.strptime(lease.billing_start_date, '%Y-%m-%d')
                            prev_month_days = calendar.monthrange(prev_relative_month.year, prev_relative_month.month)[
                                1]
                            prev_month_to = last_from_date + relativedelta.relativedelta(days=-1)
                            # datetime(prev_relative_month.year, prev_relative_month.month,prev_month_days)
                            prev_month = prev_month_from.strftime('%b')
                            prev_year = prev_month_from.strftime('%Y')

                        for line in lease.lease_lines:
                            product = line.product_id
                            invoice_line = self.env['account.move.line']
                            l_resp = self.calculate_line_amount(
                                product, line, line.price, lease.invoice_from, lease.invoice_to, lease)
                            line_amount = l_resp['amount']
                            start_date = datetime.strptime(lease.invoice_from, '%Y-%m-%d').date()
                            end_date = datetime.strptime(lease.invoice_to, '%Y-%m-%d').date()

                            num_days = (end_date - start_date).days + 1
                            quantity = 1
                            unit_str = ''
                            if lease.vehicle_id.unit_no:
                                unit_str = 'Unit # ' + str(lease.vehicle_id.unit_no)
                            else:
                                unit_str = str(product.name)

                            if num_days < end_of_month and not lease.rate_type == 'Bi-Weekly' \
                                    and not lease.rate_type == 'Monthly' and not lease.rate_type == 'Stelco Monthly':

                                description = self.create_daily_invoice_line_description(start_date, end_date,
                                                                                         lease)
                                quantity = num_days
                                line_amount = l_resp['rate']

                            elif lease.rate_type == 'Bi-Weekly':
                                if not lease.last_invoice_to:
                                    last_to_date = datetime.strptime(lease.billing_start_date, '%Y-%m-%d')
                                else:
                                    last_to_date = datetime.strptime(lease.last_invoice_to, '%Y-%m-%d')

                                # changing description model
                                last_to_date = datetime.strptime(lease.invoice_from, '%Y-%m-%d')
                                # end

                                start_date = last_to_date  # + relativedelta.relativedelta(days=+1)

                                if lease.lease_return_date:
                                    end_date = datetime.strptime(lease.lease_return_date, '%Y-%m-%d')
                                # else:
                                #    end_date = last_to_date + relativedelta.relativedelta(weeks=+4)

                                start_date_str = start_date.strftime('%b %d')
                                end_date_str = end_date.strftime('%b %d')
                                description = 'Bi Weekly Lease for ' + unit_str + ' - ' + \
                                              start_date_str + ' to ' + end_date_str + ', ' + year
                                line_amount = line.price
                                rel_days = relativedelta.relativedelta(end_date, start_date).days
                                rel_weeks = relativedelta.relativedelta(end_date, start_date).weeks
                                quantity = '{0:,.2f}'.format(
                                    (rel_days + 1) / 14)  # (rel_weeks + (rel_days - (rel_weeks * 7)) / 7) / 2

                            elif lease.rate_type == 'Daily' or lease.rate_type == 'Stelco Daily':
                                quantity = num_days
                                line_amount = l_resp['rate']  # line.price

                                description = self.create_daily_invoice_line_description(start_date, end_date, lease)
                                # start_date_str + ' - ' + end_date_str + ' ' + year + ' - Lease: for Unit # ' + the_lease.id.vehicle_id.unit_no

                            elif lease.rate_type == 'Weekly' or lease.rate_type == 'Stelco Weekly':
                                days = num_days % 7
                                weeks = math.floor(num_days / 7)
                                line_amount = l_resp["rate"]  # line.price / 7
                                quantity = (weeks * 7) + days
                                t_quantity = str(weeks) + " weeks " + str(days) + " days "
                                description = month + ' ' + year + ' - ' + t_quantity + 'Lease: for Unit # ' + lease.vehicle_id.unit_no
                            elif lease.rate_type == 'Monthly' or lease.rate_type == 'Stelco Monthly':
                                description = self.create_monthly_invoice_line_description(start_date, end_date, month,
                                                                                           year, lease)
                            else:
                                description = line.description

                            # create the invoice line
                            line_id = invoice_line.create({
                                'product_id': product.id,
                                'lease_line_id': line.id,
                                'vehicle_id': line.vehicle_id.id,
                                'price_unit': line_amount,
                                'quantity': quantity,
                                'name': description,
                                'invoice_line_tax_ids': [(6, 0, product.taxes_id.ids)],
                                'account_id': product.property_account_income_id.id
                            })

                            # call set taxes to set them...otherwise the relationships aren't set properly
                            # line_id._set_taxes()
                            line_id.price_unit = line_amount
                            line_ids.append(line_id.id)
                            if lease.invoice_ids:
                                lease_invoices.extend(lease.invoice_ids.ids)

                            for l_id in lease.vehicle_id.lease_invoice_ids:
                                if l_id.id not in unit_invoices:
                                    unit_invoices.append(l_id.id)
                            # if lease.vehicle_id.lease_invoice_ids:
                            #    if lease.vehicle_id.lease_invoice_ids.ids not in unit_invoices:
                            #        unit_invoices.extend(lease.vehicle_id.lease_invoice_ids.ids)

                        if lease.run_initial_invoicing:
                            for next_line in lease.lease_lines:
                                n_resp = self.calculate_line_amount(product, next_line, next_line.price,
                                                                    prev_month_from.strftime(
                                                                        '%Y-%m-%d'), prev_month_to.strftime('%Y-%m-%d'),
                                                                    lease)
                                next_line_amount = n_resp['amount']
                                num_days = (prev_month_to - prev_month_from).days + 1
                                date_delta = relativedelta.relativedelta(prev_month_from, prev_month_to)
                                num_months = date_delta.months
                                num_years = date_delta.years

                                pro_rated = prev_month + ' ' + prev_year
                                quantity = 1
                                if num_days < prev_month_days and not lease.rate_type == 'Bi-Weekly' \
                                        and not lease.rate_type == 'Monthly':
                                    description = self.create_daily_invoice_line_description(prev_month_from,
                                                                                             prev_month_to,
                                                                                             lease)
                                    quantity = num_days
                                    next_line_amount = n_resp['rate']

                                elif lease.rate_type == 'Bi-Weekly':  # need to determine what to do here
                                    if not lease.last_invoice_to:
                                        last_to_date = datetime.strptime(lease.billing_start_date, '%Y-%m-%d')
                                    else:
                                        last_to_date = datetime.strptime(lease.last_invoice_to, '%Y-%m-%d')

                                    start_date = last_to_date + relativedelta.relativedelta(days=+1)

                                    if lease.lease_return_date:
                                        end_date = datetime.strptime(lease.lease_return_date, '%Y-%m-%d')
                                    else:
                                        end_date = last_to_date + relativedelta.relativedelta(weeks=+4)

                                    start_date_str = start_date.strftime('%b %d')
                                    end_date_str = end_date.strftime('%b %d')
                                    description = 'Bi Weekly Lease for Unit # ' + lease.vehicle_id.unit_no + ' - ' + \
                                                  start_date_str + ' to ' + end_date_str + ', ' + year
                                    next_line_amount = next_line.price
                                    rel_days = relativedelta.relativedelta(end_date, start_date).days
                                    rel_weeks = relativedelta.relativedelta(end_date, start_date).weeks
                                    quantity = '{0:,.2f}'.format((rel_days + 1) / 14)
                                    # (rel_weeks + (rel_days - (rel_weeks * 7)) / 7) / 2
                                elif lease.rate_type == 'Daily' or lease.rate_type == 'stelco_daily':
                                    quantity = num_days
                                    next_line_amount = n_resp["rate"]  # next_line.price
                                    description = self.create_daily_invoice_line_description(prev_month_from,
                                                                                             prev_month_to, lease)
                                elif lease.rate_type == 'Weekly' or lease.rate_type == 'stelco_weekly':
                                    days = prev_month_days % 7
                                    weeks = math.floor(prev_month_days / 7)
                                    next_line_amount = n_resp["rate"]  # next_line.price / 7
                                    quantity = (weeks * 7) + days
                                    t_quantity = str(weeks) + " week " + str(days) + " days "
                                    description = month + ' ' + year + ' - ' + t_quantity + 'Lease: for Unit # ' + lease.vehicle_id.unit_no
                                elif lease.rate_type == 'Monthly' or lease.rate_type == 'stelco_monthly':
                                    # if "Dofasco" in lease.customer_id.name:
                                    #     description = self.create_dofasco_monthly_invoice_line_description(lease)
                                    # else:
                                    #     description = self.create_monthly_invoice_line_description(prev_month_from,
                                    #                                                                prev_month_to,
                                    #                                                                prev_month,
                                    #                                                                prev_year, lease)
                                    description = self.create_monthly_invoice_line_description(prev_month_from,
                                                                                               prev_month_to,
                                                                                               prev_month,
                                                                                               prev_year, lease)
                                else:
                                    description = next_line.description

                                next_month_line_id = invoice_line.create({
                                    'product_id': product.id,
                                    'lease_line_id': next_line.id,
                                    'vehicle_id': next_line.vehicle_id.id,
                                    'price_unit': next_line_amount,
                                    'quantity': quantity,
                                    'name': description,
                                    'invoice_line_tax_ids': [(6, 0, product.taxes_id.ids)],
                                    'account_id': product.property_account_income_id.id
                                })

                                # next_month_line_id._set_taxes()
                                next_month_line_id.price_unit = next_line_amount

                                next_month_line_ids.append(next_month_line_id.id)
                                if lease.invoice_ids:
                                    initial_lease_invoices.extend(lease.invoice_ids.ids)
                                if lease.vehicle_id.lease_invoice_ids:
                                    initial_unit_invoices.extend(lease.vehicle_id.lease_invoice_ids.ids)

                            if "Dofasco" in lease.customer_id.name:
                                inv_date = datetime(last_to_date.year, last_to_date.month, 1)
                            comment = ''
                            if len(leases) == 1 and len(lease.lease_lines) == 1:
                                comment = n_resp['formula']
                            initial_lease_ids.append(lease.id)
                            a_next_invoice = accounting_invoice.create({
                                'partner_id': lease.customer_id.id,
                                'vehicle_id': lease.vehicle_id.id,
                                'comment': comment,
                                'invoice_date': inv_date,  # lease.invoice_generation_date,
                                'invoice_date_due': lease.invoice_due_date,
                                'invoice_from': prev_month_from,
                                'invoice_to': prev_month_to,
                                'invoice_posting_date': lease.invoice_generation_date,
                                'invoice_generation_date': lease.invoice_generation_date,
                                'type': 'out_invoice',
                                'initial_invoice': True,
                                'state': 'draft',
                                'po_number': lease.po_number,
                                # 'partner_invoice_id': lease.partner_invoice_id.id,
                                'partner_shipping_id': lease.partner_shipping_id.id,
                                'requires_manual_calculations': lease.requires_manual_calculations,
                                'invoice_line_ids': [(6, 0, next_month_line_ids)]
                            })

                            # lease_invoices.append(a_next_invoice.id)
                            initial_lease_invoices.append(a_next_invoice.id)
                            new_invoices.append(a_next_invoice)
                            # unit_invoices.append(a_next_invoice.id)
                            initial_unit_invoices.append(a_next_invoice.id)
                            lease.aggregation_id = False
                # lease.run_initial_invoicing = False
                # TODO: move this out of the line for loop since I think it would create multiple invoice per lease line
                comment = ''
                if len(leases) == 1 and len(lease.lease_lines) == 1:
                    comment = l_resp['formula']
                a_invoice = accounting_invoice.create({
                    'partner_id': lease.customer_id.id,
                    'vehicle_id': lease.vehicle_id.id,
                    'comment': comment,
                    'invoice_date': the_wizard.invoice_date,  # lease.invoice_generation_date,
                    'invoice_date_due': lease.invoice_due_date,
                    'invoice_from': lease.invoice_from,
                    'invoice_to': lease.invoice_to,
                    'invoice_posting_date': lease.invoice_posting_date,
                    'invoice_generation_date': lease.invoice_generation_date,
                    'type': 'out_invoice',
                    'state': 'draft',
                    'po_number': lease.po_number,
                    # 'partner_invoice_id': lease.partner_invoice_id.id,
                    'partner_shipping_id': lease.partner_shipping_id.id,
                    'requires_manual_calculations': lease.requires_manual_calculations,
                    'invoice_line_ids': [(6, 0, line_ids)]
                })

                lease_invoices.append(a_invoice.id)
                new_invoices.append(a_invoice)
                if a_invoice.id not in unit_invoices:
                    unit_invoices.append(a_invoice.id)
                lease.aggregation_id = False
                # set the invoice ids for the lease agreement
                for lease in self.web_progress_iter(leases, msg="Updating Units"):
                    _logger.info("out loop...updating unit # " + str(lease.vehicle_id.unit_no))
                    if self.aggregate_lease_selected(lease):
                        if lease.id in initial_lease_ids:
                            _logger.info("Instide Initial Lease id aggregate U")
                            if lease.invoice_ids:
                                initial_lease_invoices.extend(lease.invoice_ids.ids)
                            if lease_invoices:
                                initial_lease_invoices.extend(lease_invoices)
                            lease.invoice_ids = [(6, 0, initial_lease_invoices)]
                            # lease.last_invoice_to = self.determine_last_invoice_to(lease)
                            # unit_invoices.extend(initial_unit_invoices)
                            # lease_invoices.extend(initial_lease_invoices)
                            if lease.vehicle_id.lease_invoice_ids:
                                initial_unit_invoices.extend(lease.vehicle_id.lease_invoice_ids.ids)
                            if unit_invoices:
                                initial_unit_invoices.extend(unit_invoices)
                            for vehicle in lease.vehicle_id:
                                vehicle.with_context(skip_update=True,tracking_disable=True).lease_invoice_ids = [
                                    (6, 0, initial_unit_invoices)]
                            initial_lease_ids.remove(lease.id)
                            # if lease.invoice_ids:
                            #    lease_invoices.extend(lease.invoice_ids.ids)
                            # if lease.vehicle_id.lease_invoice_ids:
                            #   unit_invoices.extend(lease.vehicle_id.lease_invoice_ids.ids)
                            # lease.invoice_ids = [(6, 0, lease_invoices)]
                            #

                            lease.run_initial_invoicing = False
                            lease.last_invoice_to = self.determine_last_invoice_to(lease)

                            # for vehicle in lease.vehicle_id:
                            #    vehicle.with_context(skip_update=True).lease_invoice_ids = [(6, 0, unit_invoices)]
                        else:
                            for l_inv in new_invoices:
                                _logger.info(
                                    "Start updating lease invoice ids for unit# " + str(lease.vehicle_id.unit_no))
                                if lease.customer_id == l_inv.partner_id and lease.po_number == l_inv.po_number:
                                    lease.invoice_ids = [(4, l_inv.id)]
                                    _logger.info("end update lease")
                                    _logger.info("Start unit Update with Context")
                                    lease.vehicle_id.with_context(skip_update=True,tracking_disable=True).lease_invoice_ids = [(4, l_inv.id)]
                                    _logger.info("End unit Update with Context")
                            # if lease.invoice_ids:
                            #    lease_invoices.extend(lease.invoice_ids.ids)

                            # for llid in lease.vehicle_id.lease_invoice_ids:
                            #    if llid.id not in unit_invoices:
                            #        unit_invoices.append(llid.id)
                            # if lease.vehicle_id.lease_invoice_ids:
                            #    if lease.vehicle_id.lease_invoice_ids.ids not in unit_invoices:
                            #        unit_invoices.extend(lease.vehicle_id.lease_invoice_ids.ids)
                            # lease.invoice_ids = [(6, 0, lease_invoices)]
                            # lease.run_initial_invoicing = False
                            lease.last_invoice_to = self.determine_last_invoice_to(lease)

                            # for vehicle in lease.vehicle_id:
                            #    for inv in new_invoices:
                            #        vehicle.with_context(skip_update=True).lease_invoice_ids = [(4, inv.id)]

        return new_invoices

    def invoice_exists(self, lease):
        in_range = False
        if lease.last_invoice_date:
            last_invoice_dt = datetime.strptime(lease.last_invoice_date, '%Y-%m-%d')
            invoice_to = datetime.strptime(lease.invoice_to, '%Y-%m-%d')
            invoice_from = datetime.strptime(lease.invoice_from, '%Y-%m-%d')

            if invoice_from <= last_invoice_dt <= invoice_to:
                for inv in lease.invoice_ids:
                    if inv.type == 'out_invoice':
                        if inv.invoice_to and inv.invoice_from:
                            i_inv_to = datetime.strptime(inv.invoice_to, '%Y-%m-%d')
                            i_inv_from = datetime.strptime(inv.invoice_from, '%Y-%m-%d')
                            if i_inv_to == invoice_to and i_inv_from == invoice_from:
                                in_range = True
                        else:
                            raise models.ValidationError('Invoice: ' + str(inv.display_name) + ' for Rental Agreement ' + str(
                                lease.lease_number) + ' is missing Invoice From and To dates')
            # if last_invoice_dt <= invoice_to and last_invoice_dt >= invoice_from:
            #    in_range = True

        return in_range

    @api.model
    def ok_pressed(self):
        print("IN OK FUNCTION")

    @api.model
    def record_lease_invoices2(self):
        aggregate_customers = []
        lease_with_existing_invoice = []
        lease_success = []
        norm_invoices = []
        agg_invoices = []
        str_lease_closed = ''

        for wizard in self:
            # leases = wizard.lease_ids
            for a_lease in self.lease_records:
                # determine if an invoice already exists for the lease and don't create again...warn user
                # a_lease = self.env['thomaslease.lease'].browse(lease)
                print("Processing Lease:" + a_lease.lease_number)
                if self.invoice_exists(a_lease):
                    lease_with_existing_invoice.append(a_lease)
                else:
                    if a_lease.customer_id.aggregate_invoicing:
                        print("Processing Aggregate Customer:" + str(a_lease.customer_id.name))
                        aggregate_customers.append(a_lease.customer_id)
                        lease_success.append(a_lease)
                    else:
                        norm_invoices = self.record_normal_invoice2(a_lease)
                        lease_success.append(a_lease)

                    a_lease.with_context(tracking_disable=True).write({'last_invoice_date': wizard.invoice_date})
                    if a_lease.state == 'invoice_pending':
                        a_lease.state = 'closed'
                        str_lease_closed += '<p> Lease: ' + a_lease.id.lease_number + 'state changed from Invoice Pending to Closed</p>'
                        a_lease.message_post(
                            body='<p><b>Lease state changed from Invoice Pending to Closed</b></p>',
                            subject="Lease State Changed")#, subtype="mt_note")

            aggregate_customers = list(dict.fromkeys(aggregate_customers))
            agg_invoices = self.record_aggregate_invoice(aggregate_customers, wizard)
            agg_invoices.extend(norm_invoices)

        strSuccess = ""

        str_i_date = datetime.strptime(self.invoice_date, '%Y-%m-%d').strftime('%m/%d/%Y')

        for l in lease_success:
            strPost = ""
            strSuccess += '<p>' + l.lease_number + '<\p>'
            for a in agg_invoices:
                if l in a.lease_ids:
                    a_f_date = datetime.strptime(a.invoice_from, '%Y-%m-%d').strftime('%m/%d/%Y')
                    a_t_date = datetime.strptime(a.invoice_to, '%Y-%m-%d').strftime('%m/%d/%Y')
                    a_i_date = datetime.strptime(a.invoice_date, '%Y-%m-%d').strftime('%m/%d/%Y')
                    strSuccess += '<p>Invoice id: ' + str(
                        a.id) + ' Invoice Date: ' + a_i_date + ' From: ' + a_f_date + ' to: ' + a_t_date + '<\p>'
                    strPost = '<p>Invoice id: ' + str(
                        a.id) + ' Invoice Date: ' + a_i_date + ' From: ' + a_f_date + ' to: ' + a_t_date + '<\p>'
                    l.message_post(
                        body='<p><b>Invoice(s) have been successfully created for: ' + a_i_date + '</b></p>' + strPost,
                        subject="Invoice Creation")#, subtype="mt_note")

            strSuccess += "<hr/>"

        strExisting = ""
        for l in lease_with_existing_invoice:
            str_l_i_date = datetime.strptime(l.last_invoice_date, '%Y-%m-%d').strftime('%m/%d/%Y')
            str_f_date = datetime.strptime(l.invoice_from, '%Y-%m-%d').strftime('%m/%d/%Y')
            str_t_date = datetime.strptime(l.invoice_to, '%Y-%m-%d').strftime('%m/%d/%Y')
            strExisting += '<p>' + l.lease_number + ' Target Invoice Date: ' + str_i_date + ' - Last Invoice Date: ' + str_l_i_date + ' for range from ' + str_f_date + ' to ' + str_t_date + '<\p>'

        if strSuccess == '':
            strMess = ''
        else:
            strMess = '<h2>Invoice(s) have been successfully created: </h2>' + strSuccess

        if not strExisting == '':
            strMess += '<h2>WARNING - INVOICES NOT CREATED</h2> <h3>Invoices with the same or crossing' \
                       ' date ranges already exist for the following lease agreements:</h3><br/>' + strExisting

        if not str_lease_closed == '':
            strMess += '<h2>The following Lease Agreements state have changed</h2><br/>' + str_lease_closed

        rec = self.env['thomaslease.message'].create({'message': strMess})

        # rec = theMess.
        # rec2 = rec.with_context(ok_handler=self.ok_pressed)
        res = self.env['ir.actions.act_window'].for_xml_id('thomasfleet', 'message_action')
        res.update(
            context=dict(self.env.context, ok_handler='ok_pressed', caller_model=self._name, caller_id=self.id),
            res_id=rec.id
        )
        return res

    @api.model
    def record_lease_invoices(self):
        aggregate_customers = []
        lease_with_existing_invoice = []
        lease_success = []
        norm_invoices = []
        agg_invoices = []
        str_lease_closed = ''

        for wizard in self:
            leases = self.env['thomaslease.lease'].browse(wizard.lease_ids)
            for a_lease in self.web_progress_iter(leases, msg="Creating Invoices"):
                # determine if an invoice already exists for the lease and don't create again...warn user
                # a_lease = self.env['thomaslease.lease'].browse(lease)
                print("Processing Lease:" + a_lease.id.lease_number)
                if self.invoice_exists(a_lease.id):
                    lease_with_existing_invoice.append(a_lease.id)
                else:
                    if a_lease.id.customer_id.aggregate_invoicing:
                        print("Processing Aggregate Customer:" + str(a_lease.id.customer_id.name))
                        aggregate_customers.append(a_lease.id.customer_id)
                        lease_success.append(a_lease.id)
                    else:
                        norm_invoices = self.record_normal_invoice2(a_lease)
                        lease_success.append(a_lease.id)

                    a_lease.id.last_invoice_date = wizard.invoice_date
                    if a_lease.id.state == 'invoice_pending':
                        a_lease.id.state = 'closed'
                        str_lease_closed += '<p> Lease: ' + a_lease.id.lease_number + 'state changed from Invoice Pending to Closed</p>'
                        a_lease.id.message_post(
                            body='<p><b>Lease state changed from Invoice Pending to Closed</b></p>',
                            subject="Lease State Changed")#, subtype="mt_note")

            aggregate_customers = list(dict.fromkeys(aggregate_customers))
            agg_invoices = self.record_aggregate_invoice(aggregate_customers, wizard)
            #todo look into this..norm invoice seems off..
            agg_invoices.extend(norm_invoices)

        strSuccess = ""

        str_i_date = datetime.strptime(self.invoice_date, '%Y-%m-%d').strftime('%m/%d/%Y')
        count_leases = 1
        count_invoices =1
        for l in lease_success:
            strPost = ""
            strSuccess += '<p>' + l.lease_number + '<\p>'
            _logger.info("Posting message for Invoice creation " + str(count_leases))
            count_leases = count_leases + 1
            for a in agg_invoices:
                _logger.info("Processing message for Invoice creation " + str(count_invoices))
                count_invoices = count_invoices + 1
                if l in a.lease_ids:

                    a_f_date = datetime.strptime(a.invoice_from, '%Y-%m-%d').strftime('%m/%d/%Y')
                    a_t_date = datetime.strptime(a.invoice_to, '%Y-%m-%d').strftime('%m/%d/%Y')
                    a_i_date = datetime.strptime(a.invoice_date, '%Y-%m-%d').strftime('%m/%d/%Y')
                    strSuccess += '<p>Invoice id: ' + str(
                        a.id) + ' Invoice Date: ' + a_i_date + ' From: ' + a_f_date + ' to: ' + a_t_date + '<\p>'
                    strPost = '<p>Invoice id: ' + str(
                        a.id) + ' Invoice Date: ' + a_i_date + ' From: ' + a_f_date + ' to: ' + a_t_date + '<\p>'

                    l.message_post(
                        body='<p><b>Invoice(s) have been successfully created for: ' + a_i_date + '</b></p>' + strPost,
                        subject="Invoice Creation")#, subtype="mt_note")
                    _logger.info("Posted message for Invoice creation " + str(count_invoices))

            strSuccess += "<hr/>"

        strExisting = ""
        for l in lease_with_existing_invoice:
            str_l_i_date = datetime.strptime(l.last_invoice_date, '%Y-%m-%d').strftime('%m/%d/%Y')
            str_f_date = datetime.strptime(l.invoice_from, '%Y-%m-%d').strftime('%m/%d/%Y')
            str_t_date = datetime.strptime(l.invoice_to, '%Y-%m-%d').strftime('%m/%d/%Y')
            strExisting += '<p>' + l.lease_number + ' Target Invoice Date: ' + str_i_date + ' - Last Invoice Date: ' + str_l_i_date + ' for range from ' + str_f_date + ' to ' + str_t_date + '<\p>'

        if strSuccess == '':
            strMess = ''
        else:
            strMess = '<h2>Invoice(s) have been successfully created: </h2>' + strSuccess

        if not strExisting == '':
            strMess += '<h2>WARNING - INVOICES NOT CREATED</h2> <h3>Invoices with the same or crossing' \
                       ' date ranges already exist for the following lease agreements:</h3><br/>' + strExisting

        if not str_lease_closed == '':
            strMess += '<h2>The following Lease Agreements state have changed</h2><br/>' + str_lease_closed

        rec = self.env['thomaslease.message'].create({'message': strMess})

        # rec = theMess.
        # rec2 = rec.with_context(ok_handler=self.ok_pressed)
        res = self.env['ir.actions.act_window'].for_xml_id('thomasfleet', 'message_action')
        res.update(
            context=dict(self.env.context, ok_handler='ok_pressed', caller_model=self._name, caller_id=self.id),
            res_id=rec.id
        )
        return res


