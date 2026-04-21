{
    'name': 'eLearning Details',
    'version': '18.0.1.1.0',
    'summary': 'Custom eLearning details records with popup lines',
    'description': '''
Custom menu under eLearning / Configuration to manage Details records.
Each record contains a name, a skill type, and detail lines opened in popup form view.
The can do statement is stored in one field and edited as left/right columns.
''',
    'category': 'Website/eLearning',
    'author': 'OpenAI',
    'license': 'LGPL-3',
    'depends': ['website_slides'],
    'data': [
        'security/elearning_detail_security.xml',
        'security/ir.model.access.csv',
        'views/elearning_detail_views.xml',
    ],
    'application': False,
    'installable': True,
}
