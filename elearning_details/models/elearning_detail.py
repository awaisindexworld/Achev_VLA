from odoo import fields, models


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
    line_ids = fields.One2many(
        'elearning.detail.line',
        'detail_id',
        string='Lines',
    )
    recommendation = fields.Html(string='Recommendation')


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
    # ── NEW: optional job-position filter ──────────────────────────────────────
    # When set, this line applies only to attendees with this job position.
    # When left empty (False), this line is the generic/default for that CLB
    # level and is used as a fallback when no job-position-specific line exists.
    job_position_id = fields.Many2one(
        'vla.job.position',
        string='Job Position',
        index=True,
        ondelete='set null',
        help=(
            'Leave empty for a generic line (fallback for all job positions). '
            'Select a specific job position to override the generic content for that position.'
        ),
    )
    # ───────────────────────────────────────────────────────────────────────────
    can_do_statement = fields.Html(string='Can do statement')
    recommendation = fields.Html(string='Recommendation')