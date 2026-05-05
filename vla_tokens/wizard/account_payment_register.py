# -*- coding: utf-8 -*-

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def action_create_payments(self):
        # Resolve the invoices BEFORE the super call using self.line_ids.move_id.
        # This is reliable regardless of what active_model/active_ids are in the
        # context — Odoo 18 passes account.move.line IDs, not account.move IDs.
        invoices = self.line_ids.move_id.filtered(
            lambda m: m.move_type == 'out_invoice' and not m.vla_tokens_processed
        )

        _logger.info(
            "VLA TOKENS [AccountPaymentRegister.action_create_payments] "
            "invoices to process after payment: %s (ids=%s)",
            invoices.mapped('name'), invoices.ids,
        )

        res = super().action_create_payments()

        # By the time super() returns, posting AND reconciliation are complete.
        # payment_state on the invoices is now 'paid' or 'in_payment'.
        if invoices:
            _logger.info(
                "VLA TOKENS [AccountPaymentRegister.action_create_payments] "
                "post-payment states: %s",
                {inv.name: inv.payment_state for inv in invoices},
            )
            invoices._process_vla_tokens_if_needed()

        return res
