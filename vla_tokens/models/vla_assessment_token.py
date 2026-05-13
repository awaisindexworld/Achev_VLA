import uuid

from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


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

            if website_url.startswith('http://') or website_url.startswith('https://'):
                token.course_url = website_url
                continue

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

    def _link_partner_to_company(self, partner):
        """
        Automatically link the given partner (the user who just registered or
        logged in) to the company partner stored on this token.

        Rules:
        - Only runs when company_partner_id is set (B2B tokens).
        - Sets partner.parent_id so the user appears under that company in
          Contacts, exactly as if an admin had done it manually.
        - Never changes the user's portal/internal group — they remain portal.
        - Also stores the partner back on the token so it is traceable in the
          backend (only sets it if not already set, to avoid overwriting a
          manually-assigned B2C partner).
        """
        self.ensure_one()

        if not self.company_partner_id or not partner:
            return

        # Ensure company_partner_id is actually flagged as a company in Odoo
        if not self.company_partner_id.is_company:
            _logger.warning(
                "VLA token %s: company_partner_id %s is not flagged as a company — "
                "skipping automatic company assignment",
                self.token_code, self.company_partner_id.id,
            )
            return

        vals = {}

        # Only set parent_id if not already pointing to the right company.
        # This avoids overwriting an existing company relationship.
        if partner.parent_id.id != self.company_partner_id.id:
            vals['parent_id'] = self.company_partner_id.id
            _logger.info(
                "VLA token %s: linking partner %s (%s) to company %s (%s)",
                self.token_code,
                partner.id, partner.email or partner.name,
                self.company_partner_id.id, self.company_partner_id.name,
            )

        if vals:
            partner.sudo().write(vals)

        # Record who used this token if not already set
        if not self.partner_id:
            self.sudo().write({'partner_id': partner.id})