from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    token_wallet_processed = fields.Boolean(copy=False, default=False)
