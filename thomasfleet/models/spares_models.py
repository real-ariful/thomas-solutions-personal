from odoo import models, fields, api


class ThomasSwapRecord(models.Model):

    _name = 'thomaslease.swap'
    _description = 'Unit Swap for Thomas Leasing Operations'

    #invoice_ids = fields.One2many('account.move', 'message_id', string='Invoices')
    #lease_ids = fields.One2many('thomaslease.lease', string='Lease Agreements')
    swap_date = fields.Date('Swap Date')
    swap_return_date = fields.Date('Swap Return Date')
    vehicle_id = fields.Many2one("fleet.vehicle", string="Unit #")
    spare_vehicle_id = fields.Many2one("fleet.vehicle", string="Swap Unit #")
    vehicle_swap_out_odometer_id = fields.Many2one('fleet.vehicle.odometer', string="Unit Odometer at Swap",
                                            domain="[('vehicle_id','=',vehicle_id), ('activity','=','spare_swap')]")
    vehicle_swap_back_odometer_id = fields.Many2one('fleet.vehicle.odometer', string="Odometer at Return",
                                               domain="[('vehicle_id','=',vehicle_id), ('activity','=','spare_swap_back')]")


    mileage_at_lease = fields.Float(string='Lease Start Odometer', related='lease_out_odometer_id.value', readonly=True)

    mileage_at_return = fields.Float(string='Lease Return Odometer', related='lease_return_odometer_id.value',
                                     readonly=True)

class ThomasFleetSwapWizard(models.TransientModel):
    _name = 'thomaslease.lease.swap.wizard'

    def _default_lease_id(self):
        # for the_id in self.env.context.get('active_ids'):
        #    print(the_id.name)
        return self.env.context.get('active_id')

    lease_id = fields.Many2one('thomaslease.lease', string="Lease", default=_default_lease_id)
    vehicle_id = fields.Many2one(related="lease_id.vehicle_id", string= "Unit #")
    spare_vehicle_id = fields.Many2one("fleet.vehicle", string="Spare Unit #")
    vehicle_odometer_id = fields.Many2one('fleet.vehicle.odometer', string="Unit Odometer at Swap",
                                                   domain="[('vehicle_id','=',vehicle_id), ('activity','=','spare_swap')]")
    spare_odometer_id = fields.Many2one('fleet.vehicle.odometer', string="Odometer at Return",
                                                    domain="[('vehicle_id','=',vehicle_id), ('activity','=','spare_swap')]")


    @api.model
    def record_swap(self):
        self.ensure_one()

        #create swap record
        # set date of swap
        # copy data from wizard


class ThomasFleetSwapReturnWizard(models.TransientModel):
    _name = 'thomaslease.lease.swap.return.wizard'

    def _default_lease_id(self):
        # for the_id in self.env.context.get('active_ids'):
        #    print(the_id.name)
        return self.env.context.get('active_id')

    lease_id = fields.Many2one('thomaslease.lease', string="Lease", default=_default_lease_id)

    @api.model
    def record_swap_return(self):
       self.ensure_one()