import base64
import json

from odoo import http
from odoo.http import request


class VLASurveyAudioController(http.Controller):

    @http.route('/survey/vla/audio/upload', type='http', auth='public', methods=['POST'], csrf=True, website=True)
    def survey_vla_audio_upload(self, answer_token=None, question_id=None, **post):
        user_input = request.env['survey.user_input'].sudo().search([('access_token', '=', answer_token)], limit=1)
        if not user_input:
            return self._json_response({'ok': False, 'error': 'Survey answer token not found.'}, status=404)

        try:
            question_id = int(question_id or 0)
        except (TypeError, ValueError):
            return self._json_response({'ok': False, 'error': 'Invalid question.'}, status=400)

        question = request.env['survey.question'].sudo().browse(question_id).exists()
        if not question or question.survey_id != user_input.survey_id or not question.vla_is_audio_response:
            return self._json_response({'ok': False, 'error': 'This question is not configured for audio recording.'}, status=400)

        upload = request.httprequest.files.get('audio_blob')
        if not upload:
            return self._json_response({'ok': False, 'error': 'No audio file was received.'}, status=400)

        raw = upload.read()
        if not raw:
            return self._json_response({'ok': False, 'error': 'The uploaded audio file is empty.'}, status=400)

        attachment = request.env['ir.attachment'].sudo().create({
            'name': upload.filename or f'survey_q_{question.id}.webm',
            'type': 'binary',
            'datas': base64.b64encode(raw),
            'mimetype': upload.mimetype or 'audio/webm',
            'res_model': 'survey.user_input',
            'res_id': user_input.id,
        })

        return self._json_response({
            'ok': True,
            'attachment_id': attachment.id,
            'mimetype': attachment.mimetype,
            'audio_url': f'/web/content/ir.attachment/{attachment.id}/datas?download=false',
        })

    def _json_response(self, payload, status=200):
        return request.make_response(
            json.dumps(payload),
            headers=[('Content-Type', 'application/json')],
            status=status,
        )
