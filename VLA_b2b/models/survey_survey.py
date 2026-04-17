from odoo import fields, models


class SurveySurvey(models.Model):
    _inherit = 'survey.survey'

    assessment_skill_type = fields.Selection([
        ('reading', 'Reading'),
        ('writing', 'Writing'),
        ('speaking', 'Speaking'),
        ('listening', 'Listening'),
    ], string='Assessment Skill')
