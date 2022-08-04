from odoo import models, fields, api


class ThomasMessage(models.TransientModel):

    _name = 'thomaslease.message'
    _description = 'General Messages for Thomas Leasing Operations'

    title = fields.Char('Title')
    message = fields.Html(readonly=True)
    ok_handler = False
    #invoice_ids = fields.One2many('account.move', 'message_id', string='Invoices')
    #lease_ids = fields.One2many('thomaslease.lease', string='Lease Agreements')

    def ok_pressed(self):
        print("OK Pressed")
        for rec in self:
            mod = rec.env[rec.env.context['caller_model']].browse(rec.env.context['caller_id'])
            handle = rec.env.context['ok_handler']
            if handle:
                res = getattr(mod, handle)
                res()
            else:
                res = self.env[self.env.context['active_model']].browse(self.env.context['active_id'])
                if res:
                    res.ok_pressed()


    def cancel_pressed(self):
        return
