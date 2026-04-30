# -*- coding: utf-8 -*-

from odoo import fields, models


class SlideSlide(models.Model):
    _inherit = "slide.slide"

    listening_video_type = fields.Selection(
        selection=[
            ("none", "No Video"),
            ("url", "External Video URL"),
            ("upload", "Upload Audio/Video File"),
        ],
        string="Audio/Video",
        default="none",
    )

    listening_video_url = fields.Char(
        string="Video URL",
        help="Direct media URL only, for example .mp4, .webm, .ogg, .mp3, or .wav.",
    )

    listening_video_file = fields.Binary(
        string="Uploaded Media",
        attachment=True,
    )

    listening_video_filename = fields.Char(
        string="Media Filename",
    )