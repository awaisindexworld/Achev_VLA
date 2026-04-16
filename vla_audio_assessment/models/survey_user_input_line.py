from markupsafe import Markup
from odoo import fields, models


class SurveyUserInputLine(models.Model):
    _inherit = 'survey.user_input.line'

    attachment_id = fields.Many2one('ir.attachment', string='Audio Recording', ondelete='set null')
    mimetype = fields.Char(string='MIME Type')
    answer_audio_url = fields.Char(compute='_compute_answer_audio_url')
    audio_player_html = fields.Html(compute='_compute_audio_player_html', sanitize=False)

    def _compute_answer_audio_url(self):
        for line in self:
            line.answer_audio_url = (
                f'/web/content/ir.attachment/{line.attachment_id.id}/datas?download=false'
                if line.attachment_id else False
            )

    def _compute_audio_player_html(self):
        for line in self:
            if line.answer_audio_url:
                mimetype = line.mimetype or 'audio/webm'
                line.audio_player_html = Markup(
                    f'<audio controls="controls" preload="none" style="width:100%;">'
                    f'<source src="{line.answer_audio_url}" type="{mimetype}"/>'
                    'Your browser does not support audio playback.'
                    '</audio>'
                )
            else:
                line.audio_player_html = False
