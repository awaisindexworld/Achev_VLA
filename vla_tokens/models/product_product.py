from odoo import api, fields, models, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    vla_is_token_product = fields.Boolean(
        string='VLA Token Product',
        help='Enable this on the actual product variant that grants VLA assessment tokens.',
    )
    vla_token_market = fields.Selection(
        selection=[
            ('b2c', 'B2C / Individual'),
            ('b2b', 'B2B / Company'),
        ],
        string='Token Market',
        compute='_compute_vla_token_market',
        inverse='_inverse_vla_token_market',
        store=True,
        readonly=False,
        default='b2c',
        help='Automatically derived from token quantity in the new flow: 1 token = B2C individual URL, 50/100 tokens = B2B company wallet credit.',
    )
    vla_token_market_manual = fields.Selection(
        selection=[
            ('b2c', 'B2C / Individual'),
            ('b2b', 'B2B / Company'),
        ],
        string='Manual Token Market',
        copy=False,
        help='Internal override used only if the market is manually changed.',
    )
    vla_token_duration = fields.Selection(
        selection=[
            ('30', '30 Minutes'),
            ('60', '60 Minutes'),
        ],
        string='Assessment Duration',
        help='Duration bucket this product grants or this course requires. In the new catalog flow, set this from the main course product: 30-minute product variants use 30; 60-minute product variants use 60.',
    )
    vla_token_qty = fields.Integer(
        string='Token Quantity',
        default=1,
        help='How many assessment tokens this variant grants. New flow variants are normally 1, 50, or 100 tokens. Quantity 1 is treated as B2C; 50/100 are treated as B2B wallet purchases.',
    )

    vla_website_variant_note = fields.Html(
        string='Website Variant Note',
        translate=True,
        help='Message shown on the website only when this exact variant is selected.',
    )

    @api.depends('vla_token_qty', 'vla_token_market_manual')
    def _compute_vla_token_market(self):
        for product in self:
            if product.vla_token_market_manual:
                product.vla_token_market = product.vla_token_market_manual
            elif int(product.vla_token_qty or 0) == 1:
                product.vla_token_market = 'b2c'
            else:
                product.vla_token_market = 'b2b'

    def _inverse_vla_token_market(self):
        for product in self:
            product.vla_token_market_manual = product.vla_token_market

    def vla_get_effective_token_market(self):
        """Return the token market used by processing logic.

        New purchase flow rule:
        - 1 token variant = B2C individual assessment URL
        - 50/100 token variants = B2B company wallet credit

        Manual market stays supported for existing/edge catalog records.
        """
        self.ensure_one()
        if self.vla_token_market_manual:
            return self.vla_token_market_manual
        if int(self.vla_token_qty or 0) == 1:
            return 'b2c'
        return 'b2b'

    def _vla_b2c_variant_description(self):
        return _(
            'This individual 1-token option is only for B2C users. '
            'After purchase, the direct assessment URL will be sent to the customer by email.'
        )

    def _vla_sync_individual_variant_description(self):
        for product in self.filtered(
                lambda p: p.vla_is_token_product and int(p.vla_token_qty or 0) == 1 and not p.vla_website_variant_note
        ):
            product.with_context(vla_skip_description_sync=True).write({
                'vla_website_variant_note': product._vla_b2c_variant_description(),
            })

    @api.onchange('vla_is_token_product', 'vla_token_qty')
    def _onchange_vla_individual_variant_description(self):
        for product in self:
            if product.vla_is_token_product and int(
                    product.vla_token_qty or 0) == 1 and not product.vla_website_variant_note:
                product.vla_website_variant_note = product._vla_b2c_variant_description()

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        products._vla_sync_individual_variant_description()
        return products

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('vla_skip_description_sync') and {'vla_is_token_product', 'vla_token_qty'} & set(
                vals):
            self._vla_sync_individual_variant_description()
        return res
