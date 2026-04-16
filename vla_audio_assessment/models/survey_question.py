from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SurveyQuestion(models.Model):
    _inherit = 'survey.question'

    vla_is_audio_response = fields.Boolean(
        string='Enable Audio Response',
        help='When enabled, this Single Line Text Box question is answered by recording audio instead of typing text.',
    )
    vla_audio_max_duration = fields.Integer(
        string='Suggested Max Recording Duration (sec)',
        default=60,
    )
    vla_audio_answers_count = fields.Integer(compute='_compute_vla_audio_answers_count')

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields=allfields, attributes=attributes)
        if 'question_type' in res and res['question_type'].get('selection'):
            updated = []
            for value, label in res['question_type']['selection']:
                if value == 'char_box':
                    label = 'Single Line Text Box / Audio'
                updated.append((value, label))
            res['question_type']['selection'] = updated
        return res

    @api.depends('user_input_line_ids.attachment_id')
    def _compute_vla_audio_answers_count(self):
        grouped = self.env['survey.user_input.line'].read_group(
            [('question_id', 'in', self.ids), ('attachment_id', '!=', False)],
            ['question_id'],
            ['question_id'],
        )
        count_map = {
            item['question_id'][0]: item['question_id_count']
            for item in grouped if item.get('question_id')
        }
        for question in self:
            question.vla_audio_answers_count = count_map.get(question.id, 0)

    @api.constrains('vla_is_audio_response', 'question_type')
    def _check_audio_response_question_type(self):
        for question in self:
            if question.vla_is_audio_response and question.question_type != 'char_box':
                raise ValidationError(
                    'Audio Response can only be enabled for Single Line Text Box / Audio questions.'
                )
