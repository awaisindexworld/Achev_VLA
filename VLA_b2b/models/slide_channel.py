from odoo import api, fields, models, _
from odoo.osv import expression


class SlideChannel(models.Model):
    _inherit = 'slide.channel'

    vla_response_count = fields.Integer(compute='_compute_vla_response_count', string='Responses')

    @api.depends('channel_partner_ids')
    def _compute_vla_response_count(self):
        for channel in self:
            channel.vla_response_count = self.env['slide.channel.partner'].search_count([
                ('channel_id', '=', channel.id),
                ('job_position_id', '!=', False),
            ])

    def action_vla_responses(self):
        self.ensure_one()
        tree_view = self.env.ref('VLA_b2b.slide_channel_partner_view_tree_vla_b2b')
        form_view = self.env.ref('VLA_b2b.slide_channel_partner_view_form_vla_b2b')
        search_view = self.env.ref('VLA_b2b.slide_channel_partner_view_search_vla_b2b', raise_if_not_found=False)
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Responses'),
            'res_model': 'slide.channel.partner',
            'view_mode': 'list,form',
            'views': [(tree_view.id, 'list'), (form_view.id, 'form')],
            'domain': [('channel_id', '=', self.id), ('job_position_id', '!=', False)],
            'context': {'default_channel_id': self.id},
        }
        if search_view:
            action['search_view_id'] = search_view.id
        return action

    def _action_add_members(self, target_partners, member_status='joined', raise_on_access=False):
        """Allow one attendee record per course + partner + snapped job position."""
        SlideChannelPartnerSudo = self.env['slide.channel.partner'].sudo()
        allowed_channels = self._filter_add_members(target_partners, raise_on_access=raise_on_access)
        if not allowed_channels or not target_partners:
            return SlideChannelPartnerSudo

        partner_job_map = self.env.context.get('vla_partner_job_map') or {}
        all_job_ids = [jid for jid in partner_job_map.values() if jid]
        existing_domain = [('channel_id', 'in', allowed_channels.ids), ('partner_id', 'in', target_partners.ids)]
        if all_job_ids:
            existing_domain = expression.AND([existing_domain, [('job_position_id', 'in', all_job_ids)]])
        existing_channel_partners = self.env['slide.channel.partner'].with_context(active_test=False).sudo().search(existing_domain)

        def _key(channel_id, partner_id, job_id):
            return (channel_id, partner_id, job_id or False)

        existing_map = {
            _key(cp.channel_id.id, cp.partner_id.id, cp.job_position_id.id): cp
            for cp in existing_channel_partners
        }

        to_unarchive = SlideChannelPartnerSudo
        to_update_as_joined = SlideChannelPartnerSudo
        create_vals = []

        for channel in allowed_channels:
            for partner in target_partners:
                job_id = partner_job_map.get(partner.id) or False
                key = _key(channel.id, partner.id, job_id)
                channel_partner = existing_map.get(key)
                if not channel_partner and not job_id:
                    channel_partner = next((
                        cp for cp in existing_channel_partners
                        if cp.channel_id.id == channel.id and cp.partner_id.id == partner.id
                    ), None)
                if channel_partner:
                    if not channel_partner.active:
                        channel_partner.action_unarchive()
                        channel_partner.member_status = member_status
                        to_unarchive |= channel_partner
                        if member_status == 'joined':
                            channel_partner._recompute_completion()
                    elif member_status == 'joined' and channel_partner.member_status == 'invited':
                        to_update_as_joined |= channel_partner
                    continue
                create_vals.append({
                    'channel_id': channel.id,
                    'partner_id': partner.id,
                    'member_status': member_status,
                    'job_position_id': job_id,
                })

        new_channel_partners = SlideChannelPartnerSudo.create(create_vals)
        if to_update_as_joined:
            to_update_as_joined.member_status = 'joined'
            to_update_as_joined._recompute_completion()

        result_channel_partners = to_unarchive | to_update_as_joined | new_channel_partners

        if member_status == 'joined' and result_channel_partners:
            channel_partner_map = {}
            for channel_partner in result_channel_partners:
                channel_partner_map.setdefault(channel_partner.channel_id, []).append(channel_partner.partner_id.id)
            for channel, partner_ids in channel_partner_map.items():
                channel.message_subscribe(
                    partner_ids=partner_ids,
                    subtype_ids=[self.env.ref('website_slides.mt_channel_slide_published').id],
                )
        return result_channel_partners


class SlideChannelPartner(models.Model):
    _inherit = 'slide.channel.partner'

    survey_user_input_ids = fields.One2many(
        'survey.user_input', compute='_compute_vla_user_inputs', string='Tests', readonly=True
    )
    job_position_id = fields.Many2one('vla.job.position', string='Job Position Snapshot', index=True)
    reading_score = fields.Float(string='Reading Score')
    writing_score = fields.Float(string='Writing Score')
    speaking_score = fields.Float(string='Speaking Score')
    listening_score = fields.Float(string='Listening Score')
    reading_user_input_id = fields.Many2one('survey.user_input', compute='_compute_vla_user_inputs', string='Reading Response', readonly=True)
    writing_user_input_id = fields.Many2one('survey.user_input', compute='_compute_vla_user_inputs', string='Writing Response', readonly=True)
    speaking_user_input_id = fields.Many2one('survey.user_input', compute='_compute_vla_user_inputs', string='Speaking Response', readonly=True)
    listening_user_input_id = fields.Many2one('survey.user_input', compute='_compute_vla_user_inputs', string='Listening Response', readonly=True)
    assessment_final_status = fields.Selection([
        ('pending', 'Pending'),
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('error', 'Error'),
    ], compute='_compute_vla_assessment_status', string='Assessment Status', readonly=True)
    assessment_evaluated_at = fields.Datetime(compute='_compute_vla_assessment_status', string='Assessment Evaluated At', readonly=True)
    assessment_failure_reason = fields.Text(compute='_compute_vla_assessment_status', string='Assessment Failure Reason', readonly=True)

    reading_answer_line_ids = fields.One2many('survey.user_input.line', compute='_compute_vla_answer_lines', string='Reading Answers', readonly=True)
    writing_answer_line_ids = fields.One2many('survey.user_input.line', compute='_compute_vla_answer_lines', string='Writing Answers', readonly=True)
    speaking_answer_line_ids = fields.One2many('survey.user_input.line', compute='_compute_vla_answer_lines', string='Speaking Answers', readonly=True)
    listening_answer_line_ids = fields.One2many('survey.user_input.line', compute='_compute_vla_answer_lines', string='Listening Answers', readonly=True)

    _sql_constraints = [
        ('channel_partner_uniq',
         'unique(channel_id, partner_id, job_position_id)',
         'A partner membership to a channel must be unique!'),
        ('check_vla_scores_non_negative',
         'CHECK(reading_score >= 0 AND writing_score >= 0 AND speaking_score >= 0 AND listening_score >= 0)',
         'Scores must be positive.'),
    ]

    def init(self):
        self.env.cr.execute("ALTER TABLE slide_channel_partner DROP CONSTRAINT IF EXISTS channel_partner_job_uniq")

    def _get_vla_user_inputs(self):
        self.ensure_one()
        domain = [
            ('channel_id', '=', self.channel_id.id),
            ('partner_id', '=', self.partner_id.id),
            ('survey_id.assessment_skill_type', '!=', False),
        ]
        inputs = self.env['survey.user_input'].sudo().search(domain, order='write_date desc, id desc')
        if self.job_position_id:
            matched = inputs.filtered(lambda ui: ui.job_position_id.id == self.job_position_id.id)
            if matched:
                inputs = matched
        return inputs

    def _get_vla_user_input_for_skill(self, skill):
        self.ensure_one()
        domain = [
            ('channel_id', '=', self.channel_id.id),
            ('partner_id', '=', self.partner_id.id),
            ('survey_id.assessment_skill_type', '=', skill),
        ]
        if self.job_position_id:
            domain.append(('job_position_id', '=', self.job_position_id.id))

        survey_input_model = self.env['survey.user_input'].sudo()
        done_input = survey_input_model.search(domain + [('state', '=', 'done')], order='write_date desc, id desc', limit=1)
        if done_input:
            return done_input
        return survey_input_model.search(domain, order='write_date desc, id desc', limit=1)

    @api.depends('channel_id', 'partner_id', 'job_position_id')
    def _compute_vla_user_inputs(self):
        empty = self.env['survey.user_input']
        for attendee in self:
            inputs = attendee._get_vla_user_inputs() if attendee.channel_id else empty
            attendee.survey_user_input_ids = inputs

            attendee.reading_user_input_id = attendee._get_vla_user_input_for_skill('reading') or empty
            attendee.writing_user_input_id = attendee._get_vla_user_input_for_skill('writing') or empty
            attendee.speaking_user_input_id = attendee._get_vla_user_input_for_skill('speaking') or empty
            attendee.listening_user_input_id = attendee._get_vla_user_input_for_skill('listening') or empty

    @api.depends('reading_score', 'writing_score', 'speaking_score', 'listening_score', 'job_position_id')
    def _compute_vla_assessment_status(self):
        for attendee in self:
            if not attendee.channel_id:
                attendee.assessment_final_status = 'pending'
                attendee.assessment_evaluated_at = False
                attendee.assessment_failure_reason = False
                continue

            if not attendee.job_position_id:
                inputs = attendee._get_vla_user_inputs()
                attendee.assessment_final_status = 'error' if inputs else 'pending'
                attendee.assessment_evaluated_at = fields.Datetime.now() if inputs else False
                attendee.assessment_failure_reason = _('No job position snapshot found for this attendee.') if inputs else False
                continue

            required_skills = ['reading', 'writing', 'speaking', 'listening']
            missing = [skill for skill in required_skills if not attendee._get_vla_user_input_for_skill(skill)]
            if missing:
                attendee.assessment_final_status = 'pending'
                attendee.assessment_evaluated_at = False
                attendee.assessment_failure_reason = False
                continue

            job = attendee.job_position_id
            failures = []
            for skill in required_skills:
                score = attendee[f'{skill}_score']
                threshold = job[f'{skill}_min_score']
                if score < threshold:
                    failures.append(_('%(skill)s score %(score)s is below minimum %(threshold)s',
                                      skill=skill.title(), score=('%g' % score), threshold=('%g' % threshold)))
            attendee.assessment_final_status = 'fail' if failures else 'pass'
            attendee.assessment_evaluated_at = fields.Datetime.now()
            attendee.assessment_failure_reason = '\n'.join(failures) if failures else False

    @api.depends('reading_user_input_id', 'writing_user_input_id', 'speaking_user_input_id', 'listening_user_input_id')
    def _compute_vla_answer_lines(self):
        line_model = self.env['survey.user_input.line']
        for attendee in self:
            attendee.reading_answer_line_ids = attendee.reading_user_input_id.user_input_line_ids if attendee.reading_user_input_id else line_model
            attendee.writing_answer_line_ids = attendee.writing_user_input_id.user_input_line_ids if attendee.writing_user_input_id else line_model
            attendee.speaking_answer_line_ids = attendee.speaking_user_input_id.user_input_line_ids if attendee.speaking_user_input_id else line_model
            attendee.listening_answer_line_ids = attendee.listening_user_input_id.user_input_line_ids if attendee.listening_user_input_id else line_model
