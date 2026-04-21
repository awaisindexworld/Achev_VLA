# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models


VIDEO_BLOCK_START = "<!-- listening_video:start -->"
VIDEO_BLOCK_END = "<!-- listening_video:end -->"
VIDEO_BLOCK_RE = re.compile(
    r"\s*<!-- listening_video:start -->.*?<!-- listening_video:end -->\s*",
    flags=re.S,
)


class SurveyQuestion(models.Model):
    _inherit = "survey.question"

    listening_video_type = fields.Selection(
        selection=[
            ("none", "No Video"),
            ("url", "External Video URL"),
            ("upload", "Upload Audio/Video File"),
        ],
        string="Audio/Video",
        default="none",
        help="Show a video before the answer options on this question.",
    )
    listening_video_url = fields.Char(
        string="Video URL",
        help="Direct video file URL only, for example .mp4, .webm, .ogg, or audio files like .mp3.",
    )
    listening_video_file = fields.Binary(
        string="Uploaded Media",
        attachment=True,
    )
    listening_video_filename = fields.Char(string="Media Filename")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_listening_video_description()
        return records

    def write(self, vals):
        result = super().write(vals)
        if not self.env.context.get("skip_listening_video_sync"):
            watched_fields = {
                "description",
                "listening_video_type",
                "listening_video_url",
                "listening_video_file",
                "listening_video_filename",
            }
            if watched_fields.intersection(vals):
                self._sync_listening_video_description()
        return result

    def _sync_listening_video_description(self):
        for question in self:
            base_description = VIDEO_BLOCK_RE.sub("", question.description or "").strip()
            video_html = question._build_listening_video_html()
            new_description = f"{video_html}{base_description}" if video_html else base_description
            super(
                SurveyQuestion,
                question.with_context(skip_listening_video_sync=True),
            ).write({
                "description": new_description,
            })

    def _build_listening_video_html(self):
        self.ensure_one()

        if self.is_page or self.listening_video_type == "none":
            return ""

        source_html = ""
        is_audio = False

        if self.listening_video_type == "url" and self.listening_video_url:
            raw_url = (self.listening_video_url or "").strip()
            if raw_url:
                escaped_url = self._escape_attr(raw_url)
                mimetype = self._guess_media_mimetype(raw_url)
                is_audio = self._is_audio_only(raw_url)
                source_html = self._wrap_media_player(
                    f'<source src="{escaped_url}" type="{mimetype}" />',
                    is_audio=is_audio,
                )

        elif self.listening_video_type == "upload" and self.listening_video_file:
            source_url = f"/survey/video/{self.id}"
            filename = self.listening_video_filename or f"question_{self.id}.mp4"
            mimetype = self._guess_media_mimetype(filename)
            is_audio = self._is_audio_only(filename)
            escaped_source_url = self._escape_attr(source_url)
            source_html = self._wrap_media_player(
                f'<source src="{escaped_source_url}" type="{mimetype}" />',
                is_audio=is_audio,
            )

        if not source_html:
            return ""

        return (
            f"{VIDEO_BLOCK_START}"
            f'<div class="o_survey_listening_gate mb-3" data-question-id="{self.id}" data-state="ready">'
            '<div class="o_survey_listening_intro alert alert-info py-2 px-3 mb-3">'
            'Click <strong>Start</strong> once. After the media finishes, it will lock and the answer options will appear.'
            '</div>'
            '<button type="button" class="btn btn-primary o_survey_start_watching_btn mb-3">Start</button>'
            f"{source_html}"
            '<div class="o_survey_video_locked_note alert alert-secondary mt-3 d-none">'
            'Media finished and locked. You can answer the question now.'
            '</div>'
            '</div>'
            f"{VIDEO_BLOCK_END}"
        )

    def _wrap_media_player(self, source_tag, is_audio=False):
        if is_audio:
            return (
                '<div class="o_survey_listening_video_wrap o_survey_listening_audio_wrap">'
                '<audio class="o_survey_listening_video_player o_survey_listening_audio_player" preload="auto" '
                'style="width: 100%; max-width: 650px;">'
                f"{source_tag}"
                'Your browser does not support the audio tag.'
                '</audio>'
                '</div>'
            )

        return (
            '<div class="o_survey_listening_video_wrap">'
            '<video class="o_survey_listening_video_player" preload="auto" playsinline="playsinline" '
            'style="width: 100%; max-width: 650px; height: auto; border-radius: 10px; background: #000;">'
            f"{source_tag}"
            'Your browser does not support the video tag.'
            '</video>'
            '</div>'
        )

    @staticmethod
    def _guess_media_mimetype(value):
        value = (value or "").lower()
        if value.endswith(".mp3"):
            return "audio/mpeg"
        if value.endswith(".wav"):
            return "audio/wav"
        if value.endswith(".ogg"):
            return "audio/ogg"
        if value.endswith(".webm"):
            return "video/webm"
        if value.endswith(".ogv"):
            return "video/ogg"
        return "video/mp4"

    @staticmethod
    def _is_audio_only(value):
        value = (value or "").lower()
        return value.endswith(".mp3") or value.endswith(".wav") or value.endswith(".ogg")

    @staticmethod
    def _escape_attr(value):
        return (
            (value or "")
            .replace("&", "&amp;")
            .replace('"', "&quot;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )