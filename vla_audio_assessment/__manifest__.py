{
    'name': 'VLA Audio Assessment',
    'version': '18.0.5.0.0',
    'summary': 'Audio recording answers inside Odoo 18 Surveys',
    'category': 'Marketing/Surveys',
    'author': 'OpenAI',
    'license': 'LGPL-3',
    'depends': ['survey', 'website'],
    'data': [
        'views/survey_question_views.xml',
        'views/survey_user_input_views.xml',
        'views/survey_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'vla_audio_assessment/static/src/js/vla_survey_audio.js',
            'vla_audio_assessment/static/src/css/vla_survey_audio.css',
        ],
    },
    'application': False,
    'installable': True,
}
