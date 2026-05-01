# -*- coding: utf-8 -*-

{
    'name': 'Survey Randomizer',
    'version': '18.0.1.0.0',
    'category': 'Survey',
    'summary': 'Randomize survey questions by section for every survey attempt.',
    'description': """
Survey Randomizer

This module adds custom per-attempt question randomization for surveys.

Features:
- Adds a checkbox on the survey Options tab to enable randomization by section.
- Adds a field to define the number of questions to show per attempt.
- Randomly selects questions every time a new survey attempt is created.
- Splits the requested question count evenly across sections.
- Assigns remainder questions to random sections on each attempt.
- Does not save fixed random counts on survey sections.
- Does not modify survey answers, scoring, survey.user_input.line, or eLearning/VLA result rendering.
    """,
    'depends': [
        'survey',
    ],
    'data': [
        'views/survey_survey_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
