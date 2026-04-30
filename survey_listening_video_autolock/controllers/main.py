# -*- coding: utf-8 -*-
import base64

from odoo import http
from odoo.http import request


def _guess_media_mimetype(filename):
    filename = (filename or "").lower()
    if filename.endswith(".mp3"):
        return "audio/mpeg"
    if filename.endswith(".wav"):
        return "audio/wav"
    if filename.endswith(".ogg"):
        return "audio/ogg"
    if filename.endswith(".webm"):
        return "video/webm"
    if filename.endswith(".ogv"):
        return "video/ogg"
    return "video/mp4"


def _media_response(binary_content, filename):
    content = base64.b64decode(binary_content)
    mimetype = _guess_media_mimetype(filename)

    headers = [
        ("Content-Type", mimetype),
        ("Content-Length", str(len(content))),
        ("Cache-Control", "public, max-age=3600"),
        ("Accept-Ranges", "bytes"),
    ]
    return request.make_response(content, headers)


class SurveyVideoController(http.Controller):

    @http.route("/survey/video/<int:question_id>", type="http", auth="public", website=True, sitemap=False)
    def survey_video(self, question_id, **kwargs):
        question = request.env["survey.question"].sudo().browse(question_id)

        if not question.exists():
            return request.not_found()

        if question.listening_video_type != "upload" or not question.listening_video_file:
            return request.not_found()

        return _media_response(
            question.listening_video_file,
            question.listening_video_filename,
        )

    @http.route("/slides/listening/video/<int:slide_id>", type="http", auth="public", website=True, sitemap=False)
    def slide_listening_video(self, slide_id, **kwargs):
        slide = request.env["slide.slide"].sudo().browse(slide_id)

        if not slide.exists():
            return request.not_found()

        if slide.listening_video_type != "upload" or not slide.listening_video_file:
            return request.not_found()

        return _media_response(
            slide.listening_video_file,
            slide.listening_video_filename,
        )

    @http.route("/slides/listening/video_info/<int:slide_id>", type="http", auth="public", website=True, sitemap=False)
    def slide_listening_video_info(self, slide_id, **kwargs):
        slide = request.env["slide.slide"].sudo().browse(slide_id)
        if not slide.exists() or slide.listening_video_type == "none":
            return request.make_json_response({"enabled": False})

        media_url = False
        if slide.listening_video_type == "upload" and slide.listening_video_file:
            media_url = "/slides/listening/video/%s" % slide.id
        elif slide.listening_video_type == "url" and slide.listening_video_url:
            media_url = slide.listening_video_url

        return request.make_json_response({
            "enabled": bool(media_url),
            "slide_id": slide.id,
            "media_url": media_url,
            "filename": slide.listening_video_filename or slide.listening_video_url or "",
        })