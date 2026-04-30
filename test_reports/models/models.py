from odoo import models


class SlideChannelPartner(models.Model):
    _inherit = "slide.channel.partner"

    def action_print_language_assessment_report(self):
        self.ensure_one()
        return self.env.ref("test_reports.action_report_language_assessment").report_action(self)