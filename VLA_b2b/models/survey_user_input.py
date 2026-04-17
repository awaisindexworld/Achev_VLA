from odoo import api, fields, models, _


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    channel_id = fields.Many2one('slide.channel', string='Course', readonly=True, index=True)
    slide_channel_partner_id = fields.Many2one('slide.channel.partner', string='Attendee Attempt', readonly=True, index=True)
    job_position_id = fields.Many2one('vla.job.position', string='Job Position Snapshot', readonly=True, index=True)
    assessment_skill_type = fields.Selection(related='survey_id.assessment_skill_type', string='Skill', store=True, readonly=True)
    assessment_final_status = fields.Selection([
        ('pending', 'Pending'),
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('error', 'Error'),
    ], string='Assessment Status', default='pending', readonly=True)
    evaluated_at = fields.Datetime(readonly=True)
    failure_reason = fields.Text(readonly=True)

    def _vla_guess_channel(self):
        self.ensure_one()
        if self.channel_id or not self.survey_id:
            return self.channel_id
        slides = self.env['slide.slide'].sudo().search([('survey_id', '=', self.survey_id.id)])
        channels = slides.mapped('channel_id')
        return channels[:1]

    def _vla_guess_attendee(self):
        self.ensure_one()
        channel = self.channel_id or self._vla_guess_channel()
        if not channel or not self.partner_id:
            return self.env['slide.channel.partner']
        domain = [('channel_id', '=', channel.id), ('partner_id', '=', self.partner_id.id)]
        attendees = self.env['slide.channel.partner'].sudo().search(domain, order='id desc')
        if self.job_position_id:
            matched = attendees.filtered(lambda a: a.job_position_id.id == self.job_position_id.id)
            if matched:
                attendees = matched
        return attendees[:1]

    def _vla_sync_context(self):
        for user_input in self:
            vals = {}
            channel = user_input.channel_id or user_input._vla_guess_channel()
            if channel and not user_input.channel_id:
                vals['channel_id'] = channel.id
            attendee = user_input.slide_channel_partner_id or user_input._vla_guess_attendee()
            if attendee:
                if not user_input.slide_channel_partner_id:
                    vals['slide_channel_partner_id'] = attendee.id
                if not user_input.job_position_id and attendee.job_position_id:
                    vals['job_position_id'] = attendee.job_position_id.id
            if vals:
                super(SurveyUserInput, user_input).write(vals)

    def _vla_sync_assessment_status(self):
        for user_input in self:
            if user_input.state != 'done' or not user_input.survey_id.assessment_skill_type:
                continue
            threshold = 0.0
            if user_input.job_position_id:
                threshold = user_input.job_position_id[f"{user_input.survey_id.assessment_skill_type}_min_score"]
            status = 'pass' if user_input.scoring_total >= threshold else 'fail'
            vals = {
                'assessment_final_status': status,
                'evaluated_at': fields.Datetime.now(),
                'failure_reason': False if status == 'pass' else _('%(skill)s score %(score)s is below minimum %(threshold)s',
                    skill=user_input.survey_id.assessment_skill_type.title(),
                    score=('%g' % user_input.scoring_total),
                    threshold=('%g' % threshold),
                ),
            }
            super(SurveyUserInput, user_input).write(vals)

            # Write the score to the linked slide.channel.partner
            attendee = user_input.slide_channel_partner_id
            if not attendee:
                user_input._vla_sync_context()
                attendee = user_input.slide_channel_partner_id
            if attendee:
                skill = user_input.survey_id.assessment_skill_type
                attendee.sudo().write({f'{skill}_score': user_input.scoring_total})

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._vla_sync_context()
        records._vla_sync_assessment_status()
        return records

    def write(self, vals):
        res = super().write(vals)
        trigger_fields = {'state', 'scoring_total', 'survey_id', 'partner_id', 'channel_id', 'job_position_id'}
        if trigger_fields.intersection(vals):
            self._vla_sync_context()
            self._vla_sync_assessment_status()
        return res

    def _mark_done(self):
        res = super()._mark_done()
        self._vla_sync_context()
        self._vla_sync_assessment_status()
        return res
