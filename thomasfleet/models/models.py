# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions
import logging, pprint, requests, json, uuid
from datetime import date, datetime
from dateutil import parser

_unit_inv = []

def dump_obj(obj):
    fields_dict = {}
    for key in obj.fields_get():
        fields_dict[key] = obj[key]
    return fields_dict


#Some fields don't have the exact same name
MODEL_FIELDS_TO_VEHICLE = {
    'transmission': 'transmission', 'model_year': 'model_year', 'electric_assistance': 'electric_assistance',
    'color': 'color', 'seats': 'seats', 'doors': 'doors', 'trailer_hook': 'trailer_hook',
    'default_co2': 'co2', 'co2_standard': 'co2_standard', 'default_fuel_type': 'fuel_type',
    'power': 'power', 'horsepower': 'horsepower', 'horsepower_tax': 'horsepower_tax',
}


class ThomasAsset(models.Model):
    _name = 'thomas.asset'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Thomas Asset'

    unit_no = fields.Char('Unit #', tracking=True)
    notes = fields.Text('Notes', tracking=True)
    charge_code = fields.Char('Charge Code', tracking=True)
    filed_as = fields.Char("File As", tracking=True)
    company_acct = fields.Char("Company Acct", tracking=True)
    asset_class = fields.Many2one('thomasfleet.asset_class', 'Asset Class', tracking=True)
    insurance_class = fields.Many2one('thomasfleet.insurance_class', 'Insurance Class', tracking=True)
    thomas_purchase_price = fields.Float('Thomas Purchase Price', tracking=True)
    purchase_date = fields.Char('Purchase Date', tracking=True)
    usage = fields.Char('Usage', tracking=True)
    disposal_year = fields.Char('Disposal Year', tracking=True)
    disposal_date = fields.Char('Disposal Date', tracking=True)
    disposal_proceeds = fields.Float('Disposal Proceeds', tracking=True)
    sold_to = fields.Char('Sold To', tracking=True)
    betterment_cost = fields.Char("Betterment Cost", tracking=True)
    lease_status = fields.Many2one('thomasfleet.lease_status', 'Rental Agreement Status', tracking=True)
   # lease_status = fields.Selection([('spare','Spare'), ('maint_req','Maintenance Required'),('road_test','Road Test'),('detail','Detail'),('reserved','Customer/Reserved'),('leased', 'Leased'), ('available','Available for Lease'),('returned_inspect','Returned waiting Inspection')], 'Lease Status')
    photoSets = fields.One2many('thomasfleet.asset_photo_set', 'vehicle_id', 'Photo Set', tracking=True)
    inclusions = fields.Many2many('thomasfleet.inclusions', string='Inclusions', tracking=True)
    state = fields.Selection(
        [('spare', 'Spare'), ('maint_req', 'Maintenance Required'), ('road_test', 'Road Test'), ('detail', 'Detail'),
         ('reserved', 'Customer/Reserved'), ('leased', 'Rented'), ('available', 'Available for Rent'),
         ('returned_inspect', 'Returned waiting Inspection')], string="Status", default='available')


class ThomasAssetPhotoSet(models.Model):
    _name = 'thomasfleet.asset_photo_set'
    _description = 'Thomas Asset Photo Set'

    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle')
    photoDate = fields.Date("Date")
    photos = fields.One2many('thomasfleet.asset_photo', 'photo_set_id', 'Photos')
    encounter = fields.Selection([('pickup', 'Pick Up'),('service', 'Service'),('return', 'Return')],'Encounter Type')

    @api.model
    @api.depends('photoDate', 'encounter')
    def name_get(self):
        res = []
        for record in self:
            name = str(record.encounter) + "-"+ str(record.photoDate)
            res.append((record.id, name))
        return res


class ThomasAssetPhoto(models.Model):
    _name = 'thomasfleet.asset_photo'
    _description = 'Thomas Asset Photo'

    photo_set_id = fields.Many2one('thomasfleet.asset_photo_set', 'PhotoSet')
    position = fields.Selection([('driver side', 'Driver Side'), 
                                 ('passenger side', 'Passenger Side'),
                                 ('front', 'Front'),('back', 'Back'),
                                 ('driver side front angle', 'Driver Side front Angle'),
                                 ('passenger side front angle', 'Passenger Side Front Angle'),
                                 ('driver side back angle', 'Driver Side Back Angle'),
                                 ('passenger side back angle', 'Passenger Side Back Angle')])
    image = fields.Binary("Image", attachment=True)
    image_medium=fields.Binary("Small Image", attachment=True)
    image_medium=fields.Binary("Medium Image", attachment=True)

    @api.model
    @api.depends('position')
    def name_get(self):
        res = []
        for record in self:
            name = record.position
            res.append((record.id, name))
        return res

    @api.model
    def create(self, vals):
        # tools.image_resize_images(vals)
        return super(ThomasAssetPhoto, self).create(vals)

    @api.model
    def write(self, vals):
        # tools.image_resize_images(vals)
        return super(ThomasAssetPhoto, self).write(vals)



class ThomasFleetOdometer(models.Model):
    _inherit= 'fleet.vehicle.odometer' 


    lease_id = fields.Many2one('thomaslease.lease', 'Rental Agreement')
    customer_id =fields.Many2one(related="lease_id.customer_id", string="Customer", readonly=True)
    activity = fields.Selection([('lease_out', 'Rent Start'), ('lease_in', 'Rent Return'),('service', 'Service'),('spare_swap', 'Spare Swap'), ('spare_swap_back','Spare Swap Back')], string="Activity", tracking=True)

    def name_get(self):
        if self._context.get('lease'):
            res = []
            for record in self:
                name = '{0:,.2f}'.format(record.value)
                res.append((record.id, name))
            return res
        else:
            print("Context is none")
            return super(ThomasFleetOdometer, self).name_get()


class ThomasFleetVehicleModel(models.Model):
    _inherit = 'fleet.vehicle.model'
    _description = 'Thomas Fleet Vehicle Model'


    name = fields.Char('Model name', required=True)
    trim_id = fields.One2many('thomasfleet.trim', 'model_id', 'Available Trims')

    @api.model
    @api.depends('name')
    def name_get(self):
        res = []
        for record in self:
            name = record.name
            res.append((record.id, name))
        return res


class ThomasFleetTrim(models.Model):
    _name = 'thomasfleet.trim'
    _description = 'Thomas Fleet Trim'


    name = fields.Char('Trim Name')
    description = fields.Char('Description')
    brand_id = fields.Many2one(related='model_id.brand_id', string='Make')
    model_id = fields.Many2one('fleet.vehicle.model', required=True, string='Model', help='Model of the vehicle',
                               domain="[('brand_id','=',brand_id)]")


class ThomasFleetLeaseStatus(models.Model):
    _name = 'thomasfleet.lease_status'
    _description = 'Thomas Fleet Lease Status'


    name = fields.Char('Rental Status')
    description = fields.Char('Description')


class ThomasFleetLocation(models.Model):
    _name = 'thomasfleet.location'
    _description = 'Thomas Fleet Location'

    name = fields.Char('Location')
    description = fields.Char('Description')


class ThomasFleetSeatMaterial(models.Model):
    _name = 'thomasfleet.seatmaterial'
    _description = 'Thomas Fleet Seat Material'

    name = fields.Char('Seat Material')
    description = fields.Char('Description')


class ThomasFleetFloorMaterial(models.Model):
    _name = 'thomasfleet.floormaterial'
    _description = 'Thomas Fleet Floor Material'

    name = fields.Char('Floor Material')
    description = fields.Char('Description')


class ThomasFleetFuelType(models.Model):
    _name = 'thomasfleet.fueltype'
    _description = 'Thomas Fleet Fuel Type'

    name = fields.Char('Fuel Type')
    description = fields.Char('Description')


class ThomasFleetAssetClass(models.Model):
    _name = 'thomasfleet.asset_class'
    _description = 'Thomas Fleet Asset Class'

    name = fields.Char('Asset Class')
    description = fields.Char('Description')


class ThomasFleetInsuranceClass(models.Model):
    _name = 'thomasfleet.insurance_class'
    _description = 'Thomas Fleet Insurance Class'

    name = fields.Char('Insurance Class')
    description = fields.Char('Description')

class ThomasFleetInclusions(models.Model):
    _name = 'thomasfleet.inclusions'
    _description = 'Thomas Fleet Inclusions'

    name = fields.Char('Inclusion')
    description = fields.Char('Description')
    inclusion_cost= fields.Float('Cost')
    inclusion_charge=fields.Float('Monthly Rate')

class ThomasFleetWorkOrderIndex(models.Model):
    _name = 'thomasfleet.workorder_index'
    _description = 'Thomas Fleet Work Order Index'

    invoice_number = fields.Integer("Invoice Number")
    protractor_guid = fields.Char("Protractor GUID")

class ThomasFleetJournalItemWizard(models.TransientModel):
    _name = 'thomasfleet.journal_item.wizard'
    _description = 'Thomas Fleet Journal Item Wizard'

    @api.model
    def delete_all_journal_items(self):
        logging.debug('Deleteing all journal items')
        units = self.env['fleet.vehicle'].search([])
        for unit in units:
            unit._unlink_journal_items()

    @api.model
    def delete_all_workorders(self):
        logging.debug('Deleting all Work Orders')
        units = self.env['fleet.vehicle'].search([('fleet_status', '!=', 'DISPOSED')])
        for unit in units:
            unit._unlink_protractor_workerorders()

    @api.model
    def reload_work_orders(self):
        logging.debug('Reloating Work Orders')
        units = self.env['fleet.vehicle'].search([('fleet_status', '!=', 'DISPOSED')])
        wo = self.env['thomasfleet.workorder']
        for un in units:
            if un.vin_id:
                logging.debug("Updating Unit: " + str(un.unit_no) + " : " + str(un.vin_id))
                wo._create_protractor_workorders_for_unit(un.id, un.protractor_guid)
            else:
                logging.debug("NOT UPDATING Unit: " + str(un.unit_no) + " : " + str(un.protractor_guid))

    @api.model
    def create_all_journal_items(self):
        units = self.env['fleet.vehicle'].search([])
        jitem = self.env['thomasfleet.journal_item']
        for rec in units:
            logging.debug("Adding Journal Items for : " + rec.unit_no)
            jitem.createJournalItemsForUnit(rec.id)



    @api.model
    def refresh_all_items(self):
        print("Refreshing Items")
        self.delete_all_journal_items()
        self.delete_all_workorders()
        self.reload_work_orders()
        self.create_all_journal_items()




class ThomasFleetJournalItem(models.Model):
    _name = 'thomasfleet.journal_item'
    _description = 'Thomas Fleet Journal Item'

    def createJournalItemsForUnit(self,unit_id):

        inv_lines = self.env['account.move.line'].search([('vehicle_id', '=', unit_id),
                                                             ('invoice_id.state', 'not in',['draft', 'cancel']),
                                                             ('invoice_id.thomas_invoice_class', 'in', ['rental','repair'])])
        journal_item = self.env['thomasfleet.journal_item']
        cu_date = datetime(2021, 1, 1)
        for inv in inv_lines:
            woDateS = parser.parse(inv.invoice_date)
            invDate = datetime.strptime(woDateS.strftime('%Y-%m-%d'), '%Y-%m-%d')
            if invDate >= cu_date:
                journal_item.with_context(skip_update=True).create({'transaction_date':inv.invoice_date,
                 'type':'revenue',
                 'revenue':inv.price_subtotal,
                 'invoice_line_id': inv.id,
                 'vehicle_id': inv.vehicle_id.id,
                 'product_id' : inv.lease_line_id.product_id.id,
                 'customer_id': inv.invoice_id.partner_id.id
                })

        wo_orders = self.env['thomasfleet.workorder'].search([('vehicle_id', '=', unit_id)])
        for wo in wo_orders:
            woDateS1 = parser.parse(wo.invoiceDate)
            woDate = datetime.strptime(woDateS1.strftime('%Y-%m-%d'), '%Y-%m-%d')
            if woDate >= cu_date:
                journal_item.with_context(skip_update=True).create({'transaction_date':wo.invoiceDate,
                 'type': 'expense',
                 'expense': wo.rnmTotal,
                 'work_order_id':wo.id,
                 'vehicle_id': wo.vehicle_id.id,
                 'product_id': wo.product_id.id,
                 'customer_id': wo.customer_id.id
                })


    def reload(self):
        print("RELOAD")

    @api.depends('invoice_line_id','work_order_id', 'type')
    def default_vehicle_id(self):
        for rec in self:
            if rec.type == 'revenue':
                return self.invoice_line_id.vehicle_id
            else:
                return self.work_order_id.vehicle_id

    @api.depends('invoice_line_id', 'work_order_id', 'type')
    def default_customer_id(self):
        for rec in self:
            if rec.type == 'revenue':
                return self.invoice_line_id.invoice_id.partner_id
            else:
                return self.work_order_id.customer_id

    @api.depends('invoice_line_id', 'work_order_id', 'type')
    def default_product_id(self):
        for rec in self:
            if rec.type == 'revenue':
                return self.invoice_line_id.lease_line_id.product_id
            else:
                return self.work_order_id.customer_id

    transaction_date = fields.Datetime("Transaction Date")
    expense = fields.Float("Expense")
    revenue = fields.Float("Revenue")
    type = fields.Selection([('revenue', 'Revenue'), ('expense', 'Expense')])
    work_order_id = fields.Many2one('thomasfleet.workorder', string='Work Order', help='Work Order For a Vehicle')
    invoice_line_id = fields.Many2one('account.move.line', string='Invoice Line Item', help='Rental Invoice for the Unit')
    customer_id = fields.Many2one('res.partner', default=default_customer_id,  string='Customer',
                                  help='Work Order For a Vehicle', readonly=True)
    vehicle_id = fields.Many2one('fleet.vehicle',default=default_vehicle_id,  string='Unit',
                                 help='Work Order For a Vehicle', readonly=True)
    product_id = fields.Many2one('product.product',default=default_product_id, string='Product',
                                 help='Product', readonly=True)


class ThomasFleetWorkOrder(models.Model):
    _name = 'thomasfleet.workorder'
    _description = 'Thomas Fleet Work Order'


    _res = []
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle')
    customer_id = fields.Many2one('res.partner', 'Customer')
    product_id = fields.Many2one('product.product', 'Product')
    unit_no = fields.Char(related='vehicle_id.unit_no', string="Unit #")
    workorder_details = fields.One2many('thomasfleet.workorder_details', 'workorder_id',  'Work Order Details')
    protractor_guid = fields.Char('Protractor GUID', related='vehicle_id.protractor_guid')
    invoiceTime = fields.Datetime('Invoice Time')
    invoiceDate = fields.Datetime('Invoice Date')
    workOrderTime = fields.Datetime('WorkOrder Time')
    workOrderDate = fields.Datetime('WorkOrder Date')
    technichan = fields.Char('Technician')
    serviceAdvisor = fields.Char('Service Advisor')
    lastModifiedBy = fields.Char('Last Modified By')
    workOrderNumber = fields.Char('Work Order Number')
    workflowStage = fields.Char("Workflow Stage")
    invoiceNumber = fields.Char('Invoice Number')
    partsTotal = fields.Float('Parts Total')
    subletTotal= fields.Float('Sublet Total')
    grandTotal=fields.Float('Grand Total')
    laborTotal=fields.Float('Labor Total')
    otherChargeTotal = fields.Float('Other Charge Total')
    netTotal=fields.Float('Net Total')
    rnmTotal = fields.Float('RnM Total', compute="_compute_rnm_total")
    invoice_guid = fields.Char('Invoice Guid')

    def _compute_rnm_total(self):
        for rec in self:
            rec.rnmTotal = rec.netTotal + rec.otherChargeTotal

    def search_count(self, args):
        print("Search Count")
        if len(args) == 1:
            return super(ThomasFleetWorkOrder, self).search_count(args)
        else:
            if len(args) == 2:
                vehicle_id = args[0][2]
                guid = args[1][2]
                wos = self._get_protractor_workorders_for_unit(vehicle_id,guid)
            else:
                wos = self._get_protractor_workorders()
            return len(wos)

    def get_invoice_details_rest(self):
        url = "https://integration.protractor.com/IntegrationServices/1.0/Invoice/" + str(self.invoice_guid)

        headers = {
            'connectionId': "8c3d682f873644deb31284b9f764e38f",
            'apiKey': "fb3c8305df2a4bd796add61e646f461c",
            'authentication': "S2LZy0munq81s/uiCSGfCvGJZEo=",
            'Accept': "application/json",
            'cache-control': "no-cache",
            'Postman-Token': "7c083a2f-d5ce-4c1a-aa35-8da253b61bee"
        }

        response = requests.request("GET", url, headers=headers)
        data = response.json()
        # inv_det_model = self.env['thomasfleet.invoice_details']
        for invDets in self.workorder_details:
            for invDetLine in invDets:
                invDetLine.unlink()
            invDets.unlink()
        # recs = inv_det_model.search(['invoice_id','=', self.id])

        sp_lines = []


        work_order_num = data['WorkOrderNumber']
        inv_num = data['InvoiceNumber']
        inv_guid = data['ID']

        for sp in data['ServicePackages']['ItemCollection']:
            inv_detail = {'title': sp['ServicePackageHeader']['Title'],
                          'description': sp['ServicePackageHeader']['Description'],
                          'invoice_number': inv_num,
                          'work_order_number': work_order_num,
                          'invoice_guid': inv_guid
                          }

            for spd in sp['ServicePackageLines']['ItemCollection']:
                inv_detail_line = {'invoice_number': inv_num,
                                   'work_order_number': work_order_num,
                                   'invoice_guid': inv_guid,
                                   'complete': spd.get('Completed'),
                                   'rank': spd.get('Rank'),
                                   'type': spd.get('Type'),
                                   'description': spd.get('Description'),
                                   'quantity': spd.get('Quantity'),
                                   'unit': spd.get('Unit'),
                                   'rate_code': spd.get('Rate Code'),
                                   'price': spd.get('Price'),
                                   'price_unit': spd.get('PriceUnit'),
                                   'minimum_charge': spd.get('Minimum Charge'),
                                   'total': spd.get('Total'),
                                   'discount': spd.get('Discount'),
                                   'extended_total': spd.get('Exteneded Total'),
                                   'total_cost': spd.get('Total Cost'),
                                   'other_charge_code': spd.get('Other Charge Code'),
                                   'tags': spd.get('Tags'),
                                   'flag': spd.get('Flag'),
                                   'technician_name': spd.get('Technician'),
                                   'service_advisor': spd.get('Service Advisor')
                                   }

                sp_lines.append((0, 0, inv_detail_line))

            inv_detail['workorder_line_items'] = sp_lines

        return [(0, 0, inv_detail)]


    def get_invoice_details(self):

        url = "https://integration.protractor.com/IntegrationServices/1.0/Invoice/"+str(self.invoice_guid)

        headers = {
            'connectionId': "8c3d682f873644deb31284b9f764e38f",
            'apiKey': "fb3c8305df2a4bd796add61e646f461c",
            'authentication': "S2LZy0munq81s/uiCSGfCvGJZEo=",
            'Accept': "application/json",
            'cache-control': "no-cache",
            'Postman-Token': "7c083a2f-d5ce-4c1a-aa35-8da253b61bee"
        }

        response = requests.request("GET", url, headers=headers)
        data = response.json()
        #inv_det_model = self.env['thomasfleet.invoice_details']
        for invDets in self.workorder_details:
            for invDetLine in invDets:
                invDetLine.unlink()
            invDets.unlink()
        #recs = inv_det_model.search(['invoice_id','=', self.id])

        sp_lines = []

        work_order_num = data['WorkOrderNumber']
        inv_num = data['InvoiceNumber']
        inv_guid = data['ID']

        for sp in data['ServicePackages']['ItemCollection']:
            inv_detail = {'title': sp['ServicePackageHeader']['Title'],
                          'description': sp['ServicePackageHeader']['Description'],
                          'invoice_number': inv_num,
                          'work_order_number':work_order_num,
                          'invoice_guid':inv_guid
                          }

            for spd in sp['ServicePackageLines']['ItemCollection']:
                inv_detail_line ={'invoice_number': inv_num,
                                  'work_order_number': work_order_num,
                                  'invoice_guid': inv_guid,
                                  'complete': spd.get('Completed'),
                                  'rank': spd.get('Rank'),
                                  'type': spd.get('Type'),
                                  'description': spd.get('Description'),
                                  'quantity': spd.get('Quantity'),
                                  'unit': spd.get('Unit'),
                                  'rate_code': spd.get('Rate Code'),
                                  'price': spd.get('Price'),
                                  'price_unit': spd.get('PriceUnit'),
                                  'minimum_charge': spd.get('Minimum Charge'),
                                  'total': spd.get('Total'),
                                  'discount':spd.get('Discount'),
                                  'extended_total': spd.get('Exteneded Total'),
                                  'total_cost': spd.get('Total Cost'),
                                  'other_charge_code': spd.get('Other Charge Code'),
                                  'tags': spd.get('Tags'),
                                  'flag': spd.get('Flag'),
                                  'technician_name': spd.get('Technician'),
                                  'service_advisor': spd.get('Service Advisor')
                                  }

                sp_lines.append((0,0,inv_detail_line))

            inv_detail['workorder_line_items']= sp_lines
            self.workorder_details = [(0, 0, inv_detail)]



    def thomas_workorder_form_action(self):
        print("THOMAS FORM ACTION")

    def _create_protractor_workorders_for_all_units(self):
        units = self.env['fleet.vehicle'].search([('fleet_status', '!=', 'DISPOSED')])
        self.log.info("Number of Units for Updating: " + str(len(units)))
        for unit in units:
            if unit.vin_id:
                self.log.info("Updating Unit: " + str(unit.unit_no) + " : " + str(unit.vin_id))
                self._create_protractor_workorders_for_unit(unit.id, unit.protractor_guid)
                self.log.info("Created WorkOrders")
            else:
                print("NOT UPDATING Unit: " + str(unit.unit_no) + " : " + str(unit.protractor_guid))

    def _create_protractor_workorders_for_unit(self,vehicle_id,unit_guid):
        url = "https://integration.protractor.com/IntegrationServices/1.0/ServiceItem/" + str(
            unit_guid) + "/Invoice"
        da = datetime.now()
        querystring = {" ": "", "startDate": "2021-01-01", "endDate": da.strftime("%Y-%m-%d"), "%20": ""}

        headers = {
            'connectionId': "8c3d682f873644deb31284b9f764e38f",
            'apiKey': "fb3c8305df2a4bd796add61e646f461c",
            'authentication': "S2LZy0munq81s/uiCSGfCvGJZEo=",
            'Accept': "application/json",
            'cache-control': "no-cache",
            'Postman-Token': "7c083a2f-d5ce-4c1a-aa35-8da253b61bee"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        # print("INVOICE DATA " + response.text)
        workorders = []
        the_unit = self.env['fleet.vehicle'].search([('id','=',vehicle_id)])
        if response.status_code == 200:
            data = response.json()
            aid = 0
            for item in data['ItemCollection']:
                # if item['ID'] not in workorders.items():
                #    print("Not Found")
                aid = aid + 1
                inv = {'vehicle_id': vehicle_id,
                       'unit_no' : the_unit.unit_no,
                       'invoice_guid': item['ID'],
                       'workOrderNumber': str(item['WorkOrderNumber']),
                       'workflowStage': item['WorkflowStage'],
                       'invoiceNumber': str(item['InvoiceNumber'])}
                if 'Summary' in item:
                    inv['grandTotal'] = item['Summary']['GrandTotal']
                    inv['netTotal'] = item['Summary']['NetTotal']
                    inv['laborTotal'] = item['Summary']['LaborTotal']
                    inv['partsTotal'] = item['Summary']['PartsTotal']
                    inv['subletTotal'] = item['Summary']['SubletTotal']
                    inv['otherChargeTotal']= item['Summary']['OtherChargeTotal']
                woStr = str(item['Header']['CreationTime'])
                wod = parser.parse(woStr)
                # woDT = str(item['Header']['CreationTime']).split("T")
                # woDT = datetime(item['Header']['CreationTime'])s
                wdate = datetime.strptime(wod.strftime('%Y-%m-%d'), '%Y-%m-%d')
                inv['workOrderDate'] = wod.date()
                #inv['workOrderTime'] = wod.time()
                invStr = str(item['InvoiceTime'])
                invDT = parser.parse(invStr)  # str(item['InvoiceTime']).split("T")
                iDate = datetime.strptime(invDT.strftime('%Y-%m-%d'), '%Y-%m-%d')
                inv['invoiceDate'] = invDT.date()
                #inv['invoiceTime'] = iDate.time()
                if 'Technician' in item:
                    inv['technichan'] = str(item['Technician']['Name'])
                if 'ServiceAdvisor' in item:
                    inv['serviceAdvisor'] = str(item['ServiceAdvisor']['Name'])
                if 'Header' in item:
                    per = str(item['Header']['LastModifiedBy'])
                    uName = per.split("\\")
                    # print(uName)
                    inv['lastModifiedBy'] = uName[1]
                if 'Contact' in item:
                    con_guid = item['Contact']['ID']
                    if con_guid:
                        customer_id = self.env['res.partner'].search([('protractor_guid', '=', con_guid)])
                        if customer_id:
                            print("Found Customer ID: " + str(customer_id) + " for: "+con_guid)
                            inv['customer_id'] = customer_id.id
                        else:
                            inv['customer_id'] = False

                product_id = self.env['product.product'].search([('name', 'like','Maintenance - General')])
                if product_id:
                    inv['product_id'] = product_id.id
                else:
                    inv['product_id'] = False
                dbINV = self.with_context(skip_update=True).create(inv)
                print("WorkOrder Created -> ID " + str(dbINV.id))
                workorders.append(dbINV)

        return workorders

    def _get_protractor_workorders_for_unit(self,vehicle_id,unit_guid):
        url = "https://integration.protractor.com/IntegrationServices/1.0/ServiceItem/" + str(
            unit_guid) + "/Invoice"
        da = datetime.now()
        querystring = {" ": "", "startDate": "2021-01-01", "endDate": da.strftime("%Y-%m-%d"), "%20": ""}

        headers = {
            'connectionId': "8c3d682f873644deb31284b9f764e38f",
            'apiKey': "fb3c8305df2a4bd796add61e646f461c",
            'authentication': "S2LZy0munq81s/uiCSGfCvGJZEo=",
            'Accept': "application/json",
            'cache-control': "no-cache",
            'Postman-Token': "7c083a2f-d5ce-4c1a-aa35-8da253b61bee"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        workorders = []
        #print("INVOICE DATA " + response.text)
        if response.status_code == 200:
            data = response.json()
            aid = 0
            for item in data['ItemCollection']:
                # if item['ID'] not in workorders.items():
                #    print("Not Found")
                aid = aid + 1
                inv = {'vehicle_id': vehicle_id,
                       'invoice_guid': item['ID'],
                       'workOrderNumber': str(item['WorkOrderNumber']),
                       'workflowStage': item['WorkflowStage'],
                       'invoiceNumber': str(item['InvoiceNumber'])}
                if 'Summary' in item:
                    inv['grandTotal'] = item['Summary']['GrandTotal']
                    inv['netTotal'] = item['Summary']['NetTotal']
                    inv['laborTotal'] = item['Summary']['LaborTotal']
                    inv['partsTotal'] = item['Summary']['PartsTotal']
                    inv['subletTotal'] = item['Summary']['SubletTotal']
                    inv['otherChargeTotal'] = item['Summary']['OtherChargeTotal']
                woStr=str(item['Header']['CreationTime'])
                wod = parser.parse(woStr)
                #woDT = str(item['Header']['CreationTime']).split("T")
                #woDT = datetime(item['Header']['CreationTime'])s
                wdate = datetime.strptime(wod.strftime('%Y-%m-%d'),'%Y-%m-%d')
                inv['workOrderDate'] = wdate.date()
                inv['workOrderTime'] = wdate.time()
                invStr = str(item['InvoiceTime'])
                invDT = parser.parse(invStr)#str(item['InvoiceTime']).split("T")
                iDate = datetime.strptime(invDT.strftime('%Y-%m-%d'),'%Y-%m-%d')
                inv['invoiceDate'] = iDate.date()
                inv['invoiceTime'] = iDate.time()
                if 'Technician' in item:
                    inv['technichan'] = str(item['Technician']['Name'])
                if 'ServiceAdvisor' in item:
                    inv['serviceAdvisor'] = str(item['ServiceAdvisor']['Name'])
                if 'Header' in item:
                    per = str(item['Header']['LastModifiedBy'])
                    uName = per.split("\\")
                    # print(uName)
                    inv['lastModifiedBy'] = uName[1]
                if 'Contact' in item:
                    con_guid = item['Contact']['ID']
                    if con_guid:
                        customer_id = self.env['res.partner'].search([('protractor_guid', '=', con_guid)])
                        if customer_id:
                            print("Found Customer ID: " + str(customer_id) + " for: "+con_guid)
                            inv['customer_id'] = [(4,customer_id)]
                        else:
                            inv['customer_id'] = []
                #dbINV = self.create(inv)
                workorders.append(inv)

        return workorders

    def _get_protractor_workorders(self):
        url = "https://integration.protractor.com/IntegrationServices/1.0/WorkOrder/"
        da = datetime.now()
        querystring = {" ": "", "startDate": "2021-01-01", "endDate": da.strftime("%Y-%m-%d"), "%20": ""}#, "readInProgress":"True"}

        headers = {
            'connectionId': "8c3d682f873644deb31284b9f764e38f",
            'apiKey': "fb3c8305df2a4bd796add61e646f461c",
            'authentication': "S2LZy0munq81s/uiCSGfCvGJZEo=",
            'Accept': "application/json",
            'cache-control': "no-cache",
            'Postman-Token': "7c083a2f-d5ce-4c1a-aa35-8da253b61bee"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        print("WORK ORDER DATA " + response.text)
        data = response.json()

        workorders = [] #self._res
        aid = 0
        for item in data['ItemCollection']:
            #if item['ID'] not in workorders.items():
            #    print("Not Found")
            aid = aid +1
            inv={'id':item['InvoiceNumber'],'vehicle_id': self.id,
                 'invoice_guid' : item['ID'],
                 'workOrderNumber': item['WorkOrderNumber'],
                 'workflowStage' : item['WorkflowStage'],
                 'invoiceNumber': item['InvoiceNumber']}
            if 'Summary' in item:
                inv['grandTotal'] = item['Summary']['GrandTotal']
                inv['netTotal'] = item['Summary']['NetTotal']
                inv['laborTotal'] = item['Summary']['LaborTotal']
                inv['partsTotal'] = item['Summary']['PartsTotal']
                inv['subletTotal'] = item['Summary']['SubletTotal']
                inv['otherChargeTotal'] = item['Summary']['OtherChargeTotal']

            woDT = str(item['Header']['CreationTime']).split("T")
            inv['workOrderDate'] = woDT[0]
            inv['workOrderTime'] = woDT[1]
            invDT = str(item['InvoiceTime']).split("T")
            inv['invoiceDate']= invDT[0]
            inv['invoiceTime']= invDT[1]
            if 'Technician' in item:
                inv['technichan'] = str(item['Technician']['Name'])
            if 'ServiceAdvisor' in item:
                inv['serviceAdvisor'] = str(item['ServiceAdvisor']['Name'])
            if 'Header' in item:
                per =str(item['Header']['LastModifiedBy'])
                uName = per.split("\\")
                #print(uName)
                inv['lastModifiedBy'] = uName[1]
            if 'Contact' in item:
                con_guid = item['Contact']['ID']
                if con_guid:
                    customer_id = self.env['res.partner'].search([('protractor_guid', '=', con_guid)])
                    if customer_id:
                        print("Found Customer ID: " + str(customer_id) + " for: " + con_guid)
                        inv['customer_id'] = customer_id.id
                    else:
                        inv['customer_id'] = False

            product_id = self.env['product.product'].search([('name', 'like','Maintenance - General')])
            if product_id:
                inv['product_id'] = product_id.id
            else:
                inv['product_id'] = False

            workorders.append(inv)

        return workorders

    @api.model
    def act_get_workorder_details(self):
        print("FIRED OF INVOICE DETAILS ACTION")
        for rec in self:
            if rec.workorder_details:  # don't add invoices right now if there are some
                for inv_det in rec.invoice_details:
                    print("UNLINKING  INVOICE:::" + str(inv_det.workorder_id))
                    inv_det.unlink()
        self.ensure_one()
        self.get_workorder_details()

        res = self.env['ir.actions.act_window']._for_xml_id('thomasfleet.thomas_workorder_details_action')
        res.update(
            context=dict(self.env.context, default_workorder_id=self.id, search_default_parent_false=True),
            domain=[('workorder_id', '=', self.id)]
        )
        return res

    @api.model
    def generate_account_invoices(self):
        print ("Generating Account Invoices")


class ThomasFleetWorkOrderDetails(models.Model):
    _name = 'thomasfleet.workorder_details'
    _description = 'Thomas Fleet Work Order Details'

    workorder_id = fields.Many2one('thomasfleet.workorder', 'Work Order')
    workorder_line_items = fields.One2many('thomasfleet.workorder_details_line', 'workorder_details_id', 'Work Order Details Line')
    invoice_number = fields.Char('Invoice Number')
    work_order_number = fields.Char('Work Order Number')
    title = fields.Char('Title')
    description = fields.Char('Description')
    type = fields.Char('Type')
    quantity = fields.Char('Quantity')
    rate = fields.Char('Rate')
    total = fields.Char('Total')
    invoice_guid = fields.Char('Invoice Guid')

    @api.model
    def act_get_invoice_details_line(self):
        res = self.env['ir.actions.act_window']._for_xml_id('thomasfleet.thomas_workorder_details_line_action')
        res.update(
            context=dict(self.env.context, default_invoice_id = self.id, search_default_parent_false=True),
            domain=[('workorder_details_id', '=', self.id)]
         )
        return res



class ThomasFleetWorkOrderDetailsLine(models.Model):
    _name = 'thomasfleet.workorder_details_line'
    _description = 'Thomas Fleet Work Order Details Line'

    workorder_details_id = fields.Many2one('thomasfleet.workorder_details', 'WorkOrder Details')
    complete = fields.Boolean('Complete')
    rank = fields.Integer('Rank')
    type = fields.Char('Type')
    description = fields.Char('Description')
    quantity = fields.Float('Quantity')
    unit = fields.Char('Unit')
    rate_code = fields.Char('Rate Code')
    price = fields.Float('Price')
    price_unit = fields.Char('PriceUnit')
    minimum_charge = fields.Float('Minimum Charge')
    total = fields.Float('Total')
    discount = fields.Float('Discount')
    extended_total = fields.Float('Extended Total')
    total_cost = fields.Float('Total Cost')
    other_charge_code = fields.Char('Other Charge Code')
    tags = fields.Char('Tags')
    flag = fields.Char('Flag')
    technician_name = fields.Char('Technician')
    service_advisor = fields.Char('Service Advisor')
    invoice_number =  fields.Char('Invoice Number')
    work_order_number = fields.Char('Work Order Number')
    invoice_guid = fields.Char('Invoice Guid')

class ThomasFleetAccessoryType(models.Model):
    _name='thomasfleet.accessory_type'
    _description = 'Thomas Fleet Accessory Type'

    name = fields.Char("Accessory Type")


class ThomasFleetAccessory(models.Model):
    _name = 'thomasfleet.accessory'
    _description = 'Thomas Fleet Accessory'

    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle')
    name = fields.Char('Accessory Name')
    description = fields.Char('Description')
    unit_no = fields.Char('Accessory #')
    thomas_purchase_price = fields.Float('Thomas Purchase Price')
    accessory_charge = fields.Float('Monthly Rate')
    purchase_date = fields.Date('Purchase Date')
    type = fields.Many2one('thomasfleet.accessory_type', 'Accessory Type')



    @api.model
    @api.depends('type')
    def name_get(self):
            res = []
            for record in self:
                if record.type.id == 12:
                    if record.name and record.unit_no:
                        name = record.name + " " + record.unit_no
                    else:
                        name = " 407 Transponder"
                    res.append((record.id, name))
                else:
                    res.append((record.id,record.name))
            return res



class ThomasFleetMXInvoiceWizard(models.TransientModel):
    _name = 'thomasfleet.mx.invoice.wizard'
    _description = 'Thomas Fleet MX Invoice Wizard'


    lease_ids = fields.Many2many('thomaslease.lease', string="Rent")
    invoice_date = fields.Date(string="Invoice Date")

    @api.model
    def record_lease_invoices(self):
        accounting_invoice = self.env['account.move']
        for wizard in self:
            leases = wizard.lease_ids
            for lease in leases:
                #determine if an invoice already exists for the lease and don't create again...warn user
                print("Accounting Invoice Create " +str(wizard.invoice_date) + " : "+ lease.id)
                #accounting_invoice.create({}) need to match customer to accounting invoice etc