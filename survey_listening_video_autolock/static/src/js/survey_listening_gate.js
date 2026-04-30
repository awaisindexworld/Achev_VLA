(function () {
    'use strict';

    const GATE_SELECTOR = '.o_survey_listening_gate';
    const HIDDEN_CLASS = 'o_survey_hidden_until_video_done';

    function getVideo(gate) {
        return gate.querySelector('.o_survey_listening_video_player');
    }

    function getStartButton(gate) {
        return gate.querySelector('.o_survey_start_watching_btn');
    }

    function isSurveyGate(gate) {
        return !!gate.dataset.questionId && !gate.classList.contains('o_course_listening_gate');
    }

    function getContinueButtons() {
        return Array.from(document.querySelectorAll('.o_survey_navigation_submit')).filter(function (btn) {
            return btn.value === 'next' || btn.value === 'finish';
        });
    }

    function hideElement(el) {
        if (!el) {
            return;
        }
        el.classList.add(HIDDEN_CLASS);
        el.style.display = 'none';
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
        if (!gate) {
            return;
        }

        if (isSurveyGate(gate)) {
            gate._continueButtons = getContinueButtons();
            gate._continueButtons.forEach(hideElement);
        }
    }

    function completeGate(gate, video) {
        gate.dataset.state = 'completed';
        lockVideo(gate, video);
        refreshGate(gate);

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

        const video = getVideo(gate);
        const startButton = getStartButton(gate);

        if (!video || !startButton) {
            return;
        }

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
            refreshGate(gate);
        }, 300);
    }

    function initAll() {
        document.querySelectorAll(GATE_SELECTOR).forEach(function (gate) {
            initGate(gate);
            refreshGate(gate);
        });
    }

    function hideContinueButtonEverywhere() {
        if (!document.querySelector('.o_survey_listening_gate[data-question-id]')) {
            return;
        }

        const selectors = [
            '.o_survey_navigation_submit',
            'button',
            'input[type="submit"]',
            'a.btn',
            '.btn'
        ];

        document.querySelectorAll(selectors.join(',')).forEach(function (el) {
            const text = (el.innerText || el.value || '').trim().toLowerCase();

            if (
                text === 'continue' ||
                text === 'next' ||
                text === 'finish' ||
                text.includes('continue')
            ) {
                el.style.setProperty('display', 'none', 'important');
                el.style.setProperty('visibility', 'hidden', 'important');
                el.disabled = true;
                el.setAttribute('aria-hidden', 'true');
                el.setAttribute('tabindex', '-1');
            }
        });

        document.querySelectorAll('*').forEach(function (el) {
            const text = (el.innerText || '').trim().toLowerCase();

            if (text === 'or press enter') {
                el.style.setProperty('display', 'none', 'important');
            }
        });
    }

    function boot() {
        initAll();
        hideContinueButtonEverywhere();

        window.setInterval(function () {
            initAll();
            hideContinueButtonEverywhere();
        }, 300);

        new MutationObserver(function () {
            initAll();
            hideContinueButtonEverywhere();
        }).observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
// Course/eLearning listening video injection
(function () {
    'use strict';

    function isFullscreenLesson() {
        return window.location.href.includes('fullscreen=1');
    }

    function isAudio(filename) {
        filename = (filename || '').toLowerCase();
        return filename.endsWith('.mp3') || filename.endsWith('.wav') || filename.endsWith('.ogg');
    }

    function getSlideId() {
        const match = window.location.href.match(/-(\d+)(?:\?|#|$)/);
        return match ? match[1] : false;
    }

    function findFullscreenTarget() {
        return document.querySelector('.o_wslides_fs_article')
            || document.querySelector('.o_wslides_fs_content .container')
            || document.querySelector('.o_wslides_fs_content')
            || document.querySelector('main');
    }

    async function injectCourseVideo() {
        if (!isFullscreenLesson()) {
            return;
        }

        const slideId = getSlideId();
        const target = findFullscreenTarget();

        if (!slideId || !target || document.querySelector('.o_course_listening_gate')) {
            return;
        }

        let data;
        try {
            const response = await fetch('/slides/listening/video_info/' + slideId);
            data = await response.json();
        } catch (error) {
            return;
        }

        if (!data || !data.enabled || !data.media_url) {
            return;
        }

        const mediaHtml = isAudio(data.filename)
            ? `<audio class="o_survey_listening_video_player" preload="auto" style="width:100%;max-width:760px;"><source src="${data.media_url}"/></audio>`
            : `<video class="o_survey_listening_video_player" preload="auto" playsinline="playsinline" style="width:100%;max-width:760px;height:auto;border-radius:10px;background:#000;"><source src="${data.media_url}"/></video>`;

        const wrapper = document.createElement('div');
        wrapper.className = 'o_survey_listening_gate o_course_listening_gate';
        wrapper.dataset.slideId = slideId;
        wrapper.innerHTML = `
            <div style="width:100%;min-height:calc(100vh - 160px);display:flex;flex-direction:column;align-items:center;justify-content:flex-start;padding:28px 24px;background:#111821;">
                <button type="button" class="btn btn-primary o_survey_start_watching_btn mb-3">Start</button>
                <div class="o_survey_listening_video_wrap" style="width:100%;max-width:760px;text-align:center;">
                    ${mediaHtml}
                </div>
            </div>
        `;

        target.innerHTML = '';
        target.appendChild(wrapper);

        const video = wrapper.querySelector('.o_survey_listening_video_player');
        const startButton = wrapper.querySelector('.o_survey_start_watching_btn');

        let started = false;
        let completed = false;
        let maxAllowedTime = 0;

        video.controls = false;
        video.removeAttribute('controls');
        video.preload = 'auto';
        video.autoplay = false;
        video.muted = false;
        video.setAttribute('playsinline', 'true');
        video.setAttribute('webkit-playsinline', 'true');
        video.setAttribute('controlsList', 'nodownload noplaybackrate noremoteplayback nofullscreen');
        video.setAttribute('disablePictureInPicture', 'true');

        startButton.addEventListener('click', function () {
            if (started || completed) {
                return;
            }

            started = true;
            startButton.disabled = true;
            startButton.classList.add('disabled');
            startButton.setAttribute('aria-disabled', 'true');

            video.play().catch(function () {
                started = false;
                startButton.disabled = false;
                startButton.classList.remove('disabled');
                startButton.removeAttribute('aria-disabled');
            });
        });

        video.addEventListener('play', function () {
            if (!completed) {
                started = true;
                startButton.disabled = true;
                startButton.classList.add('disabled');
                startButton.setAttribute('aria-disabled', 'true');
            }
        });

        video.addEventListener('timeupdate', function () {
            if (!completed && video.currentTime > maxAllowedTime) {
                maxAllowedTime = video.currentTime;
            }
        });

        video.addEventListener('seeking', function () {
            if (started && !completed && video.currentTime > maxAllowedTime + 0.15) {
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
            wrapper.dataset.state = 'completed';

            video.pause();
            video.controls = false;
            video.removeAttribute('controls');
            video.style.pointerEvents = 'none';

            wrapper.classList.add('o_survey_video_completed');
        });
    }

    function bootCourseVideo() {
        injectCourseVideo();
        window.setInterval(injectCourseVideo, 700);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bootCourseVideo);
    } else {
        bootCourseVideo();
    }
})();