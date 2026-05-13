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

    @api.model
    def get_detail_line(self, attendee, skill_type):
        """
        Return the best-matching elearning.detail.line for the given attendee and skill.

        Lookup priority:
        1. CLB + job_position_id match  (job-position-specific content)
        2. CLB match with no job_position_id set  (generic fallback)

        Companies are naturally segregated because vla.job.position records
        are company-scoped, so a line referencing a job position from
        Company A will never match an attendee from Company B.
        """
        clb = getattr(attendee, f'{skill_type}_clb', '0') or '0'
        ELine = self.env['elearning.detail.line'].sudo()
        base_domain = [('detail_id.skill_type', '=', skill_type), ('clb', '=', clb)]

        # 1. Try job-position-specific line first
        job_position_id = attendee.job_position_id.id if attendee.job_position_id else False
        if job_position_id:
            line = ELine.search(base_domain + [('job_position_id', '=', job_position_id)], limit=1)
            if line:
                return line

        # 2. Fall back to the generic line (no job position set)
        return ELine.search(base_domain + [('job_position_id', '=', False)], limit=1)