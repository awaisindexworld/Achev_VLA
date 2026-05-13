from urllib.parse import quote as url_quote

from odoo import http, _
from odoo.http import request


class VlaAssessmentTokenController(http.Controller):

    @http.route(
        '/vla/assessment/register/<string:token_code>',
        type='http', auth='public', website=True, sitemap=False,
    )
    def vla_assessment_register(self, token_code, **kwargs):
        token = request.env['vla.assessment.token'].sudo().search(
            [('token_code', '=', token_code)], limit=1
        )
        if not token or token.state not in ('unused', 'started'):
            return request.render('website.404')

        # ── If the visitor is not yet logged in, send them to signup/login.
        # After auth, Odoo will redirect them back to the /complete route
        # which will finish linking them to the company.
        if request.env.user._is_public():
            request.session['vla_pending_token'] = token_code
            complete_url = '/vla/assessment/complete/%s' % token_code
            signup_url = '/web/signup?redirect=%s' % url_quote(complete_url, safe='')
            return request.redirect(signup_url)

        # ── Already logged in: apply the company link right now and show
        # the landing page directly.
        token.action_mark_started()
        token._link_partner_to_company(request.env.user.sudo().partner_id)

        return request.render('vla_tokens.vla_assessment_token_landing', {
            'token': token,
            'duration': token.duration,
        })

    @http.route(
        '/vla/assessment/complete/<string:token_code>',
        type='http', auth='user', website=True, sitemap=False,
    )
    def vla_assessment_complete(self, token_code, **kwargs):
        """
        Called after the user has logged in / registered via /web/signup.
        Links the now-authenticated user's partner to the company on the token,
        then forwards them to their course (or shows the landing page).
        Portal user groups are never touched here — they remain as-is.
        """
        token = request.env['vla.assessment.token'].sudo().search(
            [('token_code', '=', token_code)], limit=1
        )
        if not token or token.state not in ('unused', 'started'):
            return request.render('website.404')

        token.action_mark_started()

        # Apply the company link now that we have an authenticated partner
        token._link_partner_to_company(request.env.user.sudo().partner_id)

        # Clear the session key — no longer needed
        request.session.pop('vla_pending_token', None)

        # If a course is attached, go straight there; otherwise show the landing page
        if token.channel_id and token.course_url:
            return request.redirect(token.course_url)

        return request.render('vla_tokens.vla_assessment_token_landing', {
            'token': token,
            'duration': token.duration,
        })