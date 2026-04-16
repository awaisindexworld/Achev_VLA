(function () {
    'use strict';

    const GATE_SELECTOR = '.o_survey_listening_gate';
    const HIDDEN_CLASS = 'o_survey_hidden_until_video_done';

    function getQuestionContainer(gate) {
        return (
            gate.closest('.o_survey_question_container') ||
            gate.closest('.o_survey_form_content') ||
            gate.closest('form') ||
            document.body
        );
    }

    function shouldKeepVisible(el, gate) {
        if (!el || !gate) {
            return false;
        }

        return (
            el === gate ||
            gate.contains(el) ||
            el.classList.contains('o_survey_question_container') ||
            el.classList.contains('o_survey_form_content') ||
            el.tagName === 'FORM'
        );
    }

    function isAncestorOfGate(el, gate) {
        return el && gate && el !== gate && el.contains(gate);
    }

    function collectTargets(container, gate) {
        const targets = [];
        const selectors = [
            '.o_survey_question_answers',
            '.o_survey_question_answer',
            '.o_survey_question_simple_choice',
            '.o_survey_question_multiple_choice',
            '.o_survey_answers_list',
            '.o_survey_choice',
            '.o_survey_answer',
            '.answer',
            '.o_survey_answer_wrapper[data-question-type="simple_choice_radio"]',
            '.o_survey_answer_wrapper.o_survey_form_choice[data-question-type="simple_choice_radio"]',
            '.o_survey_choice_btn',
            '.o_survey_form_choice_item',
            '.o_survey_comment_container',
            '.o_survey_question_matrix',
            '.o_survey_question_text_box',
            '.o_survey_question_char_box',
            '.o_survey_question_numerical_box',
            '.o_survey_question_date',
            '.o_survey_question_datetime',
            '.o_survey_form_buttons',
            '.o_survey_navigation',
            '.o_survey_next',
            '.o_survey_submit',
            '.form-check',
            '.form-check-input',
            '.form-check-label',
            '.form-control',
            'textarea',
            'select',
            'input:not([type="hidden"])',
            'button',
            '.btn'
        ];

        selectors.forEach(function (selector) {
            container.querySelectorAll(selector).forEach(function (el) {
                if (shouldKeepVisible(el, gate)) {
                    return;
                }

                if (isAncestorOfGate(el, gate)) {
                    return;
                }

                if (el.closest(GATE_SELECTOR) && el.closest(GATE_SELECTOR) !== gate) {
                    return;
                }

                if (!targets.includes(el)) {
                    targets.push(el);
                }
            });
        });

        Array.from(container.children).forEach(function (child) {
            if (shouldKeepVisible(child, gate)) {
                return;
            }

            if (isAncestorOfGate(child, gate)) {
                return;
            }

            if (!targets.includes(child)) {
                targets.push(child);
            }
        });

        return targets;
    }

    function hideElement(el) {
        if (!el || el.classList.contains(HIDDEN_CLASS)) {
            return;
        }

        if (el.closest(GATE_SELECTOR)) {
            return;
        }

        if (!el.dataset.oSurveyVideoDisplay) {
            el.dataset.oSurveyVideoDisplay = el.style.display || '';
        }

        el.classList.add(HIDDEN_CLASS);
        el.style.display = 'none';
    }

    function showElement(el) {
        if (!el) {
            return;
        }

        el.classList.remove(HIDDEN_CLASS);
        el.style.display = el.dataset.oSurveyVideoDisplay || '';
    }

    function hideTargets(targets) {
        targets.forEach(hideElement);
    }

    function showTargets(targets) {
        targets.forEach(showElement);
    }

    function lockVideo(gate, video) {
        gate.dataset.state = 'completed';
        video.pause();
        video.controls = false;
        video.removeAttribute('controls');
        video.style.pointerEvents = 'none';
        video.setAttribute('tabindex', '-1');
        gate.classList.add('o_survey_video_completed');

        const note = gate.querySelector('.o_survey_video_locked_note');
        if (note) {
            note.classList.remove('d-none');
        }
    }

    function refreshGate(gate) {
        if (!gate || gate.dataset.state === 'completed') {
            return;
        }

        const container = gate._questionContainer || getQuestionContainer(gate);
        gate._questionContainer = container;

        const currentTargets = collectTargets(container, gate);
        gate._toggleTargets = currentTargets;
        hideTargets(gate._toggleTargets);
    }

    function initGate(gate) {
        if (!gate || gate.dataset.videoGateInit === '1') {
            return;
        }

        gate.dataset.videoGateInit = '1';
        gate.dataset.state = 'ready';

        const container = getQuestionContainer(gate);
        const video = gate.querySelector('.o_survey_listening_video_player');
        const startButton = gate.querySelector('.o_survey_start_watching_btn');

        if (!container || !video || !startButton) {
            return;
        }

        gate._questionContainer = container;
        gate._toggleTargets = [];

        video.controls = false;
        video.removeAttribute('controls');
        video.preload = 'auto';
        video.autoplay = false;
        video.muted = false;
        video.setAttribute('playsinline', 'true');
        video.setAttribute('webkit-playsinline', 'true');
        video.setAttribute('controlsList', 'nodownload noplaybackrate noremoteplayback nofullscreen');
        video.setAttribute('disablePictureInPicture', 'true');

        let started = false;
        let completed = false;
        let maxAllowedTime = 0;

        refreshGate(gate);

        function disableStartButton() {
            startButton.disabled = true;
            startButton.classList.add('disabled');
            startButton.setAttribute('aria-disabled', 'true');
        }

        function enableStartButton() {
            startButton.disabled = false;
            startButton.classList.remove('disabled');
            startButton.removeAttribute('aria-disabled');
        }

        startButton.addEventListener('click', function () {
            if (started || completed) {
                return;
            }

            started = true;
            gate.dataset.state = 'playing';
            disableStartButton();
            refreshGate(gate);

            const playPromise = video.play();
            if (playPromise && typeof playPromise.catch === 'function') {
                playPromise.catch(function () {
                    started = false;
                    gate.dataset.state = 'ready';
                    enableStartButton();
                });
            }
        });

        video.addEventListener('play', function () {
            if (!completed) {
                started = true;
                gate.dataset.state = 'playing';
                disableStartButton();
                refreshGate(gate);
            }
        });

        video.addEventListener('timeupdate', function () {
            if (completed) {
                return;
            }

            if (video.currentTime > maxAllowedTime) {
                maxAllowedTime = video.currentTime;
            }

            refreshGate(gate);
        });

        video.addEventListener('seeking', function () {
            if (!started || completed) {
                return;
            }

            if (video.currentTime > maxAllowedTime + 0.15) {
                video.currentTime = maxAllowedTime;
            }
        });

        video.addEventListener('pause', function () {
            if (started && !completed && video.currentTime < (video.duration || Infinity)) {
                video.play().catch(function () {});
            }
        });

        video.addEventListener('ended', function () {
            completed = true;
            lockVideo(gate, video);
            showTargets(gate._toggleTargets || []);

            if (gate._refreshInterval) {
                clearInterval(gate._refreshInterval);
                gate._refreshInterval = null;
            }
        });

        gate._refreshInterval = window.setInterval(function () {
            if (gate.dataset.state !== 'completed') {
                refreshGate(gate);
            }
        }, 250);
    }

    function initAll() {
        document.querySelectorAll(GATE_SELECTOR).forEach(function (gate) {
            initGate(gate);
            if (gate.dataset.state !== 'completed') {
                refreshGate(gate);
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAll);
    } else {
        initAll();
    }

    const observer = new MutationObserver(function () {
        initAll();
    });

    observer.observe(document.documentElement, {
        childList: true,
        subtree: true
    });
})();