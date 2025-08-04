from odoo import models, fields, api
from datetime import timedelta, date
from odoo.exceptions import UserError, ValidationError

class EstatePropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = "Property Offer"
    _order = 'price desc'

    price = fields.Float()
    status = fields.Selection(
        selection=[('accepted', 'Accepted'), ('refused', 'Refused')]
    )

    property_id = fields.Many2one('estate.property', string='Property')
    partner_id = fields.Many2one('res.partner', string='Partner')
    validity = fields.Integer(string='Validity (days)', default=7)
    date_deadline = fields.Date(compute='_compute_date_deadline', inverse='_inverse_date_deadline')

    property_type_id = fields.Many2one('estate.property.type', string='Property Type', related='property_id.property_type_id', store=True)

    @api.depends('create_date', 'validity')
    def _compute_date_deadline(self):
        for record in self:
            if record.create_date:
                creation_date = record.create_date.date()
                record.date_deadline = creation_date + timedelta(days=record.validity)
            else:
                record.date_deadline = date.today() + timedelta(days=record.validity)
            


    def _inverse_date_deadline(self):
        for record in self:
            if record.create_date:
                record.validity = (record.date_deadline - record.create_date.date()).days
            else:
                record.validity = (record.date_deadline - date.today()).days

    def action_property_offer_accept(self):
        self.ensure_one()  # Siempre buena práctica si solo esperas un registro

        if self.property_id.state == 'sold' or self.property_id.state == 'canceled':
            raise UserError('You cannot accept an offer for a sold property or canceled property')

        # Verificar si ya hay una oferta aceptada para esta propiedad
        already_accepted = self.property_id.offer_ids.filtered(
            lambda o: o.id != self.id and o.status == 'accepted'
        )
        if already_accepted:
            raise UserError('You cannot accept an offer for a property that already has an accepted offer')

        # Rechazar todas las demás ofertas
        other_offers = self.property_id.offer_ids.filtered(lambda o: o.id != self.id)
        other_offers.write({'status': 'refused'})

        # Aceptar esta oferta
        self.status = 'accepted'
        self.property_id.selling_price = self.price
        self.property_id.buyer_id = self.partner_id.id
        self.property_id.state = 'offer_accepted'

        return True

    def action_property_offer_reject(self):
        self.ensure_one()

        if self.status == 'accepted':
            if self.property_id.state == 'sold':
                raise UserError('You cannot reject an offer for a sold property')
            self.status = 'refused'
            self.property_id.selling_price = 0
            self.property_id.buyer_id = False
            self.property_id.state = 'offer_received'
        else:
            if self.property_id.state == 'sold' or self.property_id.state == 'canceled':
                raise UserError('You cannot reject an offer for a sold property or canceled property')
            self.status = 'refused'

        return True

    _sql_constraints = [
        ('check_price', 'CHECK(price > 0)', 'The price must be greater than 0'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            property_id = vals.get('property_id')
            price = vals.get('price')

            if price and property_id:
                property_rec = self.env['estate.property'].browse(property_id)

                max_price = max(property_rec.offer_ids.mapped('price'), default=0.0)
                if price < max_price:
                    raise ValidationError("Cannot create offer lower than existing ones.")

                # cambiar estado a 'offer_received'
                if property_rec.state == 'new':
                    property_rec.state = 'offer_received'
        
        return super().create(vals_list)