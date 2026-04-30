# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import UserError


class SlideChannelInvite(models.TransientModel):
    _inherit = 'slide.channel.invite'

    def _vla_get_course_token_product(self):
        self.ensure_one()

        product = self.channel_id.product_id

        if not product:
            return False

        if product._name == 'product.template':
            variant = product.product_variant_ids.filtered(
                lambda p: p.vla_is_token_product and p.vla_token_duration
            )[:1]

            if variant:
                return variant

            return product.product_variant_id

        return product

    def _vla_get_invite_recipient_count(self):
        self.ensure_one()

        count = 0

        if hasattr(self, 'partner_ids') and self.partner_ids:
            count += len(self.partner_ids)

        if hasattr(self, 'emails') and self.emails:
            emails = self.emails.replace('\n', ',').split(',')
            count += len([email for email in emails if email.strip()])

        return count or 1

    def action_invite(self):
        self.ensure_one()

        product = self._vla_get_course_token_product()

        if not product or not product.vla_is_token_product or not product.vla_token_duration:
            return super().action_invite()

        duration = str(product.vla_token_duration)
        recipient_count = self._vla_get_invite_recipient_count()

        wallet_owner = self.env.user.partner_id.vla_get_wallet_owner()
        wallet_line = wallet_owner.vla_get_or_create_wallet_line(duration)

        if wallet_line.balance < recipient_count:
            raise UserError(_(
                'You do not have enough %(duration)s-minute tokens to send this invite.\n\n'
                'Required: %(required)s\n'
                'Available: %(available)s',
                duration=duration,
                required=recipient_count,
                available=wallet_line.balance,
            ))

        result = super().action_invite()

        wallet_line.consume(
            quantity=recipient_count,
            source_record=self.channel_id,
            note='Invite sent for course: %s' % self.channel_id.display_name,
        )

        return result