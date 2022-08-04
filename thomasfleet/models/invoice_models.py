# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import requests, json, uuid
from urllib import parse

class ThomasAccountingInvoice(models.Model):
    _inherit = 'account.move'

    qc_check = fields.Boolean(string='Data Accuracy Validation')
    sent_to_ar = fields.Boolean(string="Sent to AR" , default=False)
    thomas_invoice_type = fields.Selection( [('lease','Lease'),('maintenance', 'Maintenance'),('general', 'General')],
                                            string="Thomas Invoice Type", default='lease')
    thomas_invoice_class = fields.Selection([('rental','Rental'),('repair', 'Repair'),('407', '407'), ('fines', 'Fines')],
                                            string="Invoice Type", default='rental')

    vehicle_id = fields.Many2one("fleet.vehicle", string="Unit #")

    # unit_no = fields.Char(related='vehicle_id.unit_no', string="Unit #")
    lease_ids = fields.Many2many('thomaslease.lease',string='Lease Agreements',
                                  relation='lease_agreement_account_invoice_rel')
    vehicle_ids = fields.Many2many('fleet.vehicle',string='Units',
                                  relation='unit_lease_account_invoice_rel')

    units_display = fields.Text(string='Unit #s', compute='_compute_units_display')
    po_number = fields.Char(string='Purchase Order #')
    gp_po_number = fields.Char(string='GP Purchase Order #', compute='_compute_gp_po')
    requires_manual_calculations = fields.Char(string="Needs Manual Calculation")
    invoice_from = fields.Date(string="Invoice From")
    invoice_to = fields.Date(string="Invoice To")
    invoice_posting_date = fields.Date(string="Invoice Posting Date")
    invoice_generation_date = fields.Date(string="Invoice Generation Date")
    partner_shipping_id = fields.Many2one(
        'res.partner',
        string='Shipping Address',
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="Delivery address for current invoice.")
    customer_name = fields.Char("Customer", related="partner_id.compound_name")
    initial_invoice = fields.Boolean("Initial Invoice", default=False)
    invoice_line_ids = fields.One2many('account.move.line', 'invoice_id', string='Invoice Lines',
                                       oldname='invoice_line',
                                       readonly=True, states={'draft': [('readonly', False)]}, copy=True)

    @api.onchange('partner_id', 'company_id')
    def _onchange_delivery_address(self):
        addr = self.partner_id.address_get(['delivery'])
        self.partner_shipping_id = addr and addr.get('delivery')


    @api.onchange('thomas_invoice_type')
    def _onchange_thomas_invoice_type(self):
        for rec in self:
            print("Thomas Invoice Type " + str(rec.thomas_invoice_type))

    def _compute_gp_po(self):
        for rec in self:
            if rec.po_number:
                s = ''.join([i if ord(i) < 128 else '' for i in str.upper(rec.po_number)[0:20]])
                rec.gp_po_number = s

    def _compute_units_display(self):
        for rec in self:
            units = ''
            counter = 0
            for veh in rec.vehicle_ids:
                if units == '':
                    units = str(veh.unit_no)
                elif counter % 5 == 0:
                    units = units + "," + (str('\n')) + str(veh.unit_no)
                else:
                    units = units + "," + str(veh.unit_no)
                counter += 1
            rec.units_display = units



    @api.model
    def get_delivery_partner_id(self):
        self.ensure_one()
        return self.partner_shipping_id.id or super(ThomasAccountingInvoice, self).get_delivery_partner_id()

    @api.model
    def _get_ar_contact(self):
        self.ensure_one()
        res = []
        ar = self.env['res.partner'].search([('name', '=', 'Accounts Receivable')])
        res.append(ar.id)
        return res
    @api.model
    def _get_mail_contacts(self):

        self.ensure_one()
        contact_ids=[]
        for lease in self.lease_ids:
            contact_ids.extend(lease.ap_contact_ids.ids)
        return contact_ids

    @api.model
    def action_invoice_cancel(self):
        self.ensure_one()
        self.move_name=False
        #leases = self.env['thomaslease.lease'].search([('id', 'in', self.lease_ids.ids)], limit=1)
        res =super(ThomasAccountingInvoice, self).action_invoice_cancel()
        for lease in self.lease_ids:
            invoice = self.env['account.move'].search([('id', 'in', lease.invoice_ids.ids),('state', '!=','cancel')], limit=1,order='invoice_date desc')
            lease.last_invoice_date = False
            lease.last_invoice_date = invoice.invoice_date
            lease.message_post(
                body='<p><b>Invoice Canceled</b></p><p>Invoice dated: ' + str(self.invoice_posting_date) +
                     ' for: $' + str(self.amount_total_signed) + ' for this lease was canceled</p>',
                subject="Invoice Canceled", subtype="mt_note")

        return res

    @api.model
    def unlink(self):
        for invoice in self:
            if invoice.state not in ('draft', 'cancel', 'paid'):
                raise models.UserError(_(
                    'You cannot delete an invoice which is not draft or cancelled. You should create a credit note instead.'))
            elif invoice.move_name:
                raise models.UserError(_(
                    'You cannot delete an invoice after it has been validated (and received a number). You can set it back to "Draft" state and modify its content, then re-confirm it.'))

            for lease in invoice.lease_ids:
                the_invoice = self.env['account.move'].search([('id', 'in', lease.invoice_ids.ids),('state', '!=','cancel'), ('id', '!=', invoice.id)], limit=1,order='invoice_date desc')

                if the_invoice:
                    lease.last_invoice_date = invoice.invoice_date
                else:
                    lease.last_invoice_date = False

                lease.message_post(
                    body='<p><b>Invoice Deleted:</b></p><p>Invoice dated: ' + str(invoice.invoice_posting_date) +
                         ' for: $' + str(invoice.amount_total_signed) + ' for this lease was deleted</p>',
                    subject="Invoice Deleted", subtype="mt_note")

        return super(ThomasAccountingInvoice, self).unlink()

    @api.model
    def action_invoice_send_to_ar(self):
        self.ensure_one()
        ar = self._get_ar_contact()
        template = self.env.ref('account.email_template_edi_invoice', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='account.move',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            mark_invoice_as_sent=True,
            custom_layout="account.mail_template_data_notification_email_account_invoice",
            force_email=False,
            default_partner_ids=ar,
            message_type='email',
            partner_ids=ar,
            company=ar

        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }








    @api.model
    def action_invoice_sent(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        self.ensure_one()
        res = super(ThomasAccountingInvoice,self).action_invoice_sent()
        ctx = res['context']
        res.update(context=dict(ctx,default_partner_ids=self._get_mail_contacts()))
        return res

        '''
        template = self.env.ref('account.email_template_edi_invoice', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='account.move',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            default_partner_ids=self._get_mail_contacts(),
            mark_invoice_as_sent=True,
            custom_layout="account.mail_template_data_notification_email_account_invoice",
            force_email=True
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }
   
     '''

class ThomasAccountInvoiceLine(models.Model):
    _inherit = "account.move.line"
    _order = 'vehicle_id'

    lease_line_id = fields.Many2one('thomaslease.lease_line',string="Lease Line")
    # unit_no = fields.Char(string="Unit #",related="lease_line_id.vehicle_id.unit_no")
    #thomas_invoice_type = fields.Char(string="Invoice Type", related="invoice_id.")
    reference = fields.Char(string="Reference", compute="_compute_reference", inverse="_set_reference", store=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string="Unit #")#, domain="[('id', 'in', invoice_id.vehicle_ids.ids)]")
    invoice_id = fields.Many2one('account.move', 'invoice_line_ids')
    invoice_date = fields.Date(string="Invoice Date", related='invoice_id.invoice_date' ,store=True)
    thomas_invoice_type = fields.Char(string="Thomas Invoice Type", default="lease")

                                            #related="invoice_id.thomas_invoice_type")

    @api.depends("vehicle_id")
    def _compute_reference(self):
        for rec in self:
            if not rec.reference:
                rec.reference = rec.vehicle_id.unit_no if rec.vehicle_id else "MISC"

    def _set_reference(self):
        for rec in self:
            if rec.reference:
                continue
            else:
                rec.reference = rec.vehicle_id.unit_no if rec.vehicle_id else "MISC"





