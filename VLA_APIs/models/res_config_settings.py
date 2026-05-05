from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    vla_aws_access_key = fields.Char(
        string='Access Key',
        config_parameter='vla_apis.aws_access_key',
    )
    vla_aws_secret_key = fields.Char(
        string='Secret Key',
        config_parameter='vla_apis.aws_secret_key',
    )
    vla_aws_region = fields.Char(
        string='Region',
        config_parameter='vla_apis.aws_region',
    )
    vla_aws_service = fields.Char(
        string='Service',
        config_parameter='vla_apis.aws_service',
    )
