import json

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
        selection=[(str(i), str(i)) for i in range(1, 9)],
        string='CLB',
        required=True,
    )
    can_do_statement = fields.Html(
        string='Can do statement',
        help='Stores left and right can do statements in one field.',
    )
    can_do_statement_left = fields.Html(
        string='Can do statement Left',
        compute='_compute_can_do_statement_parts',
        inverse='_inverse_can_do_statement_parts',
    )
    can_do_statement_right = fields.Html(
        string='Can do statement Right',
        compute='_compute_can_do_statement_parts',
        inverse='_inverse_can_do_statement_parts',
    )
    recommendation = fields.Html(string='Recommendation')

    def _deserialize_can_do_statement(self):
        self.ensure_one()
        default_value = {'left': '', 'right': ''}
        if not self.can_do_statement:
            return default_value
        try:
            value = json.loads(self.can_do_statement)
            if isinstance(value, dict):
                return {
                    'left': value.get('left', '') or '',
                    'right': value.get('right', '') or '',
                }
        except Exception:
            pass
        return {
            'left': self.can_do_statement or '',
            'right': '',
        }

    def _compute_can_do_statement_parts(self):
        for record in self:
            parts = record._deserialize_can_do_statement()
            record.can_do_statement_left = parts['left']
            record.can_do_statement_right = parts['right']

    def _inverse_can_do_statement_parts(self):
        for record in self:
            left_value = record.can_do_statement_left or ''
            right_value = record.can_do_statement_right or ''
            record.can_do_statement = json.dumps({
                'left': left_value,
                'right': right_value,
            })
