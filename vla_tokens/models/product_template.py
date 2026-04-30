from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_combination_info(
        self,
        combination=False,
        product_id=False,
        add_qty=1,
        parent_combination=False,
        only_template=False,
    ):
        combination_info = super()._get_combination_info(
            combination=combination,
            product_id=product_id,
            add_qty=add_qty,
            parent_combination=parent_combination,
            only_template=only_template,
        )

        combination_info['vla_website_variant_note'] = ''
        combination_info['vla_token_qty'] = 0
        combination_info['vla_is_token_product'] = False

        product = self.env['product.product'].browse(combination_info.get('product_id'))

        if product.exists():
            combination_info['vla_website_variant_note'] = product.vla_website_variant_note or ''
            combination_info['vla_token_qty'] = product.vla_token_qty or 0
            combination_info['vla_is_token_product'] = product.vla_is_token_product

        return combination_info