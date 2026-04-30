from odoo import api, fields, models, _
from odoo.exceptions import UserError


class VlaTokenWalletLine(models.Model):
    _name = 'vla.token.wallet.line'
    _description = 'VLA Token Wallet Line'
    _order = 'partner_id, duration'

    _sql_constraints = [
        (
            'partner_duration_unique',
            'unique(partner_id, duration)',
            'A partner can only have one wallet line per duration.',
        ),
    ]

    partner_id = fields.Many2one(
        'res.partner',
        required=True,
        ondelete='cascade',
        index=True,
    )

    duration = fields.Selection(
        selection=[
            ('30', '30 Minutes'),
            ('60', '60 Minutes'),
        ],
        required=True,
        index=True,
    )

    balance = fields.Integer(
        string='Available Tokens',
        default=0,
        required=True,
    )

    duration_label = fields.Char(
        compute='_compute_duration_label',
        string='Duration Label',
    )

    @api.depends('duration')
    def _compute_duration_label(self):
        labels = dict(self._fields['duration'].selection)
        for line in self:
            line.duration_label = labels.get(line.duration, '')

    def consume(self, quantity=1, source_record=None, note=None):
        self.ensure_one()

        quantity = int(quantity or 0)

        if quantity <= 0:
            return False

        if self.balance < quantity:
            raise UserError(_(
                'Not enough %(duration)s tokens. Required: %(required)s, Available: %(available)s.',
                duration=self.duration_label,
                required=quantity,
                available=self.balance,
            ))

        new_balance = self.balance - quantity

        self.sudo().write({
            'balance': new_balance,
        })

        self.env['vla.token.wallet.transaction'].sudo().create_from_wallet_line(
            wallet_line=self,
            amount=-quantity,
            reason='invite',
            source_record=source_record,
            note=note,
        )

        return True