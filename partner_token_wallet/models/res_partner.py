from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    token_wallet_line_ids = fields.One2many('token.wallet.line', 'partner_id', string='Token Wallet Lines')
    token_total_count = fields.Integer(compute='_compute_token_total_count', string='Total Tokens')

    @api.depends('invoice_ids.payment_state', 'invoice_ids.state')
    def _compute_token_total_count(self):
        for partner in self:
            partner._sync_token_wallet()
            partner.token_total_count = sum(partner.token_wallet_line_ids.mapped('token_count'))

    def _sync_token_wallet(self):
        TokenWalletLine = self.env['token.wallet.line']
        invoices = self.env['account.move'].search([
            ('commercial_partner_id', '=', self.commercial_partner_id.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', '=', 'paid'),
            ('token_wallet_processed', '=', False),
        ])
        for inv in invoices:
            token_products = {}

            # 1) Try invoice lines
            for line in inv.invoice_line_ids.filtered(
                lambda l: not l.display_type
                and l.product_id
                and l.product_id.product_tmpl_id.token_wallet_role
            ):
                token_qty = line.product_id.product_tmpl_id.token_qty or 0
                total_tokens = int(line.quantity or 0) * token_qty
                if total_tokens > 0:
                    pid = line.product_id.id
                    token_products[pid] = token_products.get(pid, 0) + total_tokens

            # 2) Fallback to sale order via invoice_origin
            if not token_products and inv.invoice_origin:
                sale_order = self.env['sale.order'].sudo().search([
                    ('name', '=', inv.invoice_origin),
                ], limit=1)
                if sale_order:
                    for sol in sale_order.order_line.filtered(
                        lambda l: l.product_id.product_tmpl_id.token_wallet_role
                    ):
                        token_qty = sol.product_id.product_tmpl_id.token_qty or 0
                        total_tokens = int(sol.product_uom_qty or 0) * token_qty
                        if total_tokens > 0:
                            pid = sol.product_id.id
                            token_products[pid] = token_products.get(pid, 0) + total_tokens

            # 3) Create or update wallet lines
            for product_id, total_tokens in token_products.items():
                existing = TokenWalletLine.search([
                    ('partner_id', '=', self.id),
                    ('product_id', '=', product_id),
                ], limit=1)
                if existing:
                    existing.token_count += total_tokens
                else:
                    product = self.env['product.product'].browse(product_id)
                    TokenWalletLine.create({
                        'partner_id': self.id,
                        'product_tmpl_id': product.product_tmpl_id.id,
                        'product_id': product_id,
                        'token_count': total_tokens,
                    })

            inv.token_wallet_processed = True
