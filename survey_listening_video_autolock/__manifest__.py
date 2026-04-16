{
    "name": "Survey Listening Video Autolock",
    "summary": "Autoplay a per-question video, lock it on finish, then reveal answers.",
    "version": "18.0.2.0.0",
    "category": "Marketing/Surveys",
    "author": "Me",
    "license": "LGPL-3",
    "depends": ["survey"],
    "data": [
        "views/survey_question_views.xml",
    ],

    "assets": {
        "web.assets_frontend": [
            "survey_listening_video_autolock/static/src/js/survey_listening_gate.js",
            "survey_listening_video_autolock/static/src/scss/survey_listening_gate.scss",
        ],
    },
    "installable": True,
    "application": False,
}
