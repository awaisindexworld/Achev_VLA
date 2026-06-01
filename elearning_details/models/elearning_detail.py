from odoo import api, fields, models


class ElearningDetail(models.Model):
    _name = 'elearning.detail'
    _description = 'eLearning Detail'
    _order = 'id desc'

    name = fields.Char(required=True)

    skill_type = fields.Selection(
        selection=[
            ('speaking', 'Speaking'),
            ('listening', 'Listening'),
            ('writing', 'Writing'),
            ('reading', 'Reading'),
            ('all_skills', 'All Skills'),
        ],
        string='Skill',
        required=True,
        default='speaking',
    )

    job_position_id = fields.Many2one(
        'vla.job.position',
        string='Job Position',
        index=True,
        ondelete='set null',
        help=(
            'Used for All Skills recommendations. Only job positions from the '
            'currently selected companies should be selectable.'
        ),
    )

    line_ids = fields.One2many(
        'elearning.detail.line',
        'detail_id',
        string='Lines',
    )

    recommendation = fields.Html(string='Recommendation')

    @api.onchange('skill_type')
    def _onchange_skill_type(self):
        """
        Parent job position is only for All Skills records.
        Normal skill records use job_position_id on their detail lines.
        """
        for record in self:
            if record.skill_type != 'all_skills':
                record.job_position_id = False

    @api.onchange('job_position_id')
    def _onchange_job_position_id(self):
        """
        Safety check: if an old/manual value belongs to a company that is not
        checked in the company switcher, clear it.
        """
        allowed_company_ids = self.env.context.get('allowed_company_ids') or self.env.companies.ids

        for record in self:
            company = record.job_position_id.company_id
            if company and company.id not in allowed_company_ids:
                record.job_position_id = False


class ElearningDetailLine(models.Model):
    _name = 'elearning.detail.line'
    _description = 'eLearning Detail Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)

    detail_id = fields.Many2one(
        'elearning.detail',
        string='Detail',
        required=True,
        ondelete='cascade',
    )

    clb = fields.Selection(
        selection=[('0', '0')] + [(str(i), str(i)) for i in range(1, 9)],
        string='CLB',
        required=True,
        default='0',
    )

    job_position_id = fields.Many2one(
        'vla.job.position',
        string='Job Position',
        index=True,
        ondelete='set null',
        help=(
            'Leave empty for a generic line/fallback. Select a specific job '
            'position to override this CLB content for that position.'
        ),
    )

    can_do_statement = fields.Html(string='Can do statement')
    recommendation = fields.Html(string='Recommendation')

    @api.onchange('job_position_id')
    def _onchange_job_position_id(self):
        """
        Safety check: line job positions must also belong to checked companies only.
        """
        allowed_company_ids = self.env.context.get('allowed_company_ids') or self.env.companies.ids

        for record in self:
            company = record.job_position_id.company_id
            if company and company.id not in allowed_company_ids:
                record.job_position_id = False
