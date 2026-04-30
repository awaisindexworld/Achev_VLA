from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    vla_token_wallet_line_ids = fields.One2many(
        'vla.token.wallet.line',
        'partner_id',
        string='VLA Token Wallet',
    )

    vla_assessment_token_ids = fields.One2many(
        'vla.assessment.token',
        'partner_id',
        string='B2C Assessment Tokens',
    )

    vla_token_transaction_ids = fields.One2many(
        'vla.token.wallet.transaction',
        'partner_id',
        string='VLA Token Transactions',
    )

    vla_token_30_count = fields.Integer(
        compute='_compute_vla_token_totals',
        string='30 Min Tokens',
    )

    vla_token_60_count = fields.Integer(
        compute='_compute_vla_token_totals',
        string='60 Min Tokens',
    )

    vla_token_total_count = fields.Integer(
        compute='_compute_vla_token_totals',
        string='Total Tokens',
    )

    @api.depends(
        'vla_token_wallet_line_ids.balance',
        'vla_token_wallet_line_ids.duration',
        'commercial_partner_id.vla_token_wallet_line_ids.balance',
        'commercial_partner_id.vla_token_wallet_line_ids.duration',
    )
    def _compute_vla_token_totals(self):
        """
        IMPORTANT:
        Do NOT resync invoices here.
        This compute must only display current wallet balance.
        Otherwise invite deductions will appear, then come back after refresh.
        """
        for partner in self:
            owner = partner.vla_get_wallet_owner()
            lines = owner.vla_token_wallet_line_ids

            partner.vla_token_30_count = sum(
                lines.filtered(lambda line: line.duration == '30').mapped('balance')
            )

            partner.vla_token_60_count = sum(
                lines.filtered(lambda line: line.duration == '60').mapped('balance')
            )

            partner.vla_token_total_count = (
                partner.vla_token_30_count + partner.vla_token_60_count
            )

    def vla_get_wallet_owner(self):
        self.ensure_one()
        return self.commercial_partner_id or self

    def vla_get_or_create_wallet_line(self, duration):
        self.ensure_one()

        owner = self.vla_get_wallet_owner()
        duration = str(duration)

        line = self.env['vla.token.wallet.line'].sudo().search([
            ('partner_id', '=', owner.id),
            ('duration', '=', duration),
        ], limit=1)

        if not line:
            line = self.env['vla.token.wallet.line'].sudo().create({
                'partner_id': owner.id,
                'duration': duration,
                'balance': 0,
            })

        return line

    def vla_check_tokens(self, duration, quantity=1):
        self.ensure_one()

        quantity = int(quantity or 1)
        line = self.vla_get_or_create_wallet_line(duration)

        return line.balance >= quantity

    def vla_consume_tokens(self, duration, quantity=1, source_record=None, note=None):
        self.ensure_one()

        quantity = int(quantity or 1)
        line = self.vla_get_or_create_wallet_line(duration)

        if line.balance < quantity:
            raise UserError(_(
                'You do not have enough %(duration)s-minute assessment tokens. '
                'Required: %(required)s, Available: %(available)s.',
                duration=duration,
                required=quantity,
                available=line.balance,
            ))

        return line.consume(
            quantity=quantity,
            source_record=source_record,
            note=note,
        )

    def action_vla_resync_tokens(self):
        """
        Manual rebuild from paid invoices.

        Important:
        Existing invite deductions are preserved.
        Without this, Resync/refresh can restore 50 after it was deducted to 49.
        """
        self.ensure_one()

        owner = self.vla_get_wallet_owner()

        old_deductions = {
            '30': 0,
            '60': 0,
        }

        for tx in owner.vla_token_transaction_ids.filtered(
            lambda t: t.reason == 'invite' and t.amount < 0
        ):
            old_deductions[tx.duration] += abs(tx.amount)

        invoices = self.env['account.move'].sudo().search([
            ('partner_id', 'child_of', owner.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['paid', 'in_payment']),
        ])

        invoices.write({'vla_tokens_processed': False})

        owner.vla_token_wallet_line_ids.unlink()
        owner.vla_token_transaction_ids.unlink()

        invoices._process_vla_tokens_if_needed()

        for duration, deduction_qty in old_deductions.items():
            if deduction_qty <= 0:
                continue

            wallet_line = owner.vla_get_or_create_wallet_line(duration)

            if wallet_line.balance >= deduction_qty:
                wallet_line.consume(
                    quantity=deduction_qty,
                    source_record=owner,
                    note='Preserved invite deductions after token resync',
                )
            else:
                available = wallet_line.balance
                wallet_line.write({'balance': 0})

                if available:
                    self.env['vla.token.wallet.transaction'].sudo().create_from_wallet_line(
                        wallet_line=wallet_line,
                        amount=-available,
                        reason='invite',
                        source_record=owner,
                        note='Partial preserved invite deduction after token resync',
                    )

        return True