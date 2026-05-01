(function () {
    'use strict';

    const GATE_SELECTOR = '.o_survey_listening_gate';

    function getVideo(gate) {
        return gate.querySelector('.o_survey_listening_video_player');
    }

    function getStartButton(gate) {
        return gate.querySelector('.o_survey_start_watching_btn');
    }

    function hardStopAndLockMedia(gate) {
        if (!gate) {
            return;
        }

        const media = getVideo(gate);
        if (!media) {
            return;
        }

        gate.dataset.state = 'completed';
        media.dataset.forceLocked = '1';

        try {
            media.pause();
        } catch (error) {}

        media.controls = false;
        media.removeAttribute('controls');
        media.style.pointerEvents = 'none';
        media.setAttribute('tabindex', '-1');

        gate.classList.add('o_survey_video_completed');

        const note = gate.querySelector('.o_survey_video_locked_note');
        if (note) {
            note.classList.remove('d-none');
        }
    }

    function stopAllListeningMedia() {
        document.querySelectorAll(GATE_SELECTOR).forEach(function (gate) {
            const media = getVideo(gate);
            if (!media) {
                return;
            }

            if (!media.paused || gate.dataset.state === 'playing') {
                hardStopAndLockMedia(gate);
            }
        });
    }

    function isSurveyContinueButton(target) {
        const button = target.closest('button, input[type="submit"], input[type="button"], a');
        if (!button) {
            return false;
        }

        if (button.classList.contains('o_survey_start_watching_btn')) {
            return false;
        }

        const surveyForm = button.closest('.o_survey_form, form[action*="/survey/"]');
        if (!surveyForm) {
            return false;
        }

        const buttonText = (
            (button.textContent || '') + ' ' +
            (button.value || '') + ' ' +
            (button.getAttribute('name') || '')
        ).toLowerCase();

        return (
            button.matches('button[type="submit"], input[type="submit"]') ||
            button.classList.contains('o_survey_next') ||
            button.classList.contains('o_survey_submit') ||
            buttonText.includes('continue') ||
            buttonText.includes('next') ||
            buttonText.includes('submit') ||
            buttonText.includes('finish')
        );
    }

    function bindStopOnContinue() {
        if (window.__surveyListeningStopOnContinueBound) {
            return;
        }

        window.__surveyListeningStopOnContinueBound = true;

        document.addEventListener('click', function (event) {
            if (isSurveyContinueButton(event.target)) {
                stopAllListeningMedia();
            }
        }, true);

        document.addEventListener('submit', function (event) {
            const form = event.target;
            if (form && form.querySelector && form.querySelector(GATE_SELECTOR)) {
                stopAllListeningMedia();
            }
        }, true);
    }

    function lockVideo(gate, video) {
        gate.dataset.state = 'completed';
        video.dataset.forceLocked = '1';
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
            if (
                started ||
                completed ||
                video.dataset.forceLocked === '1' ||
                gate.dataset.state === 'completed'
            ) {
                return;
            }

            started = true;
            gate.dataset.state = 'playing';
            disableStartButton();

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
            if (
                completed ||
                video.dataset.forceLocked === '1' ||
                gate.dataset.state === 'completed'
            ) {
                video.pause();
                return;
            }

            started = true;
            gate.dataset.state = 'playing';
            disableStartButton();
        });

        video.addEventListener('timeupdate', function () {
            if (
                completed ||
                video.dataset.forceLocked === '1' ||
                gate.dataset.state === 'completed'
            ) {
                return;
            }

            if (video.currentTime > maxAllowedTime) {
                maxAllowedTime = video.currentTime;
            }
        });

        video.addEventListener('seeking', function () {
            if (
                !started ||
                completed ||
                video.dataset.forceLocked === '1' ||
                gate.dataset.state === 'completed'
            ) {
                return;
            }

            if (video.currentTime > maxAllowedTime + 0.15) {
                video.currentTime = maxAllowedTime;
            }
        });

        video.addEventListener('pause', function () {
            if (
                completed ||
                video.dataset.forceLocked === '1' ||
                gate.dataset.state === 'completed'
            ) {
                return;
            }

            if (started && video.currentTime < (video.duration || Infinity)) {
                video.play().catch(function () {});
            }
        });

        video.addEventListener('ended', function () {
            completed = true;
            lockVideo(gate, video);
        });
    }

    function initAll() {
        document.querySelectorAll(GATE_SELECTOR).forEach(initGate);
    }

    function boot() {
        bindStopOnContinue();
        initAll();

        window.setInterval(initAll, 300);

        new MutationObserver(initAll).observe(document.body, {
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
        wrapper.dataset.state = 'ready';
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
            if (
                started ||
                completed ||
                video.dataset.forceLocked === '1' ||
                wrapper.dataset.state === 'completed'
            ) {
                return;
            }

            started = true;
            wrapper.dataset.state = 'playing';
            startButton.disabled = true;
            startButton.classList.add('disabled');
            startButton.setAttribute('aria-disabled', 'true');

            video.play().catch(function () {
                started = false;
                wrapper.dataset.state = 'ready';
                startButton.disabled = false;
                startButton.classList.remove('disabled');
                startButton.removeAttribute('aria-disabled');
            });
        });

        video.addEventListener('play', function () {
            if (
                completed ||
                video.dataset.forceLocked === '1' ||
                wrapper.dataset.state === 'completed'
            ) {
                video.pause();
                return;
            }

            started = true;
            wrapper.dataset.state = 'playing';
            startButton.disabled = true;
            startButton.classList.add('disabled');
            startButton.setAttribute('aria-disabled', 'true');
        });

        video.addEventListener('timeupdate', function () {
            if (
                completed ||
                video.dataset.forceLocked === '1' ||
                wrapper.dataset.state === 'completed'
            ) {
                return;
            }

            if (video.currentTime > maxAllowedTime) {
                maxAllowedTime = video.currentTime;
            }
        });

        video.addEventListener('seeking', function () {
            if (
                !started ||
                completed ||
                video.dataset.forceLocked === '1' ||
                wrapper.dataset.state === 'completed'
            ) {
                return;
            }

            if (video.currentTime > maxAllowedTime + 0.15) {
                video.currentTime = maxAllowedTime;
            }
        });

        video.addEventListener('pause', function () {
            if (
                completed ||
                video.dataset.forceLocked === '1' ||
                wrapper.dataset.state === 'completed'
            ) {
                return;
            }

            if (started && video.currentTime < (video.duration || Infinity)) {
                video.play().catch(function () {});
            }
        });

        video.addEventListener('ended', function () {
            completed = true;
            wrapper.dataset.state = 'completed';
            video.dataset.forceLocked = '1';

            video.pause();
            video.controls = false;
            video.removeAttribute('controls');
            video.style.pointerEvents = 'none';
            video.setAttribute('tabindex', '-1');

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