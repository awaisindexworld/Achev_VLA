{
    'name': 'VLA B2B',
    'version': '18.0.1.0.0',
    'summary': 'B2B virtual language assessment flow for courses and surveys',
    'depends': ['website_slides', 'survey', 'mail', 'website_slides_survey', ],
    'data': [
        'security/record_rule.xml',
        'security/ir.model.access.csv',
        'views/job_position_views.xml',
        'data/mail_template.xml',
        'views/res_partner_views.xml',
        'views/survey_survey_views.xml',
        'views/slide_slide_views.xml',
        'views/slide_channel_views.xml',
        'views/slide_channel_partner_views.xml',
        'views/slide_channel_invite_views.xml',
        'views/survey_user_input_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'VLA_b2b/static/src/css/survey_hide_breadcrumb.css',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
