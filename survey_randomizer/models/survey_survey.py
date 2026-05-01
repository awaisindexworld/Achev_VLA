# -*- coding: utf-8 -*-

import random

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SurveySurvey(models.Model):
    _inherit = 'survey.survey'

    vla_randomize_by_section = fields.Boolean(
        string='Randomize Questions by Section',
        help='Randomly pick questions from each section for every new survey attempt.',
    )

    vla_random_total_questions = fields.Integer(
        string='Number of Questions to Show',
        default=0,
        help=(
            'Total number of questions shown per attempt. '
            'The amount is split evenly across sections; any remainder is assigned '
            'to random sections for each attempt.'
        ),
    )

    @api.constrains('vla_random_total_questions')
    def _check_vla_random_total_questions(self):
        for survey in self:
            if survey.vla_random_total_questions < 0:
                raise ValidationError(_('Number of Questions to Show cannot be negative.'))

    @api.onchange('vla_randomize_by_section')
    def _onchange_vla_randomize_by_section(self):
        """Keep onchange safe.

        Do not apply fixed section allocation on save.
        Randomization happens fresh on every survey attempt.
        """
        return

    def _vla_get_section_question_map(self):
        """Return section -> questions mapping.

        Odoo stores sections/pages and questions together in question_and_page_ids.
        Sections/pages have is_page = True.
        Real questions have is_page = False and a valid question_type.

        Sections are used only to group questions. They are never stored as
        attempt questions.
        """
        self.ensure_one()

        items = self.question_and_page_ids.sorted(
            key=lambda q: (q.sequence, q.id or 0)
        )

        section_question_map = {}
        current_section = False

        for item in items:
            if item.is_page:
                current_section = item
                section_question_map.setdefault(
                    current_section,
                    self.env['survey.question']
                )
                continue

            if current_section and not item.is_page and item.question_type:
                section_question_map[current_section] |= item

        return {
            section: questions
            for section, questions in section_question_map.items()
            if questions
        }

    def _vla_get_attempt_distribution(self, section_question_map):
        """Calculate a fresh random section distribution for one attempt.

        Example:
        - Total questions: 10
        - Sections: 4
        - Base: 2 each
        - Remainder: 2

        Every attempt randomly chooses which two sections receive +1.
        Nothing is saved globally on the survey or section records.
        """
        self.ensure_one()

        available_by_section = {
            section.id: len(questions)
            for section, questions in section_question_map.items()
        }

        available_by_section = {
            section_id: count
            for section_id, count in available_by_section.items()
            if section_id and count > 0
        }

        if not available_by_section:
            return {}

        total_available = sum(available_by_section.values())
        requested_total = min(
            self.vla_random_total_questions or 0,
            total_available
        )

        if requested_total <= 0:
            return {}

        section_ids = list(available_by_section.keys())
        random.shuffle(section_ids)

        base_count, remainder = divmod(requested_total, len(section_ids))

        distribution = {
            section_id: base_count
            for section_id in section_ids
        }

        # Remainder sections are randomized for every attempt.
        remainder_candidates = section_ids[:]
        random.shuffle(remainder_candidates)

        for section_id in remainder_candidates:
            if remainder <= 0:
                break

            if distribution[section_id] < available_by_section[section_id]:
                distribution[section_id] += 1
                remainder -= 1

        # If any section cannot satisfy its assigned count, cap it.
        shortage = 0

        for section_id, count in list(distribution.items()):
            available = available_by_section[section_id]

            if count > available:
                shortage += count - available
                distribution[section_id] = available

        # Redistribute shortage to sections that still have capacity.
        while shortage > 0:
            candidates = [
                section_id
                for section_id in section_ids
                if distribution[section_id] < available_by_section[section_id]
            ]

            if not candidates:
                break

            section_id = random.choice(candidates)
            distribution[section_id] += 1
            shortage -= 1

        return distribution

    def _vla_get_random_questions_for_attempt(self):
        """Pick real questions for one attempt.

        It only returns selected real questions for this attempt.
        """
        self.ensure_one()

        if not self.vla_randomize_by_section:
            return self.env['survey.question']

        section_question_map = self._vla_get_section_question_map()
        if not section_question_map:
            return self.env['survey.question']

        distribution = self._vla_get_attempt_distribution(section_question_map)
        if not distribution:
            return self.env['survey.question']

        selected_questions = self.env['survey.question']

        for section, questions in section_question_map.items():
            count = distribution.get(section.id, 0)

            if count <= 0:
                continue

            question_ids = questions.ids[:]
            random.shuffle(question_ids)

            selected_questions |= self.env['survey.question'].browse(
                question_ids[:count]
            )

        # Critical: return only real questions, never section/page records.
        selected_questions = selected_questions.filtered(
            lambda q: not q.is_page and q.question_type
        )

        return selected_questions.sorted(
            key=lambda q: (q.sequence, q.id or 0)
        )


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    @api.model_create_multi
    def create(self, vals_list):
        user_inputs = super().create(vals_list)

        for user_input in user_inputs:
            survey = user_input.survey_id

            if not survey.vla_randomize_by_section:
                continue

            selected_questions = survey._vla_get_random_questions_for_attempt()

            if not selected_questions:
                continue

            # Store randomized real questions only for this attempt.
            # Do not include section/page records here.
            if 'predefined_question_ids' in user_input._fields:
                user_input.write({
                    'predefined_question_ids': [(6, 0, selected_questions.ids)]
                })

        return user_inputs
