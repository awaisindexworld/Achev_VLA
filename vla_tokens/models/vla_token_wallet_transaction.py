from odoo import fields, models


class VlaTokenWalletTransaction(models.Model):
    _name = 'vla.token.wallet.transaction'
    _description = 'VLA Token Wallet Transaction'
    _order = 'create_date desc, id desc'

    partner_id = fields.Many2one('res.partner', required=True, index=True, ondelete='cascade')
    wallet_line_id = fields.Many2one('vla.token.wallet.line', string='Wallet Line', ondelete='set null')
    duration = fields.Selection([('30', '30 Minutes'), ('60', '60 Minutes')], required=True, index=True)
    amount = fields.Integer(required=True)
    balance_after = fields.Integer(string='Balance After')
    reason = fields.Selection(
        selection=[
            ('purchase', 'Purchase'),
            ('invite', 'Invite Deduction'),
            ('manual', 'Manual Adjustment'),
            ('sync_reset', 'Sync Reset'),
        ],
        default='manual',
        required=True,
    )
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', ondelete='set null')
    invoice_id = fields.Many2one('account.move', string='Invoice', ondelete='set null')
    product_id = fields.Many2one('product.product', string='Product Variant', ondelete='set null')
    source_model = fields.Char()
    source_res_id = fields.Integer()
    note = fields.Char()

    def create_from_wallet_line(self, wallet_line, amount, reason='manual', source_record=None, note=None, invoice=None, sale_order=None, product=None):
        vals = {
            'partner_id': wallet_line.partner_id.id,
            'wallet_line_id': wallet_line.id,
            'duration': wallet_line.duration,
            'amount': amount,
            'balance_after': wallet_line.balance,
            'reason': reason,
            'note': note,
        }
        if invoice:
            vals['invoice_id'] = invoice.id
        if sale_order:
            vals['sale_order_id'] = sale_order.id
        if product:
            vals['product_id'] = product.id
        if source_record:
            vals['source_model'] = source_record._name
            vals['source_res_id'] = source_record.id
        return self.create(vals)
