# -*- coding: utf-8 -*-

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def action_create_payments(self):
        # Capture the invoice IDs being paid BEFORE the super call.
        # active_ids in context = the account.move records that were open
        # when "Register Payment" was clicked.
        active_model = self._context.get('active_model', '')
        active_ids = self._context.get('active_ids', [])

        _logger.info(
            "VLA TOKENS [AccountPaymentRegister.action_create_payments] "
            "active_model=%s | active_ids=%s",
            active_model, active_ids,
        )

        res = super().action_create_payments()

        # By the time super() returns, payment posting AND reconciliation are
        # complete. payment_state on the invoices is now 'paid'/'in_payment'.
        if active_model == 'account.move' and active_ids:
            invoices = self.env['account.move'].sudo().browse(active_ids)
            _logger.info(
                "VLA TOKENS [AccountPaymentRegister.action_create_payments] "
                "post-payment: checking invoice(s) %s — payment_state(s): %s",
                invoices.mapped('name'),
                invoices.mapped('payment_state'),
            )
            invoices._process_vla_tokens_if_needed()

        return res
