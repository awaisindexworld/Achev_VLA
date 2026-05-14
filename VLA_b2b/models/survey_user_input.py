from odoo import api, fields, models, _


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    channel_id = fields.Many2one('slide.channel', string='Course', readonly=True, index=True)
    slide_channel_partner_id = fields.Many2one('slide.channel.partner', string='Attendee Attempt', readonly=True, index=True)
    job_position_id = fields.Many2one('vla.job.position', string='Job Position Snapshot', readonly=True, index=True)
    assessment_skill_type = fields.Selection(
        related='survey_id.assessment_skill_type',
        string='Skill',
        store=True,
        readonly=True
    )
    assessment_final_status = fields.Selection([
        ('pending', 'Pending'),
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('error', 'Error'),
    ], string='Assessment Status', default='pending', readonly=True)
    evaluated_at = fields.Datetime(readonly=True)
    failure_reason = fields.Text(readonly=True)

    company_id = fields.Many2one(
        'res.company',
        related='channel_id.company_id',
        store=True,
        readonly=True,
        index=True,
    )

    def _vla_guess_channel(self):
        self.ensure_one()

        if self.channel_id or not self.survey_id:
            return self.channel_id

        slides = self.env['slide.slide'].sudo().search([
            ('survey_id', '=', self.survey_id.id)
        ])

        channels = slides.mapped('channel_id')

        return channels[:1]

    def _vla_guess_attendee(self):
        self.ensure_one()

        if not self.partner_id:
            return self.env['slide.channel.partner']

        channel = self.channel_id or self._vla_guess_channel()

        if channel:
            domain = [
                ('channel_id', '=', channel.id),
                ('partner_id', '=', self.partner_id.id)
            ]

            attendees = self.env['slide.channel.partner'].sudo().search(
                domain,
                order='id desc'
            )

            if self.job_position_id:
                matched = attendees.filtered(
                    lambda a: a.job_position_id.id == self.job_position_id.id
                )
                if matched:
                    attendees = matched

            if attendees:
                return attendees[:1]

        # Fallback for surveys not embedded in any course slide
        skill = getattr(self.survey_id, 'assessment_skill_type', None)

        if skill:
            attendees = self.env['slide.channel.partner'].sudo().search(
                [('partner_id', '=', self.partner_id.id)],
                order='id desc'
            )

            if self.job_position_id:
                matched = attendees.filtered(
                    lambda a: a.job_position_id.id == self.job_position_id.id
                )
                if matched:
                    attendees = matched

            for attendee in attendees:
                has_skill = any(
                    s.survey_id and s.survey_id.assessment_skill_type == skill
                    for s in attendee.channel_id.slide_ids
                )

                if has_skill:
                    return attendee

        return self.env['slide.channel.partner']

    def _vla_sync_context(self):
        for user_input in self:
            vals = {}

            channel = user_input.channel_id or user_input._vla_guess_channel()

            if channel and not user_input.channel_id:
                vals['channel_id'] = channel.id

            attendee = (
                user_input.slide_channel_partner_id
                or user_input._vla_guess_attendee()
            )

            if attendee:
                if not user_input.slide_channel_partner_id:
                    vals['slide_channel_partner_id'] = attendee.id

                if (
                    not user_input.job_position_id
                    and attendee.job_position_id
                ):
                    vals['job_position_id'] = attendee.job_position_id.id

            if vals:
                user_input.sudo().write(vals)

    def _vla_sync_assessment_status(self):
        for user_input in self:
            if (
                user_input.state != 'done'
                or not user_input.survey_id.assessment_skill_type
            ):
                continue

            skill_type = user_input.survey_id.assessment_skill_type

            threshold = 0

            if user_input.job_position_id:
                threshold = user_input.job_position_id[
                    f"{skill_type}_min_clb"
                ]

            # Writing/Speaking CLB from survey input
            # Reading/Listening CLB from attendee
            if skill_type in ('writing', 'speaking'):
                clb = getattr(
                    user_input,
                    f'{skill_type}_clb',
                    0
                ) or 0
            else:
                attendee = (
                    user_input.slide_channel_partner_id
                    or user_input._vla_guess_attendee()
                )

                clb = int(
                    attendee[f'{skill_type}_clb'] or 0
                ) if attendee else 0

            if not clb:
                status = 'pending'
                failure = False
                evaluated = False
            else:
                status = 'pass' if clb >= threshold else 'fail'

                failure = (
                    False
                    if status == 'pass'
                    else _(
                        '%(skill)s CLB %(clb)s is below minimum %(threshold)s',
                        skill=skill_type.title(),
                        clb=('%g' % clb),
                        threshold=('%g' % threshold),
                    )
                )

                evaluated = fields.Datetime.now()

            super(SurveyUserInput, user_input).write({
                'assessment_final_status': status,
                'evaluated_at': evaluated,
                'failure_reason': failure,
            })

            # Write score to attendee
            attendee = user_input.slide_channel_partner_id

            if not attendee:
                user_input._vla_sync_context()
                attendee = user_input.slide_channel_partner_id

            if attendee:
                attendee.sudo().write({
                    f'{skill_type}_score': user_input.scoring_total
                })

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        records._vla_sync_context()
        records._vla_sync_assessment_status()

        return records

    def write(self, vals):
        res = super().write(vals)

        trigger_fields = {
            'state',
            'scoring_total',
            'survey_id',
            'partner_id',
            'channel_id',
            'job_position_id',
            'writing_clb',
            'speaking_clb',
        }

        if trigger_fields.intersection(vals):
            self._vla_sync_context()
            self._vla_sync_assessment_status()

        return res

    def _mark_done(self):
        res = super()._mark_done()

        self._vla_sync_context()
        self._vla_sync_assessment_status()

        return res