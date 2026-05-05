
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ClbLevelConfig(models.Model):
    _name = 'clb.level.config'
    _description = 'CLB Level Configuration'
    _order = 'skill_type, clb_level'

    name = fields.Char(required=True)
    skill_type = fields.Selection([
        ('reading', 'Reading'),
        ('listening', 'Listening'),
    ], required=True, string='Skill Type')
    min_percentage = fields.Float(required=True, string='Min %', digits=(6, 2))
    max_percentage = fields.Float(required=True, string='Max %', digits=(6, 2))
    clb_level = fields.Integer(required=True, string='CLB Level')

    @api.constrains('min_percentage', 'max_percentage')
    def _check_min_max(self):
        for rec in self:
            if rec.min_percentage > rec.max_percentage:
                raise ValidationError(
                    f"CLB {rec.clb_level}: Min % ({rec.min_percentage}) cannot exceed Max % ({rec.max_percentage})."
                )

    @api.constrains('min_percentage', 'max_percentage', 'skill_type')
    def _check_overlap(self):
        for rec in self:
            domain = [
                ('id', '!=', rec.id),
                ('skill_type', '=', rec.skill_type),
                ('min_percentage', '<=', rec.max_percentage),
                ('max_percentage', '>=', rec.min_percentage),
            ]
            overlap = self.search(domain)
            if overlap:
                raise ValidationError(
                    f"CLB {rec.clb_level} range [{rec.min_percentage}%, {rec.max_percentage}%] "
                    f"overlaps with CLB {overlap[0].clb_level} "
                    f"[{overlap[0].min_percentage}%, {overlap[0].max_percentage}%]."
                )
