/**
 * camera.js — Face-Recognition Webcam Module
 * =============================================
 * Smart Attendance Management System
 *
 * Loaded only on the Mark Attendance page.
 *
 * Flow:
 *   1. Faculty clicks "Start Camera" → opens webcam via getUserMedia()
 *   2. Every CAPTURE_INTERVAL ms a frame is captured to a hidden <canvas>
 *   3. Frame is sent to /api/recognize-faces/ as base64 JPEG  (AJAX POST)
 *   4. Server returns { recognized_ids: [id, ...], face_rects: [...] }
 *   5. Matching student checkboxes are auto-checked with a visual highlight
 *   6. Faculty reviews + submits the form as usual
 */

(function () {
    'use strict';

    /* ── Config ──────────────────────────────────────────── */
    const CAPTURE_INTERVAL  = 2000;   // ms between recognition attempts
    const API_URL           = '/api/recognize-faces/';
    const JPEG_QUALITY      = 0.75;   // canvas.toDataURL quality
    const OVERLAY_MS        = 1500;   // how long to keep the recognized flash

    /* ── DOM refs (assigned in init) ─────────────────────── */
    let videoEl, canvasEl, ctx, statusEl, recognizedBadge;
    let stream       = null;
    let captureTimer = null;
    let isCapturing  = false;
    let csrfToken    = '';

    /* ── Recognised set (student IDs seen this session) ──── */
    const recognizedThisSession = new Set();

    /* ════════════════════════════════════════════════════════
       INITIALISE — called once DOM is ready
    ════════════════════════════════════════════════════════ */
    function init() {
        videoEl       = document.getElementById('cameraFeed');
        canvasEl      = document.getElementById('captureCanvas');
        statusEl      = document.getElementById('cameraStatus');
        recognizedBadge = document.getElementById('recognizedCount');

        if (!videoEl) return;   // not on the right page

        ctx = canvasEl.getContext('2d');

        csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

        /* Buttons */
        document.getElementById('btnStartCamera')
            ?.addEventListener('click', startCamera);
        document.getElementById('btnStopCamera')
            ?.addEventListener('click', stopCamera);
        document.getElementById('btnCaptureNow')
            ?.addEventListener('click', captureAndRecognize);
    }

    /* ════════════════════════════════════════════════════════
       START CAMERA
    ════════════════════════════════════════════════════════ */
    async function startCamera() {
        setStatus('info', '<i class="bi bi-hourglass-split me-1"></i>Requesting camera…');

        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
                audio: false
            });
        } catch (err) {
            setStatus('danger',
                `<i class="bi bi-exclamation-triangle me-1"></i>` +
                `Camera access denied: ${err.message}. ` +
                `Please allow camera permission and try again.`
            );
            return;
        }

        videoEl.srcObject = stream;
        videoEl.play();

        document.getElementById('cameraContainer').classList.remove('d-none');
        document.getElementById('btnStartCamera').classList.add('d-none');
        document.getElementById('btnStopCamera').classList.remove('d-none');
        document.getElementById('btnCaptureNow').classList.remove('d-none');

        setStatus('success',
            '<i class="bi bi-camera-video me-1"></i>' +
            'Camera active — scanning automatically every 2 seconds.'
        );

        isCapturing  = true;
        captureTimer = setInterval(captureAndRecognize, CAPTURE_INTERVAL);
    }

    /* ════════════════════════════════════════════════════════
       STOP CAMERA
    ════════════════════════════════════════════════════════ */
    function stopCamera() {
        isCapturing = false;
        clearInterval(captureTimer);

        if (stream) {
            stream.getTracks().forEach(t => t.stop());
            stream = null;
        }
        videoEl.srcObject = null;

        document.getElementById('cameraContainer').classList.add('d-none');
        document.getElementById('btnStartCamera').classList.remove('d-none');
        document.getElementById('btnStopCamera').classList.add('d-none');
        document.getElementById('btnCaptureNow').classList.add('d-none');

        setStatus('secondary',
            '<i class="bi bi-camera-video-off me-1"></i>Camera stopped.'
        );
    }

    /* ════════════════════════════════════════════════════════
       CAPTURE A FRAME AND SEND TO SERVER
    ════════════════════════════════════════════════════════ */
    async function captureAndRecognize() {
        if (!stream || !isCapturing) return;

        /* Draw current video frame to hidden canvas */
        canvasEl.width  = videoEl.videoWidth  || 640;
        canvasEl.height = videoEl.videoHeight || 480;
        ctx.drawImage(videoEl, 0, 0, canvasEl.width, canvasEl.height);

        const imageData = canvasEl.toDataURL('image/jpeg', JPEG_QUALITY);

        /* POST to Django view */
        let data;
        try {
            const resp = await fetch(API_URL, {
                method:  'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: 'image=' + encodeURIComponent(imageData)
            });
            data = await resp.json();
        } catch (fetchErr) {
            console.error('Face API error:', fetchErr);
            return;
        }

        if (data.error) {
            setStatus('warning',
                `<i class="bi bi-exclamation-circle me-1"></i>${data.error}`
            );
            return;
        }

        /* Mark matching students as present */
        if (data.recognized_ids && data.recognized_ids.length > 0) {
            data.recognized_ids.forEach(sid => markStudentPresent(sid));
            setStatus('success',
                `<i class="bi bi-person-check me-1"></i>` +
                `Recognized ${data.recognized_ids.length} face(s) this scan. ` +
                `Total this session: ${recognizedThisSession.size}`
            );
            updateRecognizedBadge();
        } else {
            setStatus('secondary',
                '<i class="bi bi-camera me-1"></i>' +
                `Scanning… (${recognizedThisSession.size} detected so far)`
            );
        }

        /* Draw face bounding boxes on overlay canvas */
        drawFaceBoxes(data.face_rects || []);
    }

    /* ════════════════════════════════════════════════════════
       MARK A STUDENT PRESENT IN THE FORM TABLE
    ════════════════════════════════════════════════════════ */
    function markStudentPresent(studentId) {
        const cb  = document.getElementById('s-' + studentId);
        const row = document.getElementById('row-' + studentId);

        if (!cb || !row) return;   // student not in current list

        if (!cb.checked) {
            cb.checked = true;
            row.classList.add('present-row');

            /* Fire the existing updateRow function so counters stay in sync */
            if (typeof updateRow === 'function') {
                updateRow(studentId, cb);
            }

            /* Flash animation to draw faculty's eye */
            row.classList.add('face-recognized-flash');
            setTimeout(() => row.classList.remove('face-recognized-flash'), OVERLAY_MS);
        }

        recognizedThisSession.add(studentId);
    }

    /* ════════════════════════════════════════════════════════
       DRAW BOUNDING BOXES OVER THE VIDEO FEED
    ════════════════════════════════════════════════════════ */
    function drawFaceBoxes(rects) {
        const overlay = document.getElementById('faceOverlay');
        if (!overlay) return;

        const octx = overlay.getContext('2d');
        overlay.width  = videoEl.videoWidth  || 640;
        overlay.height = videoEl.videoHeight || 480;
        octx.clearRect(0, 0, overlay.width, overlay.height);

        octx.strokeStyle = '#00ff88';
        octx.lineWidth   = 3;
        octx.font        = '14px monospace';
        octx.fillStyle   = '#00ff88';

        rects.forEach(r => {
            octx.strokeRect(r.x, r.y, r.w, r.h);
            octx.fillText('Face', r.x + 4, r.y - 6);
        });
    }

    /* ════════════════════════════════════════════════════════
       HELPERS
    ════════════════════════════════════════════════════════ */
    function setStatus(type, html) {
        if (!statusEl) return;
        statusEl.className = `alert alert-${type} py-2 mb-0 small`;
        statusEl.innerHTML = html;
    }

    function updateRecognizedBadge() {
        if (recognizedBadge) {
            recognizedBadge.textContent = recognizedThisSession.size + ' auto-marked';
        }
    }

    /* ── Boot ─────────────────────────────────────────────── */
    document.addEventListener('DOMContentLoaded', init);

})();
