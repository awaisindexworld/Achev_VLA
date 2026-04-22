from odoo import api, fields, models
from odoo.exceptions import UserError


class SlideChannelInvite(models.TransientModel):
    _inherit = 'slide.channel.invite'

    eligible_partner_ids = fields.Many2many(
        'res.partner', compute='_compute_eligible_partner_ids', string='Eligible Partners'
    )

    #####
    # @api.depends('channel_id')
    # def _compute_eligible_partner_ids(self):
    #     eligible = self.env['res.partner'].search([('current_job_position_id', '!=', False)])
    #     for wizard in self:
    #         wizard.eligible_partner_ids = eligible
    #         if wizard.partner_ids:
    #             wizard.partner_ids = wizard.partner_ids.filtered(lambda p: p.current_job_position_id)
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

    #####

    def action_invite(self):
        self.ensure_one()
        if not self.send_email:
            return super().action_invite()
        if not self.env.user.email:
            raise UserError("Unable to post message, please configure the sender's email address.")
        if not self.partner_ids:
            raise UserError("Please select at least one recipient.")

        partner_job_map = {partner.id: partner.current_job_position_id.id for partner in self.partner_ids if
                           partner.current_job_position_id}
        partner_ids = self.partner_ids.filtered(lambda p: p.current_job_position_id)
        if not partner_ids:
            raise UserError("Please select at least one recipient with a current job position.")

        attendees_to_reinvite = self.env['slide.channel.partner'].search([
            ('member_status', '=', 'invited'),
            ('channel_id', '=', self.channel_id.id),
            ('partner_id', 'in', partner_ids.ids),
            ('job_position_id', 'in', [jid for jid in partner_job_map.values() if jid]),
        ]) if not self.enroll_mode else self.env['slide.channel.partner']

        channel_partners = self.channel_id.with_context(vla_partner_job_map=partner_job_map)._action_add_members(
            partner_ids - attendees_to_reinvite.partner_id,
            member_status='joined' if self.enroll_mode else 'invited',
            raise_on_access=True,
        )

        if not self.enroll_mode:
            (attendees_to_reinvite | channel_partners).last_invitation_date = fields.Datetime.now()

        mail_values = []
        for channel_partner in (attendees_to_reinvite | channel_partners):
            mail_values.append(self._prepare_mail_values(channel_partner))
        self.env['mail.mail'].sudo().create(mail_values)

        return {'type': 'ir.actions.act_window_close'}
