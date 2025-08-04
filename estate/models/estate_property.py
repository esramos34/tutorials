import copy
from odoo import fields, models, api
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare

class EstateProperty(models.Model):
    _name = 'estate.property'
    _description = 'Estate Property'
    _order = 'id desc'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    description = fields.Text()
    postcode = fields.Char()
    date_availability = fields.Date(copy=False, default=lambda self: date.today() + relativedelta(months=3))
    expected_price = fields.Float(required=True)
    selling_price = fields.Float(readonly=True, copy=False, default=0.0)
    bedrooms = fields.Integer(default=2)
    living_area = fields.Float()
    facades = fields.Integer()
    garage = fields.Boolean()
    garden = fields.Boolean()
    garden_area = fields.Float()
    garden_orientation = fields.Selection(
        selection=[('north', 'North'), ('south', 'South'), ('east', 'East'), ('west', 'West')]
    )
    state = fields.Selection(
        selection=[('new', 'New'), ('offer_received', 'Offer Received'), ('offer_accepted', 'Offer Accepted'), ('sold', 'Sold'), ('canceled', 'Canceled')],
        default='new',
        required=True,
        copy=False
    )

    property_type_id = fields.Many2one('estate.property.type', string='Property Type')
    
    buyer_id = fields.Many2one('res.partner', string='Buyer', copy=False)
    salesperson_id = fields.Many2one('res.users', string='Salesperson', default=lambda self: self.env.user)
    tag_ids = fields.Many2many('estate.property.tag', string='Tags')
    offer_ids = fields.One2many('estate.property.offer', 'property_id', string='Offers')
    total_area = fields.Float(compute='_compute_total_area')
    best_price = fields.Float(compute='_compute_best_price')

    @api.depends('living_area', 'garden_area')
    def _compute_total_area(self):
        for record in self:
            record.total_area = record.living_area + record.garden_area

    @api.depends('offer_ids.price')
    def _compute_best_price(self):
        for record in self:
            prices = record.offer_ids.mapped('price')
            record.best_price = max(prices) if prices else 0.0

    @api.onchange('garden')
    def _onchange_garden(self):
        if self.garden:
            self.garden_area = 10
            self.garden_orientation = 'north'
        else:
            self.garden_area = 0
            self.garden_orientation = False

    def action_property_sold(self):
        if self.state == 'canceled':
            raise UserError('You cannot sell a canceled property')
        if self.state == 'offer_accepted':
            self.write({'state': 'sold'})
            offer_no_accepted = self.offer_ids.filtered(lambda o: o.status != 'accepted')
            offer_no_accepted.write({'status': 'refused'})
        else:
            raise UserError('You cannot sell a property that has not been offer accepted')

    def action_property_cancel(self):
        if self.state == 'sold':
            raise UserError('You cannot cancel a sold property')
        self.write({'state': 'canceled'})
        self.offer_ids.write({'status': 'refused'})
        self.buyer_id = False
        self.selling_price = 0

    _sql_constraints = [
        ('check_expected_price', 'CHECK(expected_price >= 0)', 'Expected price must be 0 or positive'),
        ('check_selling_price', 'CHECK(selling_price >= 0)', 'Selling price must be 0 or positive'),
    ]


    @api.constrains('selling_price', 'expected_price')
    def _check_selling_price(self):
        for record in self:
            # Ignorar si selling_price es 0
            if float_is_zero(record.selling_price, precision_digits=2):
                continue
            # Comparar: selling_price >= 90% de expected_price
            limit_price = record.expected_price * 0.9
            if float_compare(record.selling_price, limit_price, precision_digits=2) < 0:
                raise UserError("The selling price cannot be lower than 90% of the expected price.")

    @api.ondelete(at_uninstall=False)
    def _check_state_before_delete(self):
        for record in self:
            if record.state != 'canceled':
                raise UserError("Solo puedes borrar si está cancelado.")