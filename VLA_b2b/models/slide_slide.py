from odoo import api, fields, models


class SlideSlide(models.Model):
    _inherit = 'slide.slide'

    #####
    company_id = fields.Many2one(
        'res.company',
        related='channel_id.company_id',
        store=True,
        readonly=True,
        index=True,
    )
    #####

    assessment_skill_type = fields.Selection(related='survey_id.assessment_skill_type', string='Assessment Skill', store=True, readonly=True)

