from odoo import models, fields, api


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    clb_level = fields.Integer(string="CLB Level", compute="_compute_clb", store=True)

    @api.depends('scoring_percentage', 'survey_id.assessment_skill_type')
    def _compute_clb(self):
        for rec in self:
            rec.clb_level = 0
            skill = rec.survey_id.assessment_skill_type
            if skill not in ('reading', 'listening'):
                continue
            percentage = round(rec.scoring_percentage or 0.0, 2)
            config = self.env['clb.level.config'].search([
                ('skill_type', '=', skill),
                ('min_percentage', '<=', percentage),
                ('max_percentage', '>=', percentage),
            ], limit=1)
            # clb_level on config is a Selection (string key '0'–'8'); cast to int for storage
            rec.clb_level = int(config.clb_level) if config else 0

    def _vla_sync_assessment_status(self):
        super()._vla_sync_assessment_status()
        for rec in self:
            if rec.state != 'done':
                continue
            skill = rec.survey_id.assessment_skill_type
            if skill not in ('reading', 'listening'):
                continue
            attendee = rec.slide_channel_partner_id
            if not attendee:
                continue
            attendee.sudo().write({f'{skill}_clb': str(rec.clb_level)})
