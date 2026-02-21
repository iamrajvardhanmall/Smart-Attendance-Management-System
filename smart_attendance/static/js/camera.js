
(function () {
    'use strict';
    const CAPTURE_INTERVAL  = 2000;   
    const API_URL           = '/api/recognize-faces/';
    const JPEG_QUALITY      = 0.75;   
    const OVERLAY_MS        = 1500;   

    let videoEl, canvasEl, ctx, statusEl, recognizedBadge;
    let stream       = null;
    let captureTimer = null;
    let isCapturing  = false;
    let csrfToken    = '';

    const recognizedThisSession = new Set();
    function init() {
        videoEl       = document.getElementById('cameraFeed');
        canvasEl      = document.getElementById('captureCanvas');
        statusEl      = document.getElementById('cameraStatus');
        recognizedBadge = document.getElementById('recognizedCount');

        if (!videoEl) return;   
        ctx = canvasEl.getContext('2d');
        csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

        document.getElementById('btnStartCamera')
            ?.addEventListener('click', startCamera);
        document.getElementById('btnStopCamera')
            ?.addEventListener('click', stopCamera);
        document.getElementById('btnCaptureNow')
            ?.addEventListener('click', captureAndRecognize);
    }

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

    async function captureAndRecognize() {
        if (!stream || !isCapturing) return;
        canvasEl.width  = videoEl.videoWidth  || 640;
        canvasEl.height = videoEl.videoHeight || 480;
        ctx.drawImage(videoEl, 0, 0, canvasEl.width, canvasEl.height);
        const imageData = canvasEl.toDataURL('image/jpeg', JPEG_QUALITY);
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
        drawFaceBoxes(data.face_rects || []);
    }

    function markStudentPresent(studentId) {
        const cb  = document.getElementById('s-' + studentId);
        const row = document.getElementById('row-' + studentId);

        if (!cb || !row) return; 

        if (!cb.checked) {
            cb.checked = true;
            row.classList.add('present-row');
            if (typeof updateRow === 'function') {
                updateRow(studentId, cb);
            }
            row.classList.add('face-recognized-flash');
            setTimeout(() => row.classList.remove('face-recognized-flash'), OVERLAY_MS);
        }

        recognizedThisSession.add(studentId);
    }

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

    document.addEventListener('DOMContentLoaded', init);

})();
