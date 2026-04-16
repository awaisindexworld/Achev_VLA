from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    token_wallet_role = fields.Boolean(
        string='Token Wallet Role',
        help='If checked, this product is a token product.',
    )
    token_qty = fields.Integer(
        string='Token Quantity',
        default=0,
        help='How many tokens this product grants.',
    )
