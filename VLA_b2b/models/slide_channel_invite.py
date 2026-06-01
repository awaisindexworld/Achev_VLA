from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SlideChannelInvite(models.TransientModel):
    _inherit = 'slide.channel.invite'

    eligible_partner_ids = fields.Many2many(
        'res.partner',
        compute='_compute_eligible_partner_ids',
        string='Eligible Partners',
    )

    def _vla_get_invite_companies(self):
        """
        Companies selected in the Odoo multi-company switcher.

        If user selected:
        - YourCompany only: show YourCompany job-position attendees.
        - YourCompany + Element: show attendees from both job-position companies.
        - All companies: show attendees from all selected companies.
        """
        self.ensure_one()

        companies = self.env.companies
        if not companies:
            companies = self.env.company

        return companies

    def _vla_eligible_partner_domain(self):
        """
        Invite dropdown should depend on current job position company,
        not only on partner/contact company.
        """
        self.ensure_one()

        selected_companies = self._vla_get_invite_companies()

        return [
            ('current_job_position_id', '!=', False),
            ('current_job_position_id.state', '=', 'posted'),
            ('current_job_position_id.company_id', 'in', selected_companies.ids),
        ]

    def _vla_is_partner_valid_for_selected_companies(self, partner, selected_companies):
        """
        Final Python validation.

        Rule:
        The attendee is valid if their current job position company is one
        of the companies selected in the Odoo company switcher.
        """
        job = partner.sudo().current_job_position_id

        if not job:
            return False

        if job.state != 'posted':
            return False

        if not job.company_id:
            return False

        if job.company_id.id not in selected_companies.ids:
            return False

        return True

    @api.depends('channel_id', 'channel_id.company_id')
    @api.depends_context('allowed_company_ids')
    def _compute_eligible_partner_ids(self):
        Partner = self.env['res.partner'].sudo()

        for wizard in self:
            selected_companies = wizard._vla_get_invite_companies()

            partners = Partner.search(
                wizard._vla_eligible_partner_domain()
            ).filtered(
                lambda partner: wizard._vla_is_partner_valid_for_selected_companies(
                    partner,
                    selected_companies,
                )
            )

            wizard.eligible_partner_ids = partners

    @api.onchange('channel_id', 'partner_ids')
    def _onchange_vla_filter_partner_ids(self):
        """
        Remove already-selected recipients if they no longer match
        the currently selected companies.
        """
        for wizard in self:
            if wizard.partner_ids:
                wizard.partner_ids = wizard.partner_ids & wizard.eligible_partner_ids

    def _vla_get_invalid_partners(self):
        self.ensure_one()

        selected_companies = self._vla_get_invite_companies()
        invalid_partners = self.env['res.partner']

        for partner in self.partner_ids:
            if not self._vla_is_partner_valid_for_selected_companies(
                partner,
                selected_companies,
            ):
                invalid_partners |= partner

        return invalid_partners

    def _vla_validate_invite_partners(self):
        self.ensure_one()

        invalid_partners = self._vla_get_invalid_partners()
        if not invalid_partners:
            return

        selected_companies = self._vla_get_invite_companies()
        company_names = ', '.join(selected_companies.mapped('display_name'))

        lines = []

        for partner in invalid_partners:
            job = partner.sudo().current_job_position_id

            lines.append(_(
                '- %(partner)s | Contact Company: %(partner_company)s | '
                'Current Job Position: %(job)s | Job Position Company: %(job_company)s',
                partner=partner.display_name,
                partner_company=partner.sudo().company_id.display_name or _('No Company'),
                job=job.display_name if job else _('No Current Job Position'),
                job_company=job.company_id.display_name if job and job.company_id else _('No Company'),
            ))

        raise UserError(_(
            'You can only invite attendees whose current job position company '
            'is one of the selected companies: %(companies)s.\n\n'
            'Invalid recipient(s):\n%(lines)s',
            companies=company_names,
            lines='\n'.join(lines),
        ))

    def _vla_get_partner_target_company(self, partner):
        """
        If contact has no company, assign the company from the current job position.
        Existing contact company is not overwritten.
        """
        self.ensure_one()

        selected_companies = self._vla_get_invite_companies()
        job = partner.sudo().current_job_position_id

        if job and job.company_id and job.company_id.id in selected_companies.ids:
            return job.company_id

        if len(selected_companies) == 1:
            return selected_companies

        return self.env['res.company']

    def _sync_partner_company_to_user(self, partners):
        """
        For every partner that already has a user account, push the partner's
        company_id onto the user as both the default company and an allowed company.
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

    def _vla_prepare_partner_job_map(self):
        self.ensure_one()

        return {
            partner.id: partner.sudo().current_job_position_id.id
            for partner in self.partner_ids
            if partner.sudo().current_job_position_id
        }

    def action_invite(self):
        self.ensure_one()

        if self.partner_ids:
            for partner in self.partner_ids:
                if not partner.sudo().company_id:
                    target_company = self._vla_get_partner_target_company(partner)

                    if target_company:
                        partner.sudo().write({
                            'company_id': target_company.id,
                        })

        self._vla_validate_invite_partners()

        if not self.send_email:
            if not self.partner_ids:
                raise UserError(_('Please select at least one recipient.'))

            partner_job_map = self._vla_prepare_partner_job_map()

            partner_ids = self.partner_ids.filtered(
                lambda partner: partner.sudo().current_job_position_id
            )

            if not partner_ids:
                raise UserError(_('Please select at least one recipient with a current job position.'))

            self.channel_id.with_context(
                vla_partner_job_map=partner_job_map,
            )._action_add_members(
                partner_ids,
                member_status='joined' if self.enroll_mode else 'invited',
                raise_on_access=True,
            )

            self._sync_partner_company_to_user(partner_ids)

            return {
                'type': 'ir.actions.act_window_close',
            }

        if not self.env.user.email:
            raise UserError(_("Unable to post message, please configure the sender's email address."))

        if not self.partner_ids:
            raise UserError(_('Please select at least one recipient.'))

        if hasattr(self, '_vla_check_invite_token_balance'):
            self._vla_check_invite_token_balance()

        partner_job_map = self._vla_prepare_partner_job_map()

        partner_ids = self.partner_ids.filtered(
            lambda partner: partner.sudo().current_job_position_id
        )

        if not partner_ids:
            raise UserError(_('Please select at least one recipient with a current job position.'))

        attendees_to_reinvite = self.env['slide.channel.partner']

        if not self.enroll_mode:
            attendees_to_reinvite = self.env['slide.channel.partner'].sudo().search([
                ('member_status', '=', 'invited'),
                ('channel_id', '=', self.channel_id.id),
                ('partner_id', 'in', partner_ids.ids),
                ('job_position_id', 'in', [
                    job_id for job_id in partner_job_map.values() if job_id
                ]),
            ])

        channel_partners = self.channel_id.with_context(
            vla_partner_job_map=partner_job_map,
        )._action_add_members(
            partner_ids - attendees_to_reinvite.partner_id,
            member_status='joined' if self.enroll_mode else 'invited',
            raise_on_access=True,
        )

        self._sync_partner_company_to_user(self.partner_ids)

        if not self.enroll_mode:
            (attendees_to_reinvite | channel_partners).sudo().write({
                'last_invitation_date': fields.Datetime.now(),
            })

        mail_values = []

        for channel_partner in attendees_to_reinvite | channel_partners:
            mail_values.append(
                self._prepare_mail_values(channel_partner)
            )

        self.env['mail.mail'].sudo().create(mail_values)

        if hasattr(self, '_vla_consume_invite_tokens'):
            self._vla_consume_invite_tokens()

        return {
            'type': 'ir.actions.act_window_close',
        }