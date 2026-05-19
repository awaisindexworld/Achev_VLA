from odoo import api, fields, models, _
from odoo.osv import expression
import logging

_logger = logging.getLogger(__name__)


class SlideChannel(models.Model):
    _inherit = 'slide.channel'

    #####
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=False,
        default=lambda self: self.env.company,
        index=True,
    )
    #####

    vla_response_count = fields.Integer(
        compute='_compute_vla_response_count',
        string='Responses'
    )

    def _vla_get_selected_company_ids(self):
        """
        Return companies currently checked in the Odoo multi-company switcher.

        In Odoo, checked/selected companies come through:
        - context['allowed_company_ids']
        - self.env.companies

        We use this only for the Responses button/count/action,
        not as a global record rule.
        """
        company_ids = (
            self.env.context.get('allowed_company_ids')
            or self.env.companies.ids
        )
        return [int(company_id) for company_id in company_ids if company_id]

    def _vla_response_domain(self):
        """
        Common domain for:
        - Responses smart button count
        - Responses action/list view

        This makes sure only responses are shown where:

        1. Response/company belongs to the currently checked companies.
        2. Job position company also belongs to the currently checked companies.
        3. Response company and job position company are the same company.

        Example:
        - Checked company: ACHEV
        - Response/course company: ACHEV
        - Job position company: Element

        Result:
        - This response will NOT show.
        """
        self.ensure_one()

        domain = [
            ('channel_id', '=', self.id),
            ('job_position_id', '!=', False),
            ('vla_company_match', '=', True),
        ]

        selected_company_ids = self._vla_get_selected_company_ids()
        if selected_company_ids:
            domain += [
                ('company_id', 'in', selected_company_ids),
                ('job_position_id.company_id', 'in', selected_company_ids),
            ]

        return domain

    @api.depends(
        'channel_partner_ids',
        'channel_partner_ids.job_position_id',
        'channel_partner_ids.job_position_id.company_id',
        'channel_partner_ids.company_id',
        'channel_partner_ids.vla_company_match',
    )
    @api.depends_context('allowed_company_ids')
    def _compute_vla_response_count(self):
        Response = self.env['slide.channel.partner']

        for channel in self:
            channel.vla_response_count = Response.search_count(
                channel._vla_response_domain()
            )

    def action_vla_responses(self):
        self.ensure_one()

        tree_view = self.env.ref(
            'VLA_b2b.slide_channel_partner_view_tree_vla_b2b'
        )
        form_view = self.env.ref(
            'VLA_b2b.slide_channel_partner_view_form_vla_b2b'
        )
        search_view = self.env.ref(
            'VLA_b2b.slide_channel_partner_view_search_vla_b2b',
            raise_if_not_found=False
        )

        action = {
            'type': 'ir.actions.act_window',
            'name': _('Responses'),
            'res_model': 'slide.channel.partner',
            'view_mode': 'list,form',
            'views': [
                (tree_view.id, 'list'),
                (form_view.id, 'form'),
            ],
            'domain': self._vla_response_domain(),
            'context': {
                'default_channel_id': self.id,
                'allowed_company_ids': self._vla_get_selected_company_ids(),
            },
        }

        if search_view:
            action['search_view_id'] = search_view.id

        return action

    def _action_add_members(
        self,
        target_partners,
        member_status='joined',
        raise_on_access=False
    ):
        """Allow one attendee record per course + partner + snapped job position."""
        SlideChannelPartnerSudo = self.env['slide.channel.partner'].sudo()

        allowed_channels = self._filter_add_members(
            target_partners,
            raise_on_access=raise_on_access
        )

        if not allowed_channels or not target_partners:
            return SlideChannelPartnerSudo

        partner_job_map = self.env.context.get('vla_partner_job_map') or {}
        all_job_ids = [jid for jid in partner_job_map.values() if jid]

        existing_domain = [
            ('channel_id', 'in', allowed_channels.ids),
            ('partner_id', 'in', target_partners.ids),
        ]

        if all_job_ids:
            existing_domain = expression.AND([
                existing_domain,
                [('job_position_id', 'in', all_job_ids)]
            ])

        existing_channel_partners = self.env[
            'slide.channel.partner'
        ].with_context(active_test=False).sudo().search(existing_domain)

        def _key(channel_id, partner_id, job_id):
            return (channel_id, partner_id, job_id or False)

        existing_map = {
            _key(
                cp.channel_id.id,
                cp.partner_id.id,
                cp.job_position_id.id
            ): cp
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
                        if cp.channel_id.id == channel.id
                        and cp.partner_id.id == partner.id
                    ), None)

                if channel_partner:
                    if not channel_partner.active:
                        channel_partner.action_unarchive()
                        channel_partner.member_status = member_status
                        to_unarchive |= channel_partner

                        if member_status == 'joined':
                            channel_partner._recompute_completion()

                    elif (
                        member_status == 'joined'
                        and channel_partner.member_status == 'invited'
                    ):
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

        result_channel_partners = (
            to_unarchive
            | to_update_as_joined
            | new_channel_partners
        )

        if member_status == 'joined' and result_channel_partners:
            channel_partner_map = {}

            for channel_partner in result_channel_partners:
                channel_partner_map.setdefault(
                    channel_partner.channel_id,
                    []
                ).append(channel_partner.partner_id.id)

            for channel, partner_ids in channel_partner_map.items():
                channel.message_subscribe(
                    partner_ids=partner_ids,
                    subtype_ids=[
                        self.env.ref(
                            'website_slides.mt_channel_slide_published'
                        ).id
                    ],
                )

        return result_channel_partners


class SlideChannelPartner(models.Model):
    _inherit = 'slide.channel.partner'

    #####
    company_id = fields.Many2one(
        'res.company',
        related='partner_id.company_id',
        store=True,
        readonly=True,
        index=True,
    )

    job_position_id = fields.Many2one(
        'vla.job.position',
        string='Job Position Snapshot',
        index=True,
        check_company=True,
    )

    vla_company_match = fields.Boolean(
        string='Response Company Matches Job Company',
        compute='_compute_vla_company_match',
        store=True,
        readonly=True,
        index=True,
    )
    #####

    survey_user_input_ids = fields.One2many(
        'survey.user_input',
        compute='_compute_vla_user_inputs',
        string='Tests',
        readonly=True
    )

    reading_score = fields.Float(string='Reading Score')
    writing_score = fields.Float(string='Writing Score')
    speaking_score = fields.Float(string='Speaking Score')
    listening_score = fields.Float(string='Listening Score')

    reading_user_input_id = fields.Many2one(
        'survey.user_input',
        compute='_compute_vla_user_inputs',
        string='Reading Response',
        readonly=True
    )
    writing_user_input_id = fields.Many2one(
        'survey.user_input',
        compute='_compute_vla_user_inputs',
        string='Writing Response',
        readonly=True
    )
    speaking_user_input_id = fields.Many2one(
        'survey.user_input',
        compute='_compute_vla_user_inputs',
        string='Speaking Response',
        readonly=True
    )
    listening_user_input_id = fields.Many2one(
        'survey.user_input',
        compute='_compute_vla_user_inputs',
        string='Listening Response',
        readonly=True
    )

    _CLB_SELECTION = [
        ('0', '0'),
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7', '7'),
        ('8', '8'),
    ]

    reading_clb = fields.Selection(
        _CLB_SELECTION,
        string='Reading CLB',
        default='0'
    )

    writing_clb = fields.Selection(
        _CLB_SELECTION,
        string='Writing CLB',
        compute='_compute_api_skill_clbs',
        inverse='_inverse_api_skill_clbs',
    )

    speaking_clb = fields.Selection(
        _CLB_SELECTION,
        string='Speaking CLB',
        compute='_compute_api_skill_clbs',
        inverse='_inverse_api_skill_clbs',
    )

    listening_clb = fields.Selection(
        _CLB_SELECTION,
        string='Listening CLB',
        default='0'
    )

    assessment_final_status = fields.Selection([
        ('pending', 'Pending'),
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('error', 'Error'),
    ], compute='_compute_vla_assessment_status',
       string='Assessment Status',
       readonly=True)

    assessment_evaluated_at = fields.Datetime(
        compute='_compute_vla_assessment_status',
        string='Assessment Evaluated At',
        readonly=True
    )

    assessment_failure_reason = fields.Text(
        compute='_compute_vla_assessment_status',
        string='Assessment Failure Reason',
        readonly=True
    )

    reading_answer_line_ids = fields.One2many(
        'survey.user_input.line',
        compute='_compute_vla_answer_lines',
        string='Reading Answers',
        readonly=True
    )

    writing_answer_line_ids = fields.One2many(
        'survey.user_input.line',
        compute='_compute_vla_answer_lines',
        string='Writing Answers',
        readonly=True
    )

    speaking_answer_line_ids = fields.One2many(
        'survey.user_input.line',
        compute='_compute_vla_answer_lines',
        string='Speaking Answers',
        readonly=True
    )

    listening_answer_line_ids = fields.One2many(
        'survey.user_input.line',
        compute='_compute_vla_answer_lines',
        string='Listening Answers',
        readonly=True
    )

    _sql_constraints = [
        (
            'channel_partner_uniq',
            'unique(channel_id, partner_id, job_position_id)',
            'A partner membership to a channel must be unique!'
        ),
        (
            'check_vla_scores_non_negative',
            'CHECK(reading_score >= 0 AND writing_score >= 0 '
            'AND speaking_score >= 0 AND listening_score >= 0)',
            'Scores must be positive.'
        ),
    ]

    def init(self):
        self.env.cr.execute(
            "ALTER TABLE slide_channel_partner "
            "DROP CONSTRAINT IF EXISTS channel_partner_job_uniq"
        )

    @api.depends(
        'company_id',
        'job_position_id',
        'job_position_id.company_id',
    )
    def _compute_vla_company_match(self):
        """
        True only when the response/course company and the job position company
        are exactly the same.

        This prevents cases like:
        - Response/course company = ACHEV
        - Job position company = Element

        from appearing in the Responses button/list.
        """
        for attendee in self:
            attendee.vla_company_match = bool(
                attendee.company_id
                and attendee.job_position_id
                and attendee.job_position_id.company_id
                and attendee.company_id.id == attendee.job_position_id.company_id.id
            )

    def _get_vla_user_inputs(self):
        self.ensure_one()

        domain = [
            ('channel_id', '=', self.channel_id.id),
            ('partner_id', '=', self.partner_id.id),
            ('survey_id.assessment_skill_type', '!=', False),
        ]

        inputs = self.env['survey.user_input'].sudo().search(
            domain,
            order='write_date desc, id desc'
        )

        if self.job_position_id:
            matched = inputs.filtered(
                lambda ui: ui.job_position_id.id == self.job_position_id.id
            )
            if matched:
                inputs = matched

        return inputs

    def _get_vla_user_input_for_skill(self, skill):
        self.ensure_one()

        model = self.env['survey.user_input'].sudo()
        skill_domain = [('survey_id.assessment_skill_type', '=', skill)]
        order = 'write_date desc, id desc'

        primary = [
            ('slide_channel_partner_id', '=', self.id)
        ] + skill_domain

        result = model.search(
            primary + [('state', '=', 'done')],
            order=order,
            limit=1
        )
        if result:
            return result

        result = model.search(
            primary,
            order=order,
            limit=1
        )
        if result:
            return result

        fallback = [
            ('channel_id', '=', self.channel_id.id),
            ('partner_id', '=', self.partner_id.id),
        ] + skill_domain

        if self.job_position_id:
            fallback.append(('job_position_id', '=', self.job_position_id.id))

        result = model.search(
            fallback + [('state', '=', 'done')],
            order=order,
            limit=1
        )
        if result:
            return result

        result = model.search(
            fallback,
            order=order,
            limit=1
        )
        if result:
            return result

        if self.partner_id:
            last_resort = [
                ('partner_id', '=', self.partner_id.id)
            ] + skill_domain

            result = model.search(
                last_resort + [('state', '=', 'done')],
                order=order,
                limit=1
            )
            if result:
                return result

            result = model.search(
                last_resort,
                order=order,
                limit=1
            )
            if result:
                return result

        return model

    @api.depends('channel_id', 'partner_id', 'job_position_id')
    def _compute_vla_user_inputs(self):
        empty = self.env['survey.user_input']

        for attendee in self:
            inputs = (
                attendee._get_vla_user_inputs()
                if attendee.channel_id
                else empty
            )

            attendee.survey_user_input_ids = inputs

            attendee.reading_user_input_id = (
                attendee._get_vla_user_input_for_skill('reading') or empty
            )
            attendee.writing_user_input_id = (
                attendee._get_vla_user_input_for_skill('writing') or empty
            )
            attendee.speaking_user_input_id = (
                attendee._get_vla_user_input_for_skill('speaking') or empty
            )
            attendee.listening_user_input_id = (
                attendee._get_vla_user_input_for_skill('listening') or empty
            )

    @api.depends(
        'writing_user_input_id',
        'writing_user_input_id.writing_clb',
        'speaking_user_input_id',
        'speaking_user_input_id.speaking_clb'
    )
    def _compute_api_skill_clbs(self):
        for attendee in self:
            w_ui = attendee.writing_user_input_id
            s_ui = attendee.speaking_user_input_id

            attendee.writing_clb = (
                str(w_ui.writing_clb)
                if w_ui and w_ui.writing_clb
                else '0'
            )

            attendee.speaking_clb = (
                str(s_ui.speaking_clb)
                if s_ui and s_ui.speaking_clb
                else '0'
            )

    def _inverse_api_skill_clbs(self):
        pass

    @api.depends(
        'reading_clb',
        'writing_clb',
        'speaking_clb',
        'listening_clb',
        'job_position_id',
        'speaking_user_input_id.speaking_clb_received'
    )
    def _compute_vla_assessment_status(self):
        for attendee in self:
            if not attendee.channel_id:
                attendee.assessment_final_status = 'pending'
                attendee.assessment_evaluated_at = False
                attendee.assessment_failure_reason = False
                continue

            if not attendee.job_position_id:
                inputs = attendee._get_vla_user_inputs()

                attendee.assessment_final_status = (
                    'error' if inputs else 'pending'
                )
                attendee.assessment_evaluated_at = (
                    fields.Datetime.now() if inputs else False
                )
                attendee.assessment_failure_reason = (
                    _('No job position snapshot found for this attendee.')
                    if inputs
                    else False
                )
                continue

            all_skills = [
                'reading',
                'writing',
                'speaking',
                'listening'
            ]

            assessed = [
                skill for skill in all_skills
                if attendee._get_vla_user_input_for_skill(skill)
                and attendee._get_vla_user_input_for_skill(skill).state == 'done'
            ]

            if not assessed:
                attendee.assessment_final_status = 'pending'
                attendee.assessment_evaluated_at = False
                attendee.assessment_failure_reason = False
                continue

            if 'speaking' in assessed:
                s_ui = attendee.speaking_user_input_id

                if not (s_ui and s_ui.speaking_clb_received):
                    attendee.assessment_final_status = 'pending'
                    attendee.assessment_evaluated_at = False
                    attendee.assessment_failure_reason = False
                    continue

            job = attendee.job_position_id
            failures = []

            for skill in assessed:
                clb = int(attendee[f'{skill}_clb'] or 0)
                threshold = job[f'{skill}_min_clb']

                if clb < threshold:
                    failures.append(_(
                        '%(skill)s CLB %(clb)s is below minimum %(threshold)s',
                        skill=skill.title(),
                        clb=('%g' % clb),
                        threshold=('%g' % threshold),
                    ))

            attendee.assessment_final_status = (
                'fail' if failures else 'pass'
            )
            attendee.assessment_evaluated_at = fields.Datetime.now()
            attendee.assessment_failure_reason = (
                '\n'.join(failures) if failures else False
            )

    @api.depends(
        'reading_user_input_id',
        'writing_user_input_id',
        'speaking_user_input_id',
        'listening_user_input_id'
    )
    def _compute_vla_answer_lines(self):
        line_model = self.env['survey.user_input.line']

        for attendee in self:
            attendee.reading_answer_line_ids = (
                attendee.reading_user_input_id.user_input_line_ids
                if attendee.reading_user_input_id
                else line_model
            )

            attendee.writing_answer_line_ids = (
                attendee.writing_user_input_id.user_input_line_ids
                if attendee.writing_user_input_id
                else line_model
            )

            attendee.speaking_answer_line_ids = (
                attendee.speaking_user_input_id.user_input_line_ids
                if attendee.speaking_user_input_id
                else line_model
            )

            attendee.listening_answer_line_ids = (
                attendee.listening_user_input_id.user_input_line_ids
                if attendee.listening_user_input_id
                else line_model
            )