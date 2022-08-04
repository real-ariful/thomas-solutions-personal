# -*- coding: utf-8 -*-

from odoo import models, fields, api
import requests, json, uuid
from urllib import parse
from odoo.osv import expression


class ThomasContact(models.Model):
    _inherit = 'res.partner'

    # user_id = fields.Many2one('res.users', string='Thomas Contact',
    #                           help='The internal user that is in charge of communicating with this contact if any.',tracking=True)
    qc_check = fields.Boolean(string='Data Accuracy Validation',tracking=True)
    lease_agreements = fields.One2many('thomaslease.lease', 'customer_id', 'Lease Contracts',tracking=True)
    documents = fields.One2many('thomasfleet.customer_document', 'customer_id', 'Customer Docucments',tracking=True)
    department = fields.Many2one('thomasfleet.customer_department','Department',tracking=True)
    protractor_guid = fields.Char(string='Protractor GUID', readonly=True,tracking=True) #,compute='_compute_protractor_guid')
    protractor_search_name = fields.Char(string="Search Name", compute='_compute_protractor_search_name',tracking=True)
    ap_contact = fields.Boolean(string="Accounts Payable Contact",tracking=True)
    po_contact = fields.Boolean(string="Purchasing Contact",tracking=True)
    ops_contact = fields.Boolean(string="Operations Contact",tracking=True)
    work_orders = fields.One2many('thomasfleet.workorder', 'customer_id', 'Work Orders')
    aggregate_invoicing= fields.Boolean(string="Aggregate Invoices", default=True,tracking=True)
    preferred_invoice_delivery = fields.Selection([('email','email'),('mail','mail')],
                                                  string='Invoice Delivery',default='email',tracking=True)
    preferred_payment = fields.Selection([('cheque', 'Cheque'),
                                          ('credit card', 'Credit Card'),
                                          ('eft', 'EFT'),
                                          ('pad2', 'PAD no Invoice Sent'),
                                          ('pad1', 'PAD with Invoice Sent'),
                                          ('other', 'Other')],
                                         string='Preferred Payment Method',tracking=True
                                         )

    discount_rate_calc = fields.Boolean("Discount Rate", tracking=True, default=True)

    other_payment = fields.Char(string='Other Payment', tracking=True)

    lease_agreement_ap_ids = fields.Many2many(
        'thomaslease.lease',
        string='Lease Agreements',
        relation='lease_agreement_res_partner_ap_rel'  # optional
        , tracking=True)
    lease_agreement_po_ids = fields.Many2many(
        'thomaslease.lease',
        string='Lease Agreements',
        relation='lease_agreement_res_partner_po_rel'  # optional
        , tracking=True
    )
    lease_agreement_ops_ids = fields.Many2many(
        'thomaslease.lease',
        string='Lease Agreements',
        relation='lease_agreement_res_partner_ops_rel'  # optional
        ,tracking=True
    )
    insurance_on_file = fields.Boolean(string="Proof of Insurance on File",tracking=True)
    insurance_agent = fields.Char(string="Agent",tracking=True)
    insurance_underwriter = fields.Char(string="Underwriter",tracking=True)
    insurance_policy = fields.Char(string="Policy #",tracking=True)
    insurance_expiration = fields.Date(string="Expiration Date",tracking=True)
    drivers_license = fields.Char(string="Drivers License",tracking=True)
    drivers_license_expiry = fields.Date(string="Drivers License Expiry",tracking=True)
    gp_customer_id = fields.Char(string="GP Customer ID",tracking=True)
    internal_division = fields.Char(string="Internal Division")
    compound_name = fields.Char(string="Compound Name", compute="_compute_compound_name")
    #name = fields.Char(string="Name",index=True)


    @api.depends('name','internal_division')
    def _compute_compound_name(self):
        for rec in self:
            name = rec.name
            if rec.internal_division:
                rec.compound_name = '%s - %s' % (name, rec.internal_division)
            else:
                rec.compound_name = name


    @api.model
    def name_get(self):
        if self._context.get('show_internal_division'):
            res = []
            for rec in self:
                name = rec.name
                if rec.internal_division:
                    name = '%s - %s' % (name, rec.internal_division)
                res.append((rec.id, name))
            return res
        return super(ThomasContact, self).name_get()

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if self._context.get('show_internal_division'):
            if operator in ('ilike', 'like', '=', '=like', '=ilike'):
                domain = expression.AND([
                    args or [],
                    ['|','|', ('name', operator, name), ('internal_division', operator, name),('display_name', operator, name)]
                ])
                return self.search(domain, limit=limit).name_get()
        return super(ThomasContact, self).name_search(name, args, operator, limit)


    @api.model
    def find_protractor_guid(self):

        default_company_id = self.env['res.company']._company_default_get().id
        for record in self:

            #print("Getting Protarctor ID for Customer: "+ str(parse.quote(str(record.name_get()))))
            the_resp = "NO GUID"
            if record.id != default_company_id:# and not record.protractor_guid:
                if record.protractor_search_name:
                    print("IN GET PROTRACTOR ID for" + str(record.protractor_search_name))
                    url = "https://integration.protractor.com/IntegrationServices/1.0/Contact/Search/" + str(record.protractor_search_name)
                    headers = {
                        'connectionId': "8c3d682f873644deb31284b9f764e38f",
                        'apiKey': "fb3c8305df2a4bd796add61e646f461c",
                        'authentication': "S2LZy0munq81s/uiCSGfCvGJZEo=",
                        'Accept': "application/json"
                    }
                    response = requests.request("GET", url, headers=headers)
                    print(str(url))
                    if response.ok:
                        #print(response.text)
                        data = response.json()
                        the_id = False
                        for item in data['ItemCollection']:
                            the_id = item['ID']

                        if not the_id:
                            the_id = uuid.uuid4()
                            the_resp = the_id
                            print("Setting Write to protractor cause no id found")
                        else:
                            print("Found an existing unit: " + the_id)
                            the_resp = the_id
                            # this can only be set on create
                    else:
                        the_resp = "Can't locate: " + self.name
            else:
                the_resp = record.protractor_guid
            record.protractor_guid = the_resp


    def _compute_protractor_search_name(self):
        for rec in self:
            if rec.name:
                theString = rec.name.replace('.', '')
                if theString.find('&'):
                    theSArr = theString.split('&',1)
                    theString = theSArr[0];
                print("The String===>" + theString)
                rec.protractor_search_name = theString.rstrip()

class ThomasCustomerDocument(models.Model):
    _name = 'thomasfleet.customer_document'

    customer_id = fields.Many2one("res.partner", "Customer")
    name=fields.Char("Name")
    description = fields.Char("Description")
    type = fields.Selection([('insurance', 'Proof of Insurance'), ('certification', 'Certification')])
    expiration = fields.Date('Expiration Date')
    document = fields.Binary("Document")

class ThomaseDepartment(models.Model):
    _name = 'thomasfleet.customer_department'

    name = fields.Char("Name")
    description = fields.Char("Description")
