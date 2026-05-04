# -*- coding: utf-8 -*-

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_post(self):
        res = super().action_post()

        # In Odoo 18, reconciliation updates payment_state on the invoice via
        # direct SQL — bypassing write() and _write() hooks on account.move.
        # The reliable hook point is here: after action_post() the payment has
        # been posted AND reconciled with its matching invoice(s).
        reconciled_invoices = self.reconciled_invoice_ids.filtered(
            lambda m: not m.vla_tokens_processed
        )

        _logger.info(
            "VLA TOKENS [account.payment.action_post] payment(s) %s posted | "
            "reconciled_invoice_ids=%s | unprocessed=%s",
            self.ids,
            self.reconciled_invoice_ids.ids,
            reconciled_invoices.ids,
        )

        if reconciled_invoices:
            reconciled_invoices._process_vla_tokens_if_needed()

        return res
