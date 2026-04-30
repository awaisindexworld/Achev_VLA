# -*- coding: utf-8 -*-

import uuid

from odoo import api, fields, models


class VlaAssessmentToken(models.Model):
    _name = 'vla.assessment.token'
    _description = 'VLA Assessment Registration Token'
    _order = 'create_date desc, id desc'

    name = fields.Char(default='New', copy=False, readonly=True)

    token_code = fields.Char(
        required=True,
        copy=False,
        readonly=True,
        index=True,
    )

    token_type = fields.Selection(
        selection=[
            ('b2c', 'B2C / Individual'),
            ('b2b', 'B2B / Company Invite'),
        ],
        required=True,
        default='b2c',
        index=True,
    )

    state = fields.Selection(
        selection=[
            ('unused', 'Unused'),
            ('started', 'Started'),
            ('used', 'Used'),
            ('cancelled', 'Cancelled'),
        ],
        default='unused',
        required=True,
        index=True,
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        ondelete='set null',
        index=True,
    )

    company_partner_id = fields.Many2one(
        'res.partner',
        string='Company Wallet Owner',
        ondelete='set null',
        index=True,
    )

    candidate_email = fields.Char(string='Candidate Email')

    duration = fields.Selection(
        selection=[
            ('30', '30 Minutes'),
            ('60', '60 Minutes'),
        ],
        required=True,
        index=True,
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product Variant',
        ondelete='set null',
    )

    channel_id = fields.Many2one(
        'slide.channel',
        string='Course',
        ondelete='set null',
        help='Course connected to the purchased 30-minute or 60-minute product.',
    )

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        ondelete='set null',
    )

    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        ondelete='set null',
    )

    registration_url = fields.Char(
        compute='_compute_registration_url',
        string='Registration URL',
    )

    course_url = fields.Char(
        compute='_compute_course_url',
        string='Course URL',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('token_code'):
                vals['token_code'] = uuid.uuid4().hex

            if vals.get('name', 'New') == 'New':
                vals['name'] = 'VLA-%s' % vals['token_code'][:8].upper()

        return super().create(vals_list)

    def _compute_registration_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''

        for token in self:
            token.registration_url = '%s/vla/assessment/register/%s' % (
                base_url.rstrip('/'),
                token.token_code,
            )

    def _compute_course_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''

        for token in self:
            token.course_url = ''

            if not token.channel_id:
                continue

            website_url = token.channel_id.website_url or ''

            if not website_url:
                website_url = '/slides/%s' % token.channel_id.id

            # If Odoo already gives a full absolute URL, use it directly.
            if website_url.startswith('http://') or website_url.startswith('https://'):
                token.course_url = website_url
                continue

            # Otherwise make sure it is a relative URL starting with /
            if not website_url.startswith('/'):
                website_url = '/%s' % website_url

            token.course_url = '%s%s' % (
                base_url.rstrip('/'),
                website_url,
            )

    def action_mark_started(self):
        for token in self.filtered(lambda t: t.state == 'unused'):
            token.state = 'started'

    def action_mark_used(self):
        for token in self.filtered(lambda t: t.state in ('unused', 'started')):
            token.state = 'used'