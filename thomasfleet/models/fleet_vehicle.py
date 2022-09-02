# -*- coding: utf-8 -*-

from odoo import models, fields, api
import requests, json, uuid
from urllib import parse
from odoo.osv import expression

import logging
_logger = logging.getLogger(__name__)




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

    cost_report = fields.Float("Cost Report", readonly=True, store=True)

    @api.model
    @api.onchange('maintenance_cost_to_date')
    def set_cost_report(self):
        self.cost_report = self.maintenance_cost_to_date


    @api.depends('model_id')
    def _compute_model_fields(self):
        '''
        Copies all the related fields from the model to the vehicle
        '''
        model_values = dict()
        for vehicle in self.filtered('model_id'):
            if vehicle.model_id.id in model_values:
                write_vals = model_values[vehicle.model_id.id]
            else:
                # copy if value is truthy
                write_vals = {MODEL_FIELDS_TO_VEHICLE[key]: vehicle.model_id[key] for key in MODEL_FIELDS_TO_VEHICLE\
                    if vehicle.model_id[key]}
                model_values[vehicle.model_id.id] = write_vals
            if write_vals.get('fuel_type'):
                fuel_type_id = self.env['thomasfleet.fueltype'].search([('name', '=', write_vals.get('fule_type'))], limit=1)
                write_vals['fuel_type'] = fuel_type_id.id

            vehicle.write(write_vals)

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