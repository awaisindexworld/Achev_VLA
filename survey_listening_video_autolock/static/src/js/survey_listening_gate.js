(function () {
    'use strict';

    const GATE_SELECTOR = '.o_survey_listening_gate';

    function getVideo(gate) {
        return gate.querySelector('.o_survey_listening_video_player');
    }

    function getStartButton(gate) {
        return gate.querySelector('.o_survey_start_watching_btn');
    }

    function getStopButton(gate) {
        return gate.querySelector('.o_survey_stop_watching_btn');
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
        } catch (error) {
        }

        media.controls = false;
        media.removeAttribute('controls');
        media.style.pointerEvents = 'none';
        media.setAttribute('tabindex', '-1');

        gate.classList.add('o_survey_video_completed');

        const stopBtn = getStopButton(gate);
        if (stopBtn) {
            stopBtn.classList.add('d-none');
        }

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

        if (button.classList.contains('o_survey_start_watching_btn') ||
            button.classList.contains('o_survey_stop_watching_btn')) {
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

        const stopBtn = getStopButton(gate);
        if (stopBtn) {
            stopBtn.classList.add('d-none');
        }

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

        const video = getVideo(gate);
        const startButton = getStartButton(gate);
        const stopButton = getStopButton(gate);

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

        const questionId = gate.dataset.questionId;
        const slideId = gate.dataset.slideId;
        const storageKey = questionId ? 'vlga_q_' + questionId : (slideId ? 'vlga_s_' + slideId : null);
        const savedState = storageKey ? sessionStorage.getItem(storageKey) : null;

        let started = savedState === 'started' || savedState === 'paused';
        let completed = savedState === 'completed';
        let userPaused = savedState === 'paused';
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

        function showStopButton() {
            if (stopButton) {
                stopButton.classList.remove('d-none');
            }
        }

        function hideStopButton() {
            if (stopButton) {
                stopButton.classList.add('d-none');
            }
        }

        // Restore completed state: lock video and disable button
        if (completed) {
            lockVideo(gate, video);
            disableStartButton();
            return;
        }

        if (userPaused) {
            gate.dataset.state = 'paused';
            enableStartButton();
            hideStopButton();
        } else if (started) {
            gate.dataset.state = 'playing';
            disableStartButton();
            showStopButton();
        } else {
            gate.dataset.state = 'ready';
        }

        startButton.addEventListener('click', function () {
            if (
                completed ||
                video.dataset.forceLocked === '1' ||
                gate.dataset.state === 'completed'
            ) {
                return;
            }

            // Resume after user paused via Stop button
            if (userPaused) {
                userPaused = false;
                gate.dataset.state = 'playing';
                disableStartButton();
                showStopButton();
                if (storageKey) {
                    sessionStorage.setItem(storageKey, 'started');
                }
                video.play().catch(function () {
                    userPaused = true;
                    gate.dataset.state = 'paused';
                    enableStartButton();
                    hideStopButton();
                    if (storageKey) {
                        sessionStorage.setItem(storageKey, 'paused');
                    }
                });
                return;
            }

            if (started) {
                return;
            }

            started = true;
            gate.dataset.state = 'playing';
            disableStartButton();
            showStopButton();

            if (storageKey) {
                sessionStorage.setItem(storageKey, 'started');
            }

            const playPromise = video.play();
            if (playPromise && typeof playPromise.catch === 'function') {
                playPromise.catch(function () {
                    started = false;
                    gate.dataset.state = 'ready';
                    enableStartButton();
                    hideStopButton();
                    if (storageKey) {
                        sessionStorage.removeItem(storageKey);
                    }
                });
            }
        });

        if (stopButton) {
            stopButton.addEventListener('click', function () {
                if (
                    !started ||
                    completed ||
                    video.dataset.forceLocked === '1' ||
                    gate.dataset.state === 'completed'
                ) {
                    return;
                }

                userPaused = true;
                gate.dataset.state = 'paused';
                hideStopButton();
                enableStartButton();
                if (storageKey) {
                    sessionStorage.setItem(storageKey, 'paused');
                }
                video.pause();
            });
        }

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
            showStopButton();
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

            // Stop button deliberately paused the video — do not auto-resume.
            if (userPaused) {
                return;
            }

            if (started && video.currentTime < (video.duration || Infinity)) {
                video.play().catch(function () {
                });
            }
        });

        video.addEventListener('ended', function () {
            completed = true;
            lockVideo(gate, video);
            disableStartButton();
            if (storageKey) {
                sessionStorage.setItem(storageKey, 'completed');
            }
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
        wrapper.innerHTML = `
            <div style="width:100%;min-height:calc(100vh - 160px);display:flex;flex-direction:column;align-items:center;justify-content:flex-start;padding:28px 24px;background:#111821;">
                <div style="display:flex;gap:8px;margin-bottom:12px;">
                    <button type="button" class="btn btn-primary o_survey_start_watching_btn">Start</button>
                    <button type="button" class="btn btn-secondary o_survey_stop_watching_btn d-none">Stop</button>
                </div>
                <div class="o_survey_listening_video_wrap" style="width:100%;max-width:760px;text-align:center;">
                    ${mediaHtml}
                </div>
            </div>
        `;

        target.innerHTML = '';
        target.appendChild(wrapper);

        const video = wrapper.querySelector('.o_survey_listening_video_player');
        const startButton = wrapper.querySelector('.o_survey_start_watching_btn');
        const stopButton = wrapper.querySelector('.o_survey_stop_watching_btn');

        const storageKey = 'vlga_s_' + slideId;
        const savedState = sessionStorage.getItem(storageKey);

        let started = savedState === 'started' || savedState === 'paused';
        let completed = savedState === 'completed';
        let userPaused = savedState === 'paused';
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

        function showStopButton() {
            stopButton.classList.remove('d-none');
        }

        function hideStopButton() {
            stopButton.classList.add('d-none');
        }

        // Restore completed state: lock video and hide stop button
        if (completed) {
            wrapper.dataset.state = 'completed';
            video.dataset.forceLocked = '1';
            video.controls = false;
            video.removeAttribute('controls');
            video.style.pointerEvents = 'none';
            video.setAttribute('tabindex', '-1');
            wrapper.classList.add('o_survey_video_completed');
            disableStartButton();
            hideStopButton();
            return;
        }

        if (userPaused) {
            wrapper.dataset.state = 'paused';
            enableStartButton();
            hideStopButton();
        } else if (started) {
            wrapper.dataset.state = 'playing';
            disableStartButton();
            showStopButton();
        } else {
            wrapper.dataset.state = 'ready';
        }

        startButton.addEventListener('click', function () {
            if (
                completed ||
                video.dataset.forceLocked === '1' ||
                wrapper.dataset.state === 'completed'
            ) {
                return;
            }

            // Resume after user paused via Stop button
            if (userPaused) {
                userPaused = false;
                wrapper.dataset.state = 'playing';
                disableStartButton();
                showStopButton();
                sessionStorage.setItem(storageKey, 'started');
                video.play().catch(function () {
                    userPaused = true;
                    wrapper.dataset.state = 'paused';
                    enableStartButton();
                    hideStopButton();
                    sessionStorage.setItem(storageKey, 'paused');
                });
                return;
            }

            if (started) {
                return;
            }

            started = true;
            wrapper.dataset.state = 'playing';
            disableStartButton();
            showStopButton();
            sessionStorage.setItem(storageKey, 'started');

            video.play().catch(function () {
                started = false;
                wrapper.dataset.state = 'ready';
                enableStartButton();
                hideStopButton();
                sessionStorage.removeItem(storageKey);
            });
        });

        stopButton.addEventListener('click', function () {
            if (
                !started ||
                completed ||
                video.dataset.forceLocked === '1' ||
                wrapper.dataset.state === 'completed'
            ) {
                return;
            }

            userPaused = true;
            wrapper.dataset.state = 'paused';
            hideStopButton();
            enableStartButton();
            sessionStorage.setItem(storageKey, 'paused');
            video.pause();
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
            disableStartButton();
            showStopButton();
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

            // Stop button deliberately paused the video — do not auto-resume.
            if (userPaused) {
                return;
            }

            if (started && video.currentTime < (video.duration || Infinity)) {
                video.play().catch(function () {
                });
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
            disableStartButton();
            hideStopButton();
            sessionStorage.setItem(storageKey, 'completed');
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
