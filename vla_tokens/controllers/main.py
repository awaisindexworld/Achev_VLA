from odoo import http, _
from odoo.http import request


class VlaAssessmentTokenController(http.Controller):

    @http.route('/vla/assessment/register/<string:token_code>', type='http', auth='public', website=True, sitemap=False)
    def vla_assessment_register(self, token_code, **kwargs):
        token = request.env['vla.assessment.token'].sudo().search([('token_code', '=', token_code)], limit=1)
        if not token:
            return request.render('website.404')
        if token.state not in ('unused', 'started'):
            return request.render('website.404')

        token.action_mark_started()
        return request.render('vla_tokens.vla_assessment_token_landing', {
            'token': token,
            'duration': token.duration,
        })
