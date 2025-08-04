from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round

class EstateProperty(models.Model):
    _inherit = 'estate.property'

    def action_property_sold(self):
        res = super().action_property_sold()
                # Este print es solo para verificar que este método se ejecuta desde este módulo
        for property in self:
            if not property.buyer_id:
                continue

            # Cálculos
            commission = float_round(property.selling_price * 0.06, precision_digits=2)
            admin_fee = 100.0

            # Construir líneas de factura usando Command.create()
            invoice_lines = [
                (0, 0, {
                    'name': 'Commission (6%)',
                    'quantity': 1,
                    'price_unit': commission,
                }),
                (0, 0, {
                    'name': 'Administrative Fee',
                    'quantity': 1,
                    'price_unit': admin_fee,
                }),
            ]

            # Crear factura
            invoice_vals = {
                'partner_id': property.buyer_id.id,
                'move_type': 'out_invoice',
                'invoice_line_ids': invoice_lines,
            }

            invoice = self.env['account.move'].create(invoice_vals)
            print(f"✅ Factura creada (ID: {invoice.id}) con líneas para {property.buyer_id.name}")

        return res