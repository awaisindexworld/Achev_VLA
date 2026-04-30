import html as html_lib
import json
import re

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
    can_do_statement = fields.Text(
        string='Can do statement',
        help='Stores left and right can do statements as JSON in one field.',
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
        raw = self.can_do_statement
        if not raw:
            return default_value
        # Try 1: clean JSON (fields.Text storage)
        try:
            value = json.loads(raw)
            if isinstance(value, dict):
                return {
                    'left': value.get('left', '') or '',
                    'right': value.get('right', '') or '',
                }
        except Exception:
            pass
        # Try 2: strip HTML wrappers from legacy fields.Html storage
        stripped = html_lib.unescape(re.sub(r'<[^>]+>', '', raw)).strip()
        try:
            value = json.loads(stripped)
            if isinstance(value, dict):
                return {
                    'left': value.get('left', '') or '',
                    'right': value.get('right', '') or '',
                }
        except Exception:
            pass
        return {'left': raw or '', 'right': ''}

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
