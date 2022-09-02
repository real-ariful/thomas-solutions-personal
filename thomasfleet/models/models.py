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
        tools.image_resize_images(vals)
        return super(ThomasAssetPhoto, self).create(vals)

    @api.model
    def write(self, vals):
        tools.image_resize_images(vals)
        return super(ThomasAssetPhoto, self).write(vals)

class ThomasFleetTest(models.Model):
    _inherit = ['fleet.vehicle']

    unit_int = fields.Integer(compute='_getInteger', store=True)

    @api.depends('unit_no')
    def _getInteger(self):
        for rec in self:
            try:
                rec.unit_int = int(rec.unit_no)
            except ValueError:
                rec.unit_int = 0
                raise models.ValidationError('Protractor Unit # ' + rec.unit_no

                                             + ' is not valid (it must be an integer)')

    

    def default_unit_no(self):
        last_vehicle = self.env['fleet.vehicle'].search([], limit=1, order='unit_int desc')
        print('Last Unit #' + str(last_vehicle.unit_no))
        return str(int(last_vehicle.unit_no) + 1)


    unit_no = fields.Char("Unit #", default=default_unit_no, required=True, tracking=True)


class ThomasFleetVehicle(models.Model):
    _name = 'fleet.vehicle'
    _description = 'Thomas Fleet Vehicle'
    _inherit = ['thomas.asset', 'fleet.vehicle', 'mail.thread', 'mail.activity.mixin']
    _order = "unit_int asc"

    log = logging.getLogger('thomas')
    log.setLevel(logging.INFO)
    unit_int = fields.Integer(compute='_getInteger', store=True)
    
    @api.depends('unit_no')
    def _getInteger(self):
        for rec in self:
            try:
                rec.unit_int = int(rec.unit_no)
            except ValueError:
                rec.unit_int = 0
                raise models.ValidationError('Protractor Unit # ' + rec.unit_no

                                             + ' is not valid (it must be an integer)')

    

    def default_unit_no(self):
        last_vehicle = self.env['fleet.vehicle'].search([], limit=1, order='unit_int desc')
        print('Last Unit #' + str(last_vehicle.unit_no))
        return str(int(last_vehicle.unit_no) + 1)

    @api.model
    @api.onchange('maintenance_cost_to_date')
    def set_cost_report(self):
        self.cost_report = self.maintenance_cost_to_date

    # thomas_asset = fields.Many2one('thomas.asset', ondelete='cascade')
    # fleet_vehicle = fields.Many2one('fleet.vehicle', ondelete='cascade')
    # name = fields.Char(compute='_compute_vehicle_name', store=True)

    #plate registration?
    unit_no = fields.Char("Unit #", default=default_unit_no, required=True, tracking=True)
    protractor_workorders = fields.One2many('thomasfleet.workorder', 'vehicle_id', 'Work Orders')
    lease_agreements = fields.One2many('thomaslease.lease','vehicle_id', 'Rental Agreements')
    lease_invoice_ids = fields.Many2many('account.move',string='Invoices',
                                   relation='unit_lease_account_invoice_rel')
    lease_agreements_count = fields.Integer(compute='_compute_thomas_counts',string='Rental Agreements Count')
    lease_invoices_count = fields.Integer(compute='_compute_thomas_counts',string='Rental Invoices Count')
    workorder_invoices_count = fields.Integer(compute='_compute_thomas_counts',string='WorkOrders Count')
    unit_slug = fields.Char(compute='_compute_slug', readonly=True)
    vin_id = fields.Char('V.I.N', tracking=True)
    license_plate = fields.Char('License Plate',  required=False, tracking=True)
    brand_id = fields.Many2one(related='model_id.brand_id', string='Make', tracking=True)

    model_id = fields.Many2one('fleet.vehicle.model', 'Model', required=True, help='Model of the vehicle',
                               domain="[('brand_id','=',brand_id)]",tracking=True)

    trim_id = fields.Many2one('thomasfleet.trim', string='Trim', help='Trim for the Model of the vehicle',
                              domain="[('model_id','=',model_id)]",tracking=True)
    location = fields.Many2one('thomasfleet.location', tracking=True)
    # fields.Selection([('hamilton', 'Hamilton'), ('selkirk', 'Selkirk'), ('niagara', 'Niagara')])
    door_access_code = fields.Char('Door Access Code', tracking=True)
    body_style = fields.Char('Body Style', tracking=True)
    drive = fields.Char('Drive', tracking=True)
    wheel_studs = fields.Char('Wheel Studs', tracking=True)
    wheel_size = fields.Char('Wheel Size', tracking=True)
    wheel_style = fields.Char('Wheel Style', tracking=True)
    wheel_base = fields.Char('Wheel Base', tracking=True)
    box_size = fields.Char('Box Size', tracking=True)
    seat_material = fields.Many2one('thomasfleet.seatmaterial', 'Seat Material', tracking=True)
    flooring = fields.Many2one('thomasfleet.floormaterial', 'Floor Material', tracking=True)
    trailer_hitch = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Trailer Hitch', default='yes', tracking=True)
    brake_controller = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Brake Controller', default='yes', tracking=True)
    tires = fields.Char('Tires', tracking=True)
    capless_fuel_filler = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Capless Fuel Filter', default='no', tracking=True)
    bluetooth = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Bluetooth', default='yes', tracking=True)
    navigation = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Navigation', default='no', tracking=True)
    warranty_start_date = fields.Char('Warranty Start Date', tracking=True)
    seat_belts = fields.Integer('# Seat Belts', tracking=True)
    seats = fields.Integer('# Seats', help='Number of seats of the vehicle', tracking=True)
    doors = fields.Integer('# Doors', help='Number of doors of the vehicle', default=5, tracking=True)
    # fuel_type = fields.Selection([('gasoline', 'Gasoline'), ('diesel', 'Diesel')],'Fuel Type', default='gasoline')
    notes = fields.Text(compute='_get_protractor_notes_and_owner', string='Protractor Notes', tracking=True)
    rim_bolts = fields.Char('Rim Bolts', tracking=True)
    engine = fields.Char('Engine', tracking=True)
    fuel_type = fields.Many2one('thomasfleet.fueltype', 'Fuel Type', tracking=True)
    fleet_status = fields.Many2one('fleet.vehicle.state', 'Unit Status', tracking=True)
    air_conditioning = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Air Conditioning', default='yes', tracking=True)
    transmission = fields.Char("Transmission", tracking=True)
    protractor_guid = fields.Char(compute='protractor_guid_compute', change_default=True)
    stored_protractor_guid = fields.Char(compute='_get_protractor_notes_and_owner', readonly=True)
    qc_check = fields.Boolean('Data Accurracy Validated')
    fin_check = fields.Boolean('Financial Accuracy Validated')
    accessories = fields.One2many('thomasfleet.accessory','vehicle_id',string="Accessories", tracking=True)
    write_to_protractor = fields.Boolean(default=False)
    production_date = fields.Char("Production Date", tracking=True)
    pulled_protractor_data = fields.Boolean(default=False,string="Got Data from Protractor")
    protractor_owner_guid = fields.Char(compute='_get_protractor_notes_and_owner', string= 'Protractor Owner ID')
    unit_quality = fields.Selection([('new','New'), ('good','Good'),('satisfactory','Satisfactory'),('poor','Poor')],
                                    'Unit Quality',tracking=True)

    historical_revenue = fields.Float("Historical Revenue", tracking=True, default=0.00)
    revenue_to_date = fields.Float("Total Revenue", compute="compute_revenue", readonly=True, store=True)
    total_maintenance_cost_to_date = fields.Float("Lifetime Maintenance Cost", compute="_compute_maintenance_cost",
                                             readonly=True, store=True)
    maintenance_cost_to_date = fields.Float("Reporting Maintenance Cost (from 2020)", compute="_compute_maintenance_cost",
                                             readonly=True, store=True)
    licensing_cost_to_date = fields.Float("Licensing Cost")
    insurance_cost_to_date = fields.Float("Insurance Cost")
    line_items = fields.One2many('account.move.line','vehicle_id', string="Invoice Line Items")

    profitability_ratio = fields.Float("Revenue/Cost Ratio", compute="_compute_profitability_ratio", readonly=True,
                                       store=True)
    reporting_profit = fields.Float("Reporting Profit", compute="_compute_profitability_ratio", readonly=True,
                                    store=True)

    lifetime_profit = fields.Float("Total Profit", compute="_compute_profitability_ratio", readonly=True,
                                   store=True)

    all_cost = fields.Float("Total Costs", compute="_compute_maintenance_cost",
                                             readonly=True, store=True)

    cost_report = fields.Float("Cost Report", store=True)

    @api.model
    @api.depends('unit_no')
    def name_get(self):
        if self._context.get('lease'):
            res = []
            for record in self:
                name = record.unit_no
                res.append((record.id, name))
            return res
        else:
            print("Context is none")
            return super(ThomasFleetVehicle, self).name_get()

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):

        args = [] if args is None else args.copy()
        if not (name == '' and operator == 'ilike'):
            args += ['|',
                ('name', operator, name),
                ('unit_no', operator, name)]

        return super(ThomasFleetVehicle, self)._name_search(
            name='', args=args, operator='ilike',
            limit=limit, name_get_uid=name_get_uid)





    @api.depends('workorder_invoices_count','protractor_workorders')
    def _compute_maintenance_cost(self):
        wo_rec = self.env['thomasfleet.workorder']
        cu_date = datetime(2021,1,1)
        for rec in self:
            work_orders = wo_rec.search([('vehicle_id', '=', rec.id)])
            for wo in work_orders:
                woDateS = parser.parse(wo.invoiceDate)
                woDate = datetime.strptime(woDateS.strftime('%Y-%m-%d'), '%Y-%m-%d')
                if woDate >= cu_date:
                    rec.maintenance_cost_to_date += wo['netTotal']
                else:
                    rec.total_maintenance_cost_to_date += wo['netTotal']
            rec.all_cost += (rec.total_maintenance_cost_to_date + rec.licensing_cost_to_date + rec.insurance_cost_to_date)


    @api.depends('lease_invoices_count','lease_invoice_ids','historical_revenue')
    def compute_revenue(self):
        for rec in self:
            for line in rec.line_items:
                rec.revenue_to_date += line.price_total
            rec.revenue_to_date += rec.historical_revenue


    # accessories = fields.Many2many()
    @api.depends('revenue_to_date', 'maintenance_cost_to_date','total_maintenance_cost_to_date','all_cost' )
    def _compute_profitability_ratio(self):
        for rec in self:
            rec.lifetime_profit = rec.revenue_to_date - rec.all_cost
            rec.reporting_profit = rec.revenue_to_date - rec.maintenance_cost_to_date
            if rec.maintenance_cost_to_date > 0 and rec.revenue_to_date > 0:
                rec.profitability_ratio = rec.revenue_to_date/rec.maintenance_cost_to_date
            else:
                rec.profitability_ratio = 0.0

    @api.depends('stored_protractor_guid')
    def protractor_guid_compute(self):
        #if self:
        #    print('HERE IS THE STORED PGUID:' + str(self.stored_protractor_guid))

        for record in self:
           # print('Computing GUID ' + str(record.stored_protractor_guid))
            if not record.stored_protractor_guid:
                guid = record.get_protractor_id()
                self.log.info("GUID DICTIONARY: " + str(guid))
                #record.stored_protractor_guid = guid['id']
                if guid:
                    #print('Retrieved GUID' + guid['id'])

                    if guid['id']:
                        record.protractor_guid = guid['id']
                        #record.stored_protractor_guid = guid['id']
                        #record.with_context(skip_update=True).stored_protractor_guid = guid['id']
                        #record.with_context(skip_update=True).update({'stored_protractor_guid': guid['id']})
                    else:
                        print("Problem with GUID in protractor")
                        record.protractor_guid = 'Unable to locate Unit by VIN in Protractor'
                else:
                    print("Could NOT Retrieve GUID")
                    record.protractor_guid = 'Unable to locate Unit by VIN in Protractor'
            else:
                record.protractor_guid = record.stored_protractor_guid

    def _generateProtractorNotes(self):
        if self.notes:
            p_notes = self.notes
        else:
            p_notes = "Body Style: " + str(self.body_style) + "\r\n" + "Drive: " + str(self.drive) + "\r\n" + "Flooring: " +\
                  str(self.flooring.name)+ "\r\n" + "Wheel Base: " + str(self.wheel_base) + "\r\n" + "Box Size: " + \
                  str(self.box_size) + "\r\n" + "Seat Type: " + str(self.seat_material.name) + "\r\n" + "Seat Belts: " + \
                  str(self.seat_belts) + "\r\n" + "Trailer Hitch: " + str(self.trailer_hitch) + "\r\n" + \
                  "Brake Controller: " + str(self.brake_controller) + "\r\n" + "Tires: " + str(self.tires) + "\r\n" + \
                  "Fuel Type: " + str(self.fuel_type.name) + "\r\n" + \
                  "Location: " + str(self.location.name) + "\r\n" + \
                  "Door Access Code: " + str(self.door_access_code) + "\r\n" + \
                  "Wheel Studs: " + str(self.wheel_studs) + "\r\n" + \
                  "Rim Bolts: " + str(self.rim_bolts) + "\r\n" + \
                  "Capless Fuel Filter: " + str(self.capless_fuel_filler) + "\r\n" + \
                  "Bluetooth: " + str(self.bluetooth) + "\r\n" + \
                  "Navigation: " + str(self.navigation) + "\r\n"

        return p_notes


    @api.depends('unit_no', 'model_id')
    def _compute_slug(self):
        for record in self:

            if record.unit_no and record.model_id:
                record.unit_slug = 'Unit # - ' + record.unit_no + '-' + record.model_id.brand_id.name + '/' + record.model_id.name
            else:
                record.unit_slug = 'Unit # - '

    def _compute_thomas_counts(self):
        the_agreements = self.env['thomaslease.lease']
        the_invoices = self.env['account.move']
        the_workorders = self.with_context(checkDB=True).env['thomasfleet.workorder']
        for record in self:
            record.lease_agreements_count = the_agreements.search_count([('vehicle_id', '=', record.id)])
            record.lease_invoices_count = the_invoices.search_count([('id', 'in', tuple(record.lease_invoice_ids.ids))])
            record.workorder_invoices_count = the_workorders.search_count([('vehicle_id', '=', record.id),
                                                                           ('guid', '=', record.protractor_guid)])


    def ok_pressed(self):
        self.with_context(manual_update=True).update_protractor()

    def check_update_portractor(self):
        theMess = self.env['thomaslease.message']

        rec = theMess.create({'message': "Do you want to unit update " + self.unit_no +" in Protractor?"})

        res = self.env['ir.actions.act_window']._for_xml_id('thomasfleet.message_action')

        res.update(
            context=dict(self.env.context, ok_handler='ok_pressed', caller_model=self._name, caller_id=self.id),
            res_id=rec.id
        )
        return res

    def update_protractor(self):
        url = " "
        guid = ""
        if self.stored_protractor_guid:
            url = "https://integration.protractor.com/IntegrationServices/1.0/ServiceItem/"+self.stored_protractor_guid
            guid = self.stored_protractor_guid
        else:
            if self.protractor_guid:
                url = "https://integration.protractor.com/IntegrationServices/1.0/ServiceItem/" + self.protractor_guid
                guid = self.protractor_guid
            else:
                url = "bad guid"

        vin = self.vin_id
        plateReg = "ON"
        unit = self.unit_no
        #self.protractor_guid
        if self.protractor_owner_guid:
            owner_id = self.protractor_owner_guid
        else:
            owner_id = "43e0319c-41bc-40c3-be47-336b9e0afaa1"
        theUnit = {
            "VIN":self.vin_id,
            "PlateRegistration":"ON",
            "ID":guid,
            "IsComplete":True,
            "Unit":self.unit_no,
            "Color": self.color,
            "Year": self.model_year,
            "Make": self.model_id.brand_id.name,
            "Model": self.model_id.name,
            "Submodel":self.trim_id.name,
            "Engine": self.engine,
            "Type":"Vehicle",
            "Lookup":self.license_plate,
            "Description": self.unit_slug,
            "Usage": int(self.odometer),
            "ProductionDate":"",
            "Note": self._generateProtractorNotes(),
            "NoEmail": False,
            "NoPostCard": False,
            "PreferredContactMethod":"Email",
            "MarketingSource":"",
            "OwnerID": owner_id
            }
        payload =json.dumps(theUnit)


        headers = {
            'connectionId': "8c3d682f873644deb31284b9f764e38f",
            'apiKey': "fb3c8305df2a4bd796add61e646f461c",
            'authentication': "S2LZy0munq81s/uiCSGfCvGJZEo=",
            'Accept' : "application/json",
            'Content-Type': "application/json"
        }
        response = requests.request("POST", url, data=payload, headers=headers)



    def get_protractor_id(self):
        #print("IN GET PROTRACTOR ID for" + str(self.vin_id))
        self.ensure_one()
        self.log.info("Getting Protarctor ID for Vehicle: "+ str(self.vin_id))
        the_resp = dict()
        the_resp['id']= False
        the_resp['update'] = False

        if self.vin_id:
            url = "https://integration.protractor.com/IntegrationServices/1.0/ServiceItem/Search/"+self.vin_id
            headers = {
                'connectionId': "8c3d682f873644deb31284b9f764e38f",
                'apiKey': "fb3c8305df2a4bd796add61e646f461c",
                'authentication': "S2LZy0munq81s/uiCSGfCvGJZEo=",
                'Accept': "application/json"
            }
            response = requests.request("GET", url, headers=headers)

            self.log.info("JSON RESPONSE FROM PROTRACTOR" + response.text)
            data = response.json()
            the_id= False
            color=""
            for item in data['ItemCollection']:
                the_id = item['ID']


            if not the_id:
                the_id = uuid.uuid4()
                the_resp['id']= the_id
                the_resp['update']= True
                self.log.info("Setting Write to protractor cause no id found")
            else:
                self.log.info("Found an existing unit: "+the_id)
                the_resp['id']=the_id
                the_resp['update'] = False
                 #this can only be set on create
        else:
            if self.env.context.get('manual_update'):
                raise models.UserError('Vehicle VIN must be set before it can be linked, created or updated Protractor')

        self.log.info("RETURNING THE RESPONSE " + str(the_resp))
        return the_resp


    @api.model
    def write(self, values):
        #we only want to update protractor if the unit doesn't exist the firt time
        #subsequent updates shouldn't happen

        self.log.info("IN WRITE FUNCTION for Unit #" + str(self.unit_no))

        record = super(ThomasFleetVehicle,self).write(
            values)

        #self.message_post(body=values)

        self.log.info("Loop Breaker" + str(self.env.context.get('skip_update')))
        if self.env.context.get('skip_update'):
            print("BUSTING OUT")

        else:
            self.log.info("updating protractor")
            self.update_protractor()


        #ThomasFleetVehicle_write.get_protractor_id()

        return record


    @api.model
    def create(self, data):
        self = self.with_context(skip_update=True)
        print("before create")
        res = super(ThomasFleetVehicle, self).create(data)
        print("after create")
        guid= res.get_protractor_id()
        #print("GUID UDPATE VALUE" + str(guid['update']))
        if guid:
            if guid['update']:
                self = self.with_context(skip_update=False)
                res.with_context(self).stored_protractor_guid = guid['id']
            else:
                res.stored_protractor_guid = guid['id']


        #print("UPDATED CONTEXT" + str(self.env.context.get('skip_update')))
        print("after setting guid")
        return res

    def getMakeModelTrim(self,make,model,trim):
        theTrim = self.env['thomasfleet.trim'].search(
            [('brand_id.name', '=ilike', make), ('model_id.name', '=ilike', model), ('name', '=ilike', trim)],limit=1)
        return theTrim

    @api.onchange('vin_id')
    #@api.model
    def _get_protractor_data(self):
        print("GETTING PROTRACTOR DATA")
        the_resp = "NO VIN"
        if self.vin_id:
            url = "https://integration.protractor.com/IntegrationServices/1.0/ServiceItem/Search/" + self.vin_id
            headers = {
                'connectionId': "8c3d682f873644deb31284b9f764e38f",
                'apiKey': "fb3c8305df2a4bd796add61e646f461c",
                'authentication': "S2LZy0munq81s/uiCSGfCvGJZEo=",
                'Accept': "application/json",
                'Cache-Control': "no-cache",
                'Postman-Token': "9caffd55-2bac-4e79-abfc-7fd1a3e84c6d"
            }
            response = requests.request("GET", url, headers=headers)

            #logging.info(response.text)
            data = response.json()
            the_note = ""

            for item in data['ItemCollection']:
                the_note = item['Note']
                plate_reg = item['PlateRegistration']
                vin = item['VIN']
                unit = item['Unit']
                color = item['Color']
                year = item['Year']
                themake = item['Make']
                themodel = item['Model']
                thesubmodel = item['Submodel']
                engine = item['Engine']
                plate = item['Lookup']
                description = item['Description']
                usage = item['Usage']
                proddate = item['ProductionDate']
                ownerid = item['OwnerID']

                self.notes = the_note
                #self.vin_id = vin
                # "PlateRegistration": "ON",
                # "ID": self.stored_protractor_guid,
                # "IsComplete": True,
                # "Unit": self.unit_no,
                self.unit_no = unit
                self.color = color
                self.model_year = year
                self.odometer = int(usage)
                #try and find the complete product make,model,trim if not, try to add the missing part
                vehicleMakeModelTrim = self.getMakeModelTrim(themake,themodel,thesubmodel)
                if vehicleMakeModelTrim:
                    self.brand_id = vehicleMakeModelTrim.brand_id
                    self.model_id = vehicleMakeModelTrim.model_id
                    self.trim_id = vehicleMakeModelTrim.id
                else:
                    the_brand = self.env['fleet.vehicle.model.brand'].search([('name', '=ilike', themake)], limit=1)
                    if the_brand:
                        self.brand_id = the_brand.id
                    else:
                        brand_data={'name':themake}
                        the_new_brand = self.env['fleet.vehicle.model.brand'].create(brand_data)
                        self.brand_id = the_new_brand.id

                    the_model = self.env['fleet.vehicle.model'].search([('brand_id', '=', the_brand.id),('name', '=ilike', themodel)],limit=1)
                    if the_model:
                        self.model_id = the_model.id
                    else:
                        model_data={'name': themodel, 'brand_id':self.brand_id.id}
                        the_new_model = self.env['fleet.vehicle.model'].create(model_data)
                        self.model_id = the_new_model.id

                    the_trim = self.env['thomasfleet.trim'].search([('brand_id', '=', the_brand.id),('model_id', '=', the_model.id),('name', '=ilike', thesubmodel)],limit=1)
                    if the_trim:
                        print("Found Trim "+ the_trim.name)
                        self.trim_id = the_trim.id
                    else:
                        trim_data = {'name':thesubmodel, 'model_id':self.model_id.id, 'brand_id': self.brand_id.id}
                        the_new_trim = self.env['thomasfleet.trim'].create(trim_data)
                        self.trim_id = the_new_trim.id

                self.engine = engine
                self.license_plate = plate
                self.production_date = proddate
                self.pulled_protractor_data = True
                self.protractor_owner_guid = ownerid
                # "Usage": int(self.odometer),

                result ={'warning': {
                    'title': 'Vehicle VIN is in Protractor',
                    'message': 'Found an existing vechile with this VIN in Protractor.  The data has been copied to the form, changes will be saved back to protractor'
                }}
                return result

    @api.depends('vin_id')
    #@api.model
    def _get_protractor_notes_and_owner(self):
        the_resp = "NO VIN"
        for record in self:
            record.protractor_owner_guid = False
            record.stored_protractor_guid = False
            record.notes = False

            if record.vin_id:
                url = "https://integration.protractor.com/IntegrationServices/1.0/ServiceItem/Search/"+record.vin_id
                headers = {
                    'connectionId': "8c3d682f873644deb31284b9f764e38f",
                    'apiKey': "fb3c8305df2a4bd796add61e646f461c",
                    'authentication': "S2LZy0munq81s/uiCSGfCvGJZEo=",
                    'Accept': "application/json",
                    'Cache-Control': "no-cache",
                    'Postman-Token': "9caffd55-2bac-4e79-abfc-7fd1a3e84c6d"
                }
                response = requests.request("GET", url, headers=headers)


                data = response.json()
                the_note=""
                the_ownerID=""
                the_id=""

                for item in data['ItemCollection']:
                    the_note = item['Note']
                    the_ownerID = item['OwnerID']
                    the_id = item['ID']

                record.notes = the_note
                record.protractor_owner_guid = the_ownerID
                if not record.stored_protractor_guid:
                    record.stored_protractor_guid = the_id




    def _get_protractor_workorders_tbd(self):
        url = "https://integration.protractor.com/IntegrationServices/1.0/ServiceItem/"+str(self.stored_protractor_guid)+"/Invoice"
        da = datetime.now()
        querystring = {" ": "", "startDate": "2021-11-01", "endDate": da.strftime("%Y-%m-%d"), "%20": ""}

        headers = {
            'connectionId': "8c3d682f873644deb31284b9f764e38f",
            'apiKey': "fb3c8305df2a4bd796add61e646f461c",
            'authentication': "S2LZy0munq81s/uiCSGfCvGJZEo=",
            'Accept': "application/json",
            'cache-control': "no-cache",
            'Postman-Token': "7c083a2f-d5ce-4c1a-aa35-8da253b61bee"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        print("INVOICE DATA " + response.text)
        data = response.json()

        updatedInvoices = []
        invoices = self.protractor_workorders

        for a in invoices:
            invoiceFound = False
            for i in data['ItemCollection']:
                print("Invoice Numbers:::"+ str(a.invoiceNumber) +"=="+ str(i['InvoiceNumber']))
                if a.invoiceNumber == i['InvoiceNumber']:
                    print("Found ID " + a.id)
                    invoiceFound = True

            if not invoiceFound:
                print("Invoice Not Found# " + a.invoiceNumber)
                updatedInvoices.append((2,a.id,0))

        for item in data['ItemCollection']:
            inv={'vehicle_id': self.id,
                 'invoice_guid' : item['ID'],
                 'protractor_guid': self.stored_protractor_guid,
                 'workOrderNumber': item['WorkOrderNumber'],
                 'invoiceNumber': item['InvoiceNumber']}
            if 'Summary' in item:
                inv['grandTotal'] = item['Summary']['GrandTotal']
                inv['netTotal'] = item['Summary']['NetTotal']
                inv['laborTotal'] = item['Summary']['LaborTotal']
                inv['partsTotal'] = item['Summary']['PartsTotal']
                inv['subletTotal'] = item['Summary']['SubletTotal']
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


            invoiceNotFound=True
            invObj = self.env['thomasfleet.workoder'].create(inv)
            invDetsArr = invObj.get_invoice_details_rest()
            inv['workorder_details'] = invDetsArr
            for invoice in invoices:
                if invoice.invoiceNumber == item['InvoiceNumber']:
                    updatedInvoices.append((1, invoice.id, inv))
                    invoiceNotFound = False

            if invoiceNotFound:
                updatedInvoices.append((0,0,inv))



        print("Updated Invoices" + str(updatedInvoices))
        self.update({'protractor_workorders': updatedInvoices})


    def act_show_vehicle_photos(self):
        """ This opens log view to view and add new log for this vehicle, groupby default to only show effective costs
            @return: the costs log view
        """
        self.ensure_one()
        res = self.env['ir.actions.act_window']._for_xml_id('thomasfleet.thomas_asset_photos_action')
        res.update(
            context=dict(self.env.context, default_vehicle_id=self.id, search_default_parent_false=True),
            domain=[('vehicle_id', '=', self.id)]
        )
        print("Unit"+str(self.unit_no))
        for aSet in self.photoSets:
            print("ENCOUNTER" + aSet.encounter)
        return res



    def act_show_vehicle_lease_agreements(self):
        """ This opens log view to view and add new log for this vehicle, groupby default to only show effective costs
            @return: the costs log view
        """
        self.ensure_one()
        # action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")
        res = self.env['ir.actions.act_window']._for_xml_id('thomasfleet.thomas_lease_agreements_action')
        res.update(
            #context=dict(self.env.context, default_vehicle_id=self.id, search_default_parent_false=True),
            domain=[('vehicle_id', '=', self.id)]
        )
        print("Unit" + str(self.unit_no))

        return res

    def act_show_vehicle_lease_invoices(self):
        """ This opens log view to view and add new log for this vehicle, groupby default to only show effective costs
            @return: the costs log view
        """
        self.ensure_one()
        res = self.env['ir.actions.act_window']._for_xml_id('thomasfleet.thomas_lease_invoices_action')
        res.update(
            #context=dict(self.env.context, default_vehicle_id=self.id, search_default_parent_false=True),
            domain=[('id','in',tuple(self.lease_invoice_ids.ids))]
        )
        print("Unit" + str(self.unit_no))

        return res

    @api.model
    def _get_protractor_workrorders(self):
        print("WORK ORDERS GET")
        print('UNIT # ' + str(self.unit_no))

        wo_rec = self.env['thomasfleet.workorder']

        wo_rec._create_protractor_workorders_for_unit(self.id, self.protractor_guid)

        return

    @api.model
    def _unlink_protractor_workerorders(self):
        wo_rec = self.env['thomasfleet.workorder']
        for rec in self:
            work_orders = wo_rec.search([('vehicle_id', '=', rec.id)])
            for work_order in work_orders:
                print(" DELETING WORKORDER for UNIT "+ str(self.unit_no) +":::" + str(work_order.id))
                work_order.with_context(skip_update=True).unlink()
        return

    @api.model
    def _unlink_journal_items(self):
        ji_rec = self.env['thomasfleet.journal_item']
        for rec in self:
            j_items = ji_rec.search([('vehicle_id', '=', rec.id)])
            for j_item in j_items:
                logging.debug(" DELETING Journal Items for UNIT " + str(self.unit_no) + ":::" + str(j_item.id))
                j_item.with_context(skip_update=True).unlink()
        return

    def act_get_workorders(self):
        print("WORK ORDERS ACTION")
        print('SELF ID ' + str(self.id))

        wo_rec = self.env['thomasfleet.workorder']
        for rec in self:
            work_orders = wo_rec.search([('vehicle_id', '=', rec.id)])
            for work_order in work_orders:
                print(" DELETING INVOICE:::" + str(work_order.id))
                work_order.unlink()


        wo = self.env['thomasfleet.workorder']
        wos = wo._create_protractor_workorders_for_unit(self.id,self.protractor_guid)
        self.ensure_one()
        res = self.env['ir.actions.act_window']._for_xml_id('thomasfleet.thomas_workorder_action')
        res.update(
        context=dict(self.env.context, default_vehicle_id=self.id, search_default_parent_false=True,
                     ),
        domain=[('vehicle_id', '=', self.id)]
        )
        #jitems = self.env['thomasfleet.journal_item']
        #jitems.createJournalItemsForUnit(self.id)

        return res


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