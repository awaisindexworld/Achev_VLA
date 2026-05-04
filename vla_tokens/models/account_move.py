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
            _logger.info(
                "VLA TOKENS [_get_vla_token_sources] invoice=%s | line product=%s (id=%s) | "
                "vla_is_token_product=%s | vla_token_duration=%s | vla_token_qty=%s",
                self.name, product.display_name, product.id,
                product.vla_is_token_product, product.vla_token_duration, product.vla_token_qty,
            )
            if product.vla_is_token_product and product.vla_token_duration and product.vla_token_qty > 0:
                sources.append({
                    'product': product,
                    'quantity': int(line.quantity or 0),
                })

        if sources:
            _logger.info(
                "VLA TOKENS [_get_vla_token_sources] invoice=%s | found %s source(s) from invoice lines.",
                self.name, len(sources),
            )
            return sources

        _logger.info(
            "VLA TOKENS [_get_vla_token_sources] invoice=%s | no token lines on invoice, checking sale order.",
            self.name,
        )

        sale_order = self._get_vla_related_sale_order()

        if sale_order:
            for line in sale_order.order_line.filtered(lambda l: l.product_id):
                product = line.product_id
                _logger.info(
                    "VLA TOKENS [_get_vla_token_sources] sale order fallback | product=%s (id=%s) | "
                    "vla_is_token_product=%s | vla_token_duration=%s | vla_token_qty=%s",
                    product.display_name, product.id,
                    product.vla_is_token_product, product.vla_token_duration, product.vla_token_qty,
                )
                if product.vla_is_token_product and product.vla_token_duration and product.vla_token_qty > 0:
                    sources.append({
                        'product': product,
                        'quantity': int(line.product_uom_qty or 0),
                    })
        else:
            _logger.info(
                "VLA TOKENS [_get_vla_token_sources] invoice=%s | no related sale order found (invoice_origin=%s).",
                self.name, self.invoice_origin,
            )

        return sources

    def _send_b2c_assessment_token_email(self, assessment_token):
        _logger.info(
            "VLA TOKENS [_send_b2c_assessment_token_email] token=%s | partner=%s | email=%s | candidate_email=%s",
            assessment_token.name,
            assessment_token.partner_id.display_name,
            assessment_token.partner_id.email,
            assessment_token.candidate_email,
        )

        if self.env.context.get('vla_skip_b2c_email'):
            _logger.info("VLA TOKENS [_send_b2c_assessment_token_email] skipped via context flag.")
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
                "VLA TOKENS: B2C assessment token %s has no recipient email — email NOT sent.",
                assessment_token.display_name,
            )
            return False

        try:
            template.sudo().send_mail(assessment_token.id, force_send=True)
            _logger.info(
                "VLA TOKENS [_send_b2c_assessment_token_email] email sent successfully for token=%s to %s",
                assessment_token.name,
                assessment_token.partner_id.email or assessment_token.candidate_email,
            )
        except Exception as e:
            _logger.error(
                "VLA TOKENS [_send_b2c_assessment_token_email] FAILED to send email for token=%s | error: %s",
                assessment_token.name, str(e),
            )
            return False

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

        _logger.info(
            "VLA TOKENS [_process_vla_tokens_if_needed] called on %s record(s): %s",
            len(self), self.ids,
        )

        for invoice in self.sudo():
            _logger.info(
                "VLA TOKENS [_process_vla_tokens_if_needed] checking invoice id=%s name=%s | "
                "move_type=%s | state=%s | payment_state=%s | vla_tokens_processed=%s",
                invoice.id, invoice.name,
                invoice.move_type, invoice.state,
                invoice.payment_state, invoice.vla_tokens_processed,
            )

            if invoice.vla_tokens_processed:
                _logger.info("VLA TOKENS: invoice %s already processed — skipping.", invoice.name)
                continue

            if invoice.move_type != 'out_invoice':
                _logger.info("VLA TOKENS: invoice %s skipped — move_type=%s (not out_invoice).", invoice.name, invoice.move_type)
                continue

            if invoice.state != 'posted':
                _logger.info("VLA TOKENS: invoice %s skipped — state=%s (not posted).", invoice.name, invoice.state)
                continue

            if invoice.payment_state not in ('paid', 'in_payment'):
                _logger.info(
                    "VLA TOKENS: invoice %s skipped — payment_state=%s (not paid/in_payment).",
                    invoice.name, invoice.payment_state,
                )
                continue

            sources = invoice._get_vla_token_sources()

            if not sources:
                _logger.warning("VLA TOKENS: No token products found for invoice %s — skipping.", invoice.name)
                continue

            sale_order = invoice._get_vla_related_sale_order()
            customer = invoice.partner_id
            wallet_owner = customer.commercial_partner_id or customer

            _logger.info(
                "VLA TOKENS: processing invoice %s | customer=%s | wallet_owner=%s | sale_order=%s | sources=%s",
                invoice.name, customer.display_name, wallet_owner.display_name,
                sale_order.name if sale_order else 'None', len(sources),
            )

            for source in sources:
                product = source['product']
                quantity = source['quantity']

                if quantity <= 0:
                    _logger.info("VLA TOKENS: product %s has quantity=%s — skipping.", product.display_name, quantity)
                    continue

                total_tokens = quantity * int(product.vla_token_qty or 0)
                duration = product.vla_token_duration
                market = product.vla_get_effective_token_market()

                _logger.info(
                    "VLA TOKENS: source product=%s | qty=%s | token_qty=%s | total_tokens=%s | duration=%s | market=%s",
                    product.display_name, quantity, product.vla_token_qty, total_tokens, duration, market,
                )

                if total_tokens <= 0:
                    _logger.info("VLA TOKENS: total_tokens=%s for product %s — skipping.", total_tokens, product.display_name)
                    continue

                if market == 'b2b':
                    _logger.info("VLA TOKENS: B2B path — crediting wallet for %s tokens (%s min).", total_tokens, duration)

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
                    _logger.info("VLA TOKENS: B2C path — creating assessment token(s) and sending email.")

                    course = invoice._vla_find_course_for_product(product)
                    _logger.info(
                        "VLA TOKENS: course lookup for product %s → %s",
                        product.display_name, course.display_name if course else 'None (no course linked)',
                    )

                    existing_tokens = AssessmentToken.search([
                        ('token_type', '=', 'b2c'),
                        ('invoice_id', '=', invoice.id),
                        ('product_id', '=', product.id),
                        ('duration', '=', duration),
                    ])

                    _logger.info(
                        "VLA TOKENS: existing tokens for this invoice/product/duration: %s",
                        len(existing_tokens),
                    )

                    if course and existing_tokens:
                        existing_tokens.filtered(lambda token: not token.channel_id).write({
                            'channel_id': course.id,
                        })

                    tokens_to_create = max(total_tokens - len(existing_tokens), 0)
                    _logger.info("VLA TOKENS: tokens_to_create=%s", tokens_to_create)

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

                        _logger.info(
                            "VLA TOKENS: created assessment token %s (code=%s) — sending email.",
                            assessment_token.name, assessment_token.token_code,
                        )

                        invoice._send_b2c_assessment_token_email(assessment_token)

            invoice.write({'vla_tokens_processed': True})
            _logger.info("VLA TOKENS: invoice %s marked as vla_tokens_processed=True.", invoice.name)

    # ---------------------------------------------------------------------------
    # Hooks — trigger processing as soon as invoice is paid
    # ---------------------------------------------------------------------------

    def write(self, vals):
        res = super().write(vals)
        # payment_state may be written explicitly in some flows (e.g. direct write)
        if vals.get('payment_state') in ('paid', 'in_payment'):
            _logger.info(
                "VLA TOKENS [write hook] payment_state=%s detected on %s — triggering processing.",
                vals['payment_state'], self.ids,
            )
            self._process_vla_tokens_if_needed()
        return res

    def _write(self, vals):
        # payment_state is a stored computed field; Odoo recomputes it via _write()
        # (low-level path that bypasses write()). We hook here to catch it.
        res = super()._write(vals)
        if vals.get('payment_state') in ('paid', 'in_payment'):
            _logger.info(
                "VLA TOKENS [_write hook] payment_state=%s detected on %s — triggering processing.",
                vals['payment_state'], self.ids,
            )
            self._process_vla_tokens_if_needed()
        return res

    def action_post(self):
        res = super().action_post()
        # Handles edge case where invoice is already paid at the time of posting
        # (e.g. free products, or payment registered before posting)
        self._process_vla_tokens_if_needed()
        return res

    # Cron method disabled: token processing is now handled immediately via the
    # write() / _write() hooks above when payment_state transitions to 'paid' or 'in_payment'.
    # @api.model
    # def _cron_process_vla_tokens(self):
    #     invoices = self.sudo().search([
    #         ('move_type', '=', 'out_invoice'),
    #         ('state', '=', 'posted'),
    #         ('payment_state', 'in', ['paid', 'in_payment']),
    #         ('vla_tokens_processed', '=', False),
    #     ], limit=200)
    #
    #     invoices._process_vla_tokens_if_needed()
