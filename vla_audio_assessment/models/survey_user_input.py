from odoo import _, models
from odoo.exceptions import UserError


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    def _save_lines(self, question, answer, comment=None, overwrite_existing=True):
        old_answers = self.env['survey.user_input.line'].search([
            ('user_input_id', '=', self.id),
            ('question_id', '=', question.id),
        ])
        if old_answers and not overwrite_existing:
            raise UserError(_('This answer cannot be overwritten.'))

        if question.vla_is_audio_response and question.question_type == 'char_box':
            return self._save_line_audio_answer(question, old_answers, answer)

        return super()._save_lines(question, answer, comment=comment, overwrite_existing=overwrite_existing)

    def _save_line_audio_answer(self, question, old_answers, answer):
        vals = self._get_line_audio_answer_values(question, answer)
        if old_answers:
            old_answers.write(vals)
            return old_answers
        return self.env['survey.user_input.line'].create(vals)

    def _get_line_audio_answer_values(self, question, answer):
        vals = {
            'user_input_id': self.id,
            'question_id': question.id,
            'skipped': False,
            'answer_type': 'char_box',
            'value_char_box': '[Audio Recording]',
            'attachment_id': False,
            'mimetype': False,
        }
        if not answer or (isinstance(answer, str) and not answer.strip()):
            vals.update(answer_type=False, skipped=True, value_char_box=False)
            return vals

        try:
            attachment_id = int(answer)
        except (TypeError, ValueError):
            vals.update(answer_type=False, skipped=True, value_char_box=False)
            return vals

        attachment = self.env['ir.attachment'].sudo().browse(attachment_id).exists()
        if not attachment:
            vals.update(answer_type=False, skipped=True, value_char_box=False)
            return vals

        vals.update({
            'attachment_id': attachment.id,
            'mimetype': attachment.mimetype,
        })
        return vals
