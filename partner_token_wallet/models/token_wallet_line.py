from odoo import fields, models


class TokenWalletLine(models.Model):
    _name = 'token.wallet.line'
    _description = 'Token Wallet Line'
    _order = 'id desc'

    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade', index=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    token_count = fields.Integer(string='Token Count', required=True)
