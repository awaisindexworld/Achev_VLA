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
            rec.clb_level = config.clb_level if config else 0
