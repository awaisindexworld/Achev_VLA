
{
    'name': 'CLB Survey Integration',
    'version': '1.0',
    'depends': ['VLA_b2b'],
    'data': [
        'security/ir.model.access.csv',
        'views/clb_config_views.xml',
        'views/survey_user_input_views.xml',
        'views/survey_templates.xml',
        'data/clb_level_data.xml',
    ],
    'installable': True,
}
