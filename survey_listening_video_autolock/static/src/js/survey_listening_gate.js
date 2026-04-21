(function () {
    'use strict';

    const GATE_SELECTOR = '.o_survey_listening_gate';
    const HIDDEN_CLASS = 'o_survey_hidden_until_video_done';

    function getQuestionWrapper(gate) {
        return gate.closest('.js_question-wrapper');
    }

    function getVideo(gate) {
        return gate.querySelector('.o_survey_listening_video_player');
    }

    function getStartButton(gate) {
        return gate.querySelector('.o_survey_start_watching_btn');
    }

    function getAnswerTargets(questionWrapper, gate) {
        if (!questionWrapper) {
            return [];
        }

        const selectors = [
            '.o_survey_answer_wrapper',
            '.o_survey_question_multiple_choice',
            '.o_survey_question_matrix',
            '.o_survey_comment_container',
            '.o_survey_question_text_box',
            '.o_survey_question_char_box',
            '.o_survey_question_numerical_box',
            '.o_survey_question_date',
            '.o_survey_question_datetime'
        ];

        const targets = [];

        selectors.forEach(function (selector) {
            questionWrapper.querySelectorAll(selector).forEach(function (el) {
                if (el === gate || gate.contains(el)) {
                    return;
                }
                if (!targets.includes(el)) {
                    targets.push(el);
                }
            });
        });

        return targets;
    }

    function getContinueButtons() {
        return Array.from(document.querySelectorAll('.o_survey_navigation_submit')).filter(function (btn) {
            return btn.value === 'next' || btn.value === 'finish';
        });
    }

    function hideElement(el) {
        if (!el || el.classList.contains(HIDDEN_CLASS)) {
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

    function disableContinue(btn) {
        if (!btn) {
            return;
        }
        btn.disabled = true;
        btn.classList.add('disabled');
        btn.setAttribute('aria-disabled', 'true');
        btn.style.pointerEvents = 'none';
        btn.style.opacity = '0.5';
    }

    function enableContinue(btn) {
        if (!btn) {
            return;
        }
        btn.disabled = false;
        btn.classList.remove('disabled');
        btn.removeAttribute('aria-disabled');
        btn.style.pointerEvents = '';
        btn.style.opacity = '';
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

        const questionWrapper = gate._questionWrapper || getQuestionWrapper(gate);
        gate._questionWrapper = questionWrapper;

        gate._answerTargets = getAnswerTargets(questionWrapper, gate);
        gate._continueButtons = getContinueButtons();

        gate._answerTargets.forEach(hideElement);
        gate._continueButtons.forEach(disableContinue);
    }

    function completeGate(gate, video) {
        gate.dataset.state = 'completed';
        lockVideo(gate, video);

        (gate._answerTargets || []).forEach(showElement);
        (gate._continueButtons || []).forEach(enableContinue);

        if (gate._refreshInterval) {
            clearInterval(gate._refreshInterval);
            gate._refreshInterval = null;
        }
    }

    function initGate(gate) {
        if (!gate || gate.dataset.videoGateInit === '1') {
            return;
        }

        gate.dataset.videoGateInit = '1';
        gate.dataset.state = 'ready';

        const questionWrapper = getQuestionWrapper(gate);
        const video = getVideo(gate);
        const startButton = getStartButton(gate);

        if (!questionWrapper || !video || !startButton) {
            return;
        }

        gate._questionWrapper = questionWrapper;
        gate._answerTargets = [];
        gate._continueButtons = [];

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
            completeGate(gate, video);
        });

        gate._refreshInterval = window.setInterval(function () {
            if (gate.dataset.state !== 'completed') {
                refreshGate(gate);
            }
        }, 300);
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

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
})();