import base64
import os
from odoo import models, api


class SlideChannelPartner(models.Model):
    _inherit = "slide.channel.partner"

    def action_print_language_assessment_report(self):
        self.ensure_one()
        return self.env.ref("vla_assessment_reports.action_report_language_assessment").report_action(self)


class ReportVlaAssessmentReportsHelper(models.AbstractModel):
    _name = 'report.vla_assessment_reports.helper'
    _description = 'Report Image Helper'

    @api.model
    def get_image_base64(self, image_filename):
        img_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'static', 'src', 'img', image_filename,
        )
        with open(img_path, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
        ext = image_filename.rsplit('.', 1)[-1].lower()
        mime = 'image/png' if ext == 'png' else 'image/jpeg'
        return f'data:{mime};base64,{encoded}'