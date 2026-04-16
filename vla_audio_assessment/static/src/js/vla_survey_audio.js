(function () {
    const stateByQuestion = {};

    function formatTimer(totalSeconds) {
        const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
        const seconds = Math.floor(totalSeconds % 60).toString().padStart(2, '0');
        return `${minutes}:${seconds}`;
    }

    function guessExtension(mimeType) {
        if (!mimeType) return 'webm';
        if (mimeType.includes('ogg')) return 'ogg';
        if (mimeType.includes('mp4')) return 'mp4';
        if (mimeType.includes('mpeg')) return 'mp3';
        return 'webm';
    }

    function getQuestionBox(questionId) {
        return document.querySelector(
            `[data-vla-audio-question][data-question-id="${questionId}"]`
        );
    }

    function getForm(questionId) {
        const box = getQuestionBox(questionId);
        return box ? box.closest('form') : null;
    }

    function getMaxDuration(questionId) {
        const box = getQuestionBox(questionId);
        if (!box) return 60;
        const raw = box.dataset.vlaMaxDuration;
        const parsed = parseInt(raw || '60', 10);
        return Number.isFinite(parsed) && parsed > 0 ? parsed : 60;
    }

    function getElements(questionId) {
        const box = getQuestionBox(questionId);
        if (!box) return null;

        return {
            box,
            hidden: box.querySelector(`[data-vla-hidden="${questionId}"]`),
            start: box.querySelector(`[data-vla-start="${questionId}"]`),
            stop: box.querySelector(`[data-vla-stop="${questionId}"]`),
            reset: box.querySelector(`[data-vla-reset="${questionId}"]`),
            status: box.querySelector(`[data-vla-status="${questionId}"]`),
            timer: box.querySelector(`[data-vla-timer="${questionId}"]`),
            preview: box.querySelector(`[data-vla-preview="${questionId}"]`),
            message: box.querySelector(`[data-vla-message="${questionId}"]`),
        };
    }

    function getRecorderState(questionId) {
        if (!stateByQuestion[questionId]) {
            stateByQuestion[questionId] = {
                mediaRecorder: null,
                mediaStream: null,
                timerInterval: null,
                autoStopTimeout: null,
                startedAt: null,
                chunks: [],
                audioBlob: null,
            };
        }
        return stateByQuestion[questionId];
    }

    function clearMessage(elements) {
        if (!elements || !elements.message) return;
        elements.message.textContent = '';
        elements.message.className = 'alert d-none mt-3';
    }

    function setMessage(elements, text, level) {
        if (!elements || !elements.message) return;
        elements.message.textContent = text;
        elements.message.className = `alert alert-${level} mt-3`;
        elements.message.classList.remove('d-none');
    }

    function stopTracks(state) {
        if (state.mediaStream) {
            state.mediaStream.getTracks().forEach((track) => track.stop());
            state.mediaStream = null;
        }
    }

    function clearTimers(state) {
        if (state.timerInterval) {
            clearInterval(state.timerInterval);
            state.timerInterval = null;
        }
        if (state.autoStopTimeout) {
            clearTimeout(state.autoStopTimeout);
            state.autoStopTimeout = null;
        }
        state.startedAt = null;
    }

    async function uploadAudio(questionId, blob, durationSeconds) {
        const form = getForm(questionId);
        const elements = getElements(questionId);

        if (!form || !elements) {
            throw new Error('Survey form not found.');
        }

        const answerToken = form.dataset.answerToken;
        const csrfTokenInput = form.querySelector('input[name="csrf_token"]');

        const formData = new FormData();
        formData.append('answer_token', answerToken || '');
        formData.append('question_id', String(questionId));
        formData.append('csrf_token', csrfTokenInput ? csrfTokenInput.value : '');
        formData.append('duration_seconds', String(durationSeconds || 0));
        formData.append('audio_blob', blob, `audio_answer.${guessExtension(blob.type)}`);

        const response = await fetch('/survey/vla/audio/upload', {
            method: 'POST',
            body: formData,
            credentials: 'same-origin',
        });

        const raw = await response.text();

        let result = {};
        try {
            result = JSON.parse(raw);
        } catch (e) {
            throw new Error('Upload returned invalid JSON.');
        }

        if (!response.ok || !result.ok) {
            throw new Error(result.error || 'Audio upload failed.');
        }

        return result;
    }

    async function startRecording(questionId) {
        const elements = getElements(questionId);
        const state = getRecorderState(questionId);

        if (!elements) return;

        clearMessage(elements);

        if (state.mediaRecorder && state.mediaRecorder.state === 'recording') {
            return;
        }

        if (!window.isSecureContext) {
            setMessage(elements, 'Microphone recording needs HTTPS or localhost.', 'danger');
            return;
        }

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
            setMessage(elements, 'This browser does not support microphone recording.', 'danger');
            return;
        }

        try {
            state.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            state.chunks = [];
            state.audioBlob = null;

            state.mediaRecorder = new MediaRecorder(state.mediaStream);

            state.mediaRecorder.addEventListener('dataavailable', function (event) {
                if (event.data && event.data.size) {
                    state.chunks.push(event.data);
                }
            });

            state.mediaRecorder.addEventListener('stop', async function () {
                const mimeType = state.mediaRecorder && state.mediaRecorder.mimeType
                    ? state.mediaRecorder.mimeType
                    : 'audio/webm';

                state.audioBlob = new Blob(state.chunks, { type: mimeType });

                const durationSeconds = state.startedAt
                    ? ((Date.now() - state.startedAt) / 1000)
                    : 0;

                clearTimers(state);
                stopTracks(state);

                if (elements.preview && elements.preview.src) {
                    try {
                        URL.revokeObjectURL(elements.preview.src);
                    } catch (e) {}
                }

                if (elements.preview) {
                    elements.preview.src = URL.createObjectURL(state.audioBlob);
                    elements.preview.classList.remove('d-none');
                }

                if (elements.status) {
                    elements.status.textContent = 'Recording ready. Uploading audio...';
                }

                if (elements.reset) {
                    elements.reset.disabled = false;
                }

                if (elements.stop) {
                    elements.stop.disabled = true;
                }

                try {
                    const result = await uploadAudio(questionId, state.audioBlob, durationSeconds);

                    if (elements.hidden) {
                        // one saved answer per question
                        elements.hidden.value = String(result.attachment_id || '');
                    }

                    if (elements.status) {
                        elements.status.textContent = 'Recording uploaded successfully.';
                    }
                } catch (error) {
                    console.error('Upload failed:', error);
                    if (elements.status) {
                        elements.status.textContent = 'Recording saved locally. Upload failed.';
                    }
                    setMessage(elements, error.message || 'Audio upload failed.', 'danger');
                }

                if (elements.start) {
                    elements.start.disabled = false;
                }
            });

            state.mediaRecorder.start();
            state.startedAt = Date.now();

            const maxDuration = getMaxDuration(questionId);

            if (elements.start) elements.start.disabled = true;
            if (elements.stop) elements.stop.disabled = false;
            if (elements.reset) elements.reset.disabled = true;
            if (elements.status) elements.status.textContent = 'Recording in progress...';
            if (elements.timer) elements.timer.textContent = '00:00';

            state.timerInterval = setInterval(function () {
                if (!state.startedAt) return;
                const elapsed = (Date.now() - state.startedAt) / 1000;
                if (elements.timer) {
                    elements.timer.textContent = formatTimer(elapsed);
                }
            }, 250);

            state.autoStopTimeout = setTimeout(function () {
                if (elements.status) {
                    elements.status.textContent = 'Maximum recording time reached. Stopping...';
                }
                stopRecording(questionId);
            }, maxDuration * 1000);

        } catch (error) {
            console.error('Microphone start failed:', error);
            stopTracks(state);
            clearTimers(state);

            if (elements.start) elements.start.disabled = false;
            if (elements.stop) elements.stop.disabled = true;

            setMessage(elements, error.message || 'Microphone access failed.', 'danger');
        }
    }

    function stopRecording(questionId) {
        const elements = getElements(questionId);
        const state = getRecorderState(questionId);

        if (!elements || !state.mediaRecorder) return;

        if (state.mediaRecorder.state !== 'inactive') {
            state.mediaRecorder.stop();
        }

        if (elements.stop) {
            elements.stop.disabled = true;
        }
    }

    function resetRecording(questionId) {
        const elements = getElements(questionId);
        const state = getRecorderState(questionId);

        if (!elements) return;

        if (state.mediaRecorder && state.mediaRecorder.state !== 'inactive') {
            state.mediaRecorder.stop();
        }

        stopTracks(state);
        clearTimers(state);
        state.chunks = [];
        state.audioBlob = null;
        state.mediaRecorder = null;

        clearMessage(elements);

        if (elements.hidden) {
            elements.hidden.value = '';
        }

        if (elements.preview) {
            if (elements.preview.src) {
                try {
                    URL.revokeObjectURL(elements.preview.src);
                } catch (e) {}
            }
            elements.preview.pause();
            elements.preview.removeAttribute('src');
            elements.preview.load();
            elements.preview.classList.add('d-none');
        }

        if (elements.start) elements.start.disabled = false;
        if (elements.stop) elements.stop.disabled = true;
        if (elements.reset) elements.reset.disabled = true;
        if (elements.timer) elements.timer.textContent = '00:00';
        if (elements.status) elements.status.textContent = 'Ready to record.';
    }

    function initExistingBoxes() {
        document.querySelectorAll('[data-vla-audio-question]').forEach((box) => {
            const questionId = box.getAttribute('data-question-id');
            const elements = getElements(questionId);
            if (!elements) return;

            clearMessage(elements);

            if (elements.hidden && elements.hidden.value) {
                if (elements.reset) elements.reset.disabled = false;
                if (elements.status) elements.status.textContent = 'Audio answer ready.';
            }
        });
    }

    document.addEventListener('click', function (event) {
        const startBtn = event.target.closest('[data-vla-start]');
        if (startBtn) {
            event.preventDefault();
            startRecording(startBtn.getAttribute('data-vla-start'));
            return;
        }

        const stopBtn = event.target.closest('[data-vla-stop]');
        if (stopBtn) {
            event.preventDefault();
            stopRecording(stopBtn.getAttribute('data-vla-stop'));
            return;
        }

        const resetBtn = event.target.closest('[data-vla-reset]');
        if (resetBtn) {
            event.preventDefault();
            resetRecording(resetBtn.getAttribute('data-vla-reset'));
        }
    });

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initExistingBoxes);
    } else {
        initExistingBoxes();
    }
})();