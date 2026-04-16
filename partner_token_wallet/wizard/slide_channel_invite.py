from odoo import models, _
from odoo.exceptions import UserError


class SlideChannelInvite(models.TransientModel):
    _inherit = 'slide.channel.invite'

    def action_invite(self):
        self.ensure_one()
        product = self.channel_id.product_id

        if product:
            partner = self.env.user.partner_id
            recipient_count = len(self.partner_ids)

            wallet_line = self.env['token.wallet.line'].search([
                ('partner_id', '=', partner.id),
                ('product_id', '=', product.id),
            ], limit=1)

            if not wallet_line or wallet_line.token_count < recipient_count:
                raise UserError(_(
                    "You need at least %d token(s) for product '%s' to invite %d recipient(s). "
                    "Current balance: %d token(s).",
                    recipient_count,
                    product.display_name,
                    recipient_count,
                    wallet_line.token_count if wallet_line else 0,
                ))

            wallet_line.token_count -= recipient_count

        return super().action_invite()
