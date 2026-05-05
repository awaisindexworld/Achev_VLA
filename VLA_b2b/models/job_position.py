from odoo import fields, models


class VlaJobPosition(models.Model):
    _name = 'vla.job.position'
    _description = 'VLA Job Position'
    _order = 'name'

    name = fields.Char(required=True)
    #####
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    #####
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('closed', 'Closed'),
    ], default='draft', required=True, index=True)
    reading_min_clb = fields.Integer(string='Reading Min CLB', default=0)
    writing_min_clb = fields.Integer(string='Writing Min CLB', default=0)
    speaking_min_clb = fields.Integer(string='Speaking Min CLB', default=0)
    listening_min_clb = fields.Integer(string='Listening Min CLB', default=0)

    def action_set_draft(self):
        self.write({'state': 'draft'})

    def action_set_posted(self):
        self.write({'state': 'posted'})

    def action_set_closed(self):
        self.write({'state': 'closed'})
