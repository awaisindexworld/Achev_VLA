# -*- coding: utf-8 -*-

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_post(self):
        res = super().action_post()

        # NOTE: In Odoo 18 reconciliation happens AFTER action_post() returns,
        # so reconciled_invoice_ids is always empty here. Token processing for
        # the manual payment flow is handled in wizard/account_payment_register.py
        # via action_create_payments() which fires after full reconciliation.
        #
        # This hook is kept only as a safety net for programmatic payment posting
        # flows where reconciliation might be done before action_post() returns.
        reconciled_invoices = self.reconciled_invoice_ids.filtered(
            lambda m: not m.vla_tokens_processed
        )

        _logger.info(
            "VLA TOKENS [account.payment.action_post] payment(s) %s posted | "
            "reconciled_invoice_ids=%s (empty is expected for manual payment flow)",
            self.ids,
            reconciled_invoices.ids,
        )

        if reconciled_invoices:
            reconciled_invoices._process_vla_tokens_if_needed()

        return res
