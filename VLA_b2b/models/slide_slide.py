from odoo import api, fields, models


class SlideSlide(models.Model):
    _inherit = 'slide.slide'

    assessment_skill_type = fields.Selection(related='survey_id.assessment_skill_type', string='Assessment Skill', store=True, readonly=True)

