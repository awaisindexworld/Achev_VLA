from odoo.http import request
from odoo.addons.website_slides_survey.controllers.survey import Survey


class SurveyVLA(Survey):

    def _prepare_survey_finished_values(self, survey, answer, token=False):
        result = super()._prepare_survey_finished_values(survey, answer, token)
        if answer.slide_id:
            channel = answer.slide_id.channel_id
            content_slides = channel.slide_content_ids
            slide_ids = content_slides.ids
            if answer.slide_id.id in slide_ids:
                idx = slide_ids.index(answer.slide_id.id)
                if idx < len(slide_ids) - 1:
                    next_slide = content_slides[idx + 1]
                    slug = request.env['ir.http']._slug
                    result['next_slide_url'] = '/slides/slide/%s?fullscreen=1' % slug(next_slide)
        return result
