# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    vla_tokens_processed = fields.Boolean(
        string='VLA Tokens Processed',
        copy=False,
        default=False,
        index=True,
    )

    def _get_vla_related_sale_order(self):
        self.ensure_one()

        if not self.invoice_origin:
            return self.env['sale.order']

        return self.env['sale.order'].sudo().search([
            ('name', '=', self.invoice_origin),
        ], limit=1)

    def _get_vla_token_sources(self):
        """
        Return token source rows from invoice lines first.

        If invoice lines do not carry the product flags correctly,
        fallback to the related sale order lines.
        """
        self.ensure_one()

        sources = []

        for line in self.invoice_line_ids.filtered(lambda l: not l.display_type and l.product_id):
            product = line.product_id

            if product.vla_is_token_product and product.vla_token_duration and product.vla_token_qty > 0:
                sources.append({
                    'product': product,
                    'quantity': int(line.quantity or 0),
                })

        if sources:
            return sources

        sale_order = self._get_vla_related_sale_order()

        if sale_order:
            for line in sale_order.order_line.filtered(lambda l: l.product_id):
                product = line.product_id

                if product.vla_is_token_product and product.vla_token_duration and product.vla_token_qty > 0:
                    sources.append({
                        'product': product,
                        'quantity': int(line.product_uom_qty or 0),
                    })

        return sources

    def _send_b2c_assessment_token_email(self, assessment_token):
        if self.env.context.get('vla_skip_b2c_email'):
            return False

        template = self.env.ref(
            'vla_tokens.mail_template_b2c_assessment_token',
            raise_if_not_found=False,
        )

        if not template:
            _logger.warning("VLA TOKENS: B2C assessment token mail template was not found.")
            return False

        if not (assessment_token.partner_id.email or assessment_token.candidate_email):
            _logger.warning(
                "VLA TOKENS: B2C assessment token %s has no recipient email.",
                assessment_token.display_name,
            )
            return False

        template.sudo().send_mail(assessment_token.id, force_send=True)
        return True

    def _vla_find_course_for_product(self, product):
        """
        Find the eLearning course connected to the purchased token product.

        New flow:
        - Product template = 30 min / 60 min
        - Variants = 1 / 50 / 100 tokens

        If customer buys 30 min / 1 token, we find any course connected
        to the 30 min template or any variant of that 30 min template.

        This means:
        - If course is connected to 30 min / 1 token, it works.
        - If course is connected to 30 min / 50 tokens, it still works.
        - If course is connected to 30 min / 100 tokens, it still works.
        - Same logic applies for 60 min.
        """
        self.ensure_one()

        if not product:
            return self.env['slide.channel']

        product = product.sudo()
        product_tmpl = product.product_tmpl_id
        variant_ids = product_tmpl.product_variant_ids.ids

        SlideChannel = self.env['slide.channel'].sudo()
        course = self.env['slide.channel']

        product_field = SlideChannel._fields.get('product_id')

        if product_field:
            if product_field.comodel_name == 'product.product':
                course = SlideChannel.search([
                    ('product_id', 'in', variant_ids),
                ], limit=1)

            elif product_field.comodel_name == 'product.template':
                course = SlideChannel.search([
                    ('product_id', '=', product_tmpl.id),
                ], limit=1)

        if course:
            return course

        product_template_field = SlideChannel._fields.get('product_template_id')

        if product_template_field:
            course = SlideChannel.search([
                ('product_template_id', '=', product_tmpl.id),
            ], limit=1)

        return course

    def _process_vla_tokens_if_needed(self):
        WalletLine = self.env['vla.token.wallet.line'].sudo()
        AssessmentToken = self.env['vla.assessment.token'].sudo()
        Transaction = self.env['vla.token.wallet.transaction'].sudo()

        for invoice in self.sudo():
            if invoice.vla_tokens_processed:
                continue

            if invoice.move_type != 'out_invoice':
                continue

            if invoice.state != 'posted':
                continue

            if invoice.payment_state not in ('paid', 'in_payment'):
                continue

            sources = invoice._get_vla_token_sources()

            if not sources:
                _logger.warning("VLA TOKENS: No token products found for invoice %s", invoice.name)
                continue

            sale_order = invoice._get_vla_related_sale_order()
            customer = invoice.partner_id
            wallet_owner = customer.commercial_partner_id or customer

            for source in sources:
                product = source['product']
                quantity = source['quantity']

                if quantity <= 0:
                    continue

                total_tokens = quantity * int(product.vla_token_qty or 0)
                duration = product.vla_token_duration

                if total_tokens <= 0:
                    continue

                if product.vla_get_effective_token_market() == 'b2b':
                    wallet_line = WalletLine.search([
                        ('partner_id', '=', wallet_owner.id),
                        ('duration', '=', duration),
                    ], limit=1)

                    if not wallet_line:
                        wallet_line = WalletLine.create({
                            'partner_id': wallet_owner.id,
                            'duration': duration,
                            'balance': 0,
                        })

                    wallet_line.write({
                        'balance': wallet_line.balance + total_tokens,
                    })

                    Transaction.create_from_wallet_line(
                        wallet_line=wallet_line,
                        amount=total_tokens,
                        reason='purchase',
                        invoice=invoice,
                        sale_order=sale_order if sale_order else None,
                        product=product,
                        note='B2B token purchase from invoice %s' % invoice.name,
                    )

                else:
                    course = invoice._vla_find_course_for_product(product)

                    existing_tokens = AssessmentToken.search([
                        ('token_type', '=', 'b2c'),
                        ('invoice_id', '=', invoice.id),
                        ('product_id', '=', product.id),
                        ('duration', '=', duration),
                    ])

                    if course and existing_tokens:
                        existing_tokens.filtered(lambda token: not token.channel_id).write({
                            'channel_id': course.id,
                        })

                    tokens_to_create = max(total_tokens - len(existing_tokens), 0)

                    for _idx in range(tokens_to_create):
                        assessment_token = AssessmentToken.create({
                            'token_type': 'b2c',
                            'partner_id': customer.id,
                            'company_partner_id': False,
                            'duration': duration,
                            'product_id': product.id,
                            'channel_id': course.id if course else False,
                            'sale_order_id': sale_order.id if sale_order else False,
                            'invoice_id': invoice.id,
                            'state': 'unused',
                        })

                        invoice._send_b2c_assessment_token_email(assessment_token)

            invoice.write({'vla_tokens_processed': True})

    def action_post(self):
        res = super().action_post()
        self._process_vla_tokens_if_needed()
        return res

    @api.model
    def _cron_process_vla_tokens(self):
        invoices = self.sudo().search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['paid', 'in_payment']),
            ('vla_tokens_processed', '=', False),
        ], limit=200)

        invoices._process_vla_tokens_if_needed()