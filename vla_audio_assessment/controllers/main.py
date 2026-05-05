import base64
import json
import logging
import os
import subprocess
import tempfile

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


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

        filename = upload.filename or f'survey_q_{question.id}.webm'
        raw, mimetype, filename = self._convert_to_mp3(raw, filename)

        attachment = request.env['ir.attachment'].sudo().create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(raw),
            'mimetype': mimetype,
            'res_model': 'survey.user_input',
            'res_id': user_input.id,
        })

        return self._json_response({
            'ok': True,
            'attachment_id': attachment.id,
            'mimetype': attachment.mimetype,
            'audio_url': f'/web/content/ir.attachment/{attachment.id}/datas?download=false',
        })

    def _convert_to_mp3(self, audio_data, filename):
        """Convert audio bytes to MP3 via ffmpeg. Falls back to original data on failure."""
        tmp_in = tmp_out = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as f:
                f.write(audio_data)
                tmp_in = f.name

            tmp_out = tmp_in[:-5] + '.mp3'

            result = subprocess.run(
                ['ffmpeg', '-y', '-i', tmp_in, '-vn', '-q:a', '2', tmp_out],
                capture_output=True,
                timeout=60,
            )

            if result.returncode != 0:
                _logger.error("Audio upload: ffmpeg conversion failed: %s",
                              result.stderr.decode(errors='replace'))
                return audio_data, 'audio/webm', filename

            with open(tmp_out, 'rb') as f:
                mp3_data = f.read()

            mp3_filename = (filename.rsplit('.', 1)[0] if '.' in filename else filename) + '.mp3'
            _logger.info("Audio upload: converted to mp3 — %d → %d bytes", len(audio_data), len(mp3_data))
            return mp3_data, 'audio/mpeg', mp3_filename

        except FileNotFoundError:
            _logger.error("Audio upload: ffmpeg not found — install ffmpeg on the server")
            return audio_data, 'audio/webm', filename
        except Exception as e:
            _logger.error("Audio upload: conversion error: %s", e)
            return audio_data, 'audio/webm', filename
        finally:
            for path in (tmp_in, tmp_out):
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                    except Exception:
                        pass

    def _json_response(self, payload, status=200):
        return request.make_response(
            json.dumps(payload),
            headers=[('Content-Type', 'application/json')],
            status=status,
        )
