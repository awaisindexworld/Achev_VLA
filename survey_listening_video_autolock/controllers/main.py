# -*- coding: utf-8 -*-
import base64

from odoo import http
from odoo.http import request


class SurveyVideoController(http.Controller):

    @http.route('/survey/video/<int:question_id>', type='http', auth='public', website=True, sitemap=False)
    def survey_video(self, question_id, **kwargs):
        question = request.env['survey.question'].sudo().browse(question_id)

        if not question.exists():
            return request.not_found()

        if question.is_page or question.listening_video_type != 'upload' or not question.listening_video_file:
            return request.not_found()

        filename = (question.listening_video_filename or '').lower()
        mimetype = 'video/mp4'
        if filename.endswith('.webm'):
            mimetype = 'video/webm'
        elif filename.endswith('.ogg') or filename.endswith('.ogv'):
            mimetype = 'video/ogg'

        content = base64.b64decode(question.listening_video_file)

        headers = [
            ('Content-Type', mimetype),
            ('Content-Length', str(len(content))),
            ('Cache-Control', 'public, max-age=3600'),
            ('Accept-Ranges', 'bytes'),
        ]
        return request.make_response(content, headers)