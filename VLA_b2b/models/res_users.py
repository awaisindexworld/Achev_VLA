# Part of VLA_b2b. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _signup_create_user(self, values):
        """
        Odoo's _create_user_from_template calls copy() on a template portal
        user (YourCompany), which overwrites the existing partner's company_id.

        Fix:
          1. Snapshot partner company BEFORE super() corrupts it.
          2. ADD partner's company to user's company_ids (don't replace —
             replacing removes YourCompany and breaks website/res.company access).
          3. Set partner's company as the user's default company (company_id).
          4. Restore partner's company_id (safe now because user already has it).
        """
        # --- 1. Snapshot partner company before super() touches it ---
        partner_id = values.get('partner_id')
        original_company_id = None
        if partner_id:
            partner = self.env['res.partner'].sudo().browse(partner_id)
            if partner.exists() and partner.company_id:
                original_company_id = partner.company_id.id

        # --- 2. Create the user (may corrupt partner.company_id) ---
        user = super()._signup_create_user(values)

        if original_company_id:
            # --- 3. ADD partner company to user's allowed list + set as default ---
            # Using (4, id) adds without removing YourCompany,
            # so the user can still read res.company / access the website.
            user.sudo().write({
                'company_id': original_company_id,
                'company_ids': [(4, original_company_id)],
            })

            # --- 4. Restore partner's company safely ---
            # Constraint is satisfied because the user now has this company.
            if user.partner_id.sudo().company_id.id != original_company_id:
                user.partner_id.sudo().write({'company_id': original_company_id})

        return user