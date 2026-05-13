from odoo import api, fields, models
from odoo.exceptions import UserError


class SlideChannelInvite(models.TransientModel):
    _inherit = 'slide.channel.invite'

    eligible_partner_ids = fields.Many2many(
        'res.partner', compute='_compute_eligible_partner_ids', string='Eligible Partners'
    )

    @api.depends('channel_id')
    def _compute_eligible_partner_ids(self):
        for wizard in self:
            domain = [('current_job_position_id', '!=', False)]
            if wizard.channel_id.company_id:
                domain.append(('current_job_position_id.company_id', '=', wizard.channel_id.company_id.id))
            eligible = self.env['res.partner'].search(domain)
            wizard.eligible_partner_ids = eligible
            if wizard.partner_ids:
                wizard.partner_ids = wizard.partner_ids.filtered(
                    lambda p: p.current_job_position_id
                              and p.current_job_position_id.company_id == wizard.channel_id.company_id
                )

    def _sync_partner_company_to_user(self, partners):
        """
        For every partner that already has a user account, push the partner's
        company_id onto the user as both the default company (company_id) and
        an allowed company (company_ids).  Called AFTER _action_add_members so
        that users which were just created by that call are also covered.
        """
        for partner in partners:
            partner_company = partner.sudo().company_id
            if not partner_company:
                continue
            for user in partner.sudo().user_ids:
                write_vals = {}
                if partner_company.id not in user.company_ids.ids:
                    write_vals['company_ids'] = [(4, partner_company.id)]
                if user.company_id.id != partner_company.id:
                    write_vals['company_id'] = partner_company.id
                if write_vals:
                    user.sudo().write(write_vals)

    def action_invite(self):
        self.ensure_one()

        if self.partner_ids:
            for partner in self.partner_ids:
                # Preserve whatever company the admin set on the contact form.
                # Only assign the current operating company as a fallback when
                # the partner has no company set yet.
                if not partner.sudo().company_id:
                    partner.sudo().write({'company_id': self.env.company.id})

        # send_email=False path: let super() handle the full invite, then sync.
        if not self.send_email:
            result = super().action_invite()
            # Users may have been created inside super(); sync company now.
            self._sync_partner_company_to_user(self.partner_ids)
            return result

        if not self.env.user.email:
            raise UserError("Unable to post message, please configure the sender's email address.")
        if not self.partner_ids:
            raise UserError("Please select at least one recipient.")

        if hasattr(self, '_vla_check_invite_token_balance'):
            self._vla_check_invite_token_balance()

        partner_job_map = {
            partner.id: partner.current_job_position_id.id
            for partner in self.partner_ids
            if partner.current_job_position_id
        }
        partner_ids = self.partner_ids.filtered(lambda p: p.current_job_position_id)
        if not partner_ids:
            raise UserError("Please select at least one recipient with a current job position.")

        attendees_to_reinvite = self.env['slide.channel.partner'].sudo().search([
            ('member_status', '=', 'invited'),
            ('channel_id', '=', self.channel_id.id),
            ('partner_id', 'in', partner_ids.ids),
            ('job_position_id', 'in', [jid for jid in partner_job_map.values() if jid]),
        ]) if not self.enroll_mode else self.env['slide.channel.partner']

        channel_partners = self.channel_id.with_context(
            vla_partner_job_map=partner_job_map
        )._action_add_members(
            partner_ids - attendees_to_reinvite.partner_id,
            member_status='joined' if self.enroll_mode else 'invited',
            raise_on_access=True,
        )

        # ------------------------------------------------------------------ #
        # Sync company to users HERE – after _action_add_members, because    #
        # that call may have just created the portal user for this partner.   #
        # Also covers partners that already had a user before the invite.     #
        # ------------------------------------------------------------------ #
        self._sync_partner_company_to_user(self.partner_ids)

        if not self.enroll_mode:
            (attendees_to_reinvite | channel_partners).sudo().write({
                'last_invitation_date': fields.Datetime.now()
            })

        mail_values = []
        for channel_partner in (attendees_to_reinvite | channel_partners):
            mail_values.append(self._prepare_mail_values(channel_partner))
        self.env['mail.mail'].sudo().create(mail_values)

        if hasattr(self, '_vla_consume_invite_tokens'):
            self._vla_consume_invite_tokens()

        return {'type': 'ir.actions.act_window_close'}