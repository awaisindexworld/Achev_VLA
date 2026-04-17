from odoo import fields, models, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    current_job_position_id = fields.Many2one(
        'vla.job.position',
        string='Current Job Position',
        domain="[('state', '=', 'posted')]",
    )

    def action_send_registration_email(self):
        self.ensure_one()

        if not self.email:
            raise UserError(_("This contact does not have an email address."))

        template = self.env.ref('VLA_b2b.mail_template_partner_registration_success', raise_if_not_found=False)
        if not template:
            raise UserError(_("Registration email template not found."))

        template.send_mail(self.id, force_send=True)
        return True