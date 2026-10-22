/**
 * SmartScan AI - Advanced Tactical Electronic Warfare Dashboard
 * Author: SmartScan AI Team
 * 
 * Features:
 * - Dual Chart.js Time-Domain Oscillogram & Frequency-Domain FFT Spectrum
 * - HTML5 Canvas Plan Position Indicator (PPI) Circular Radar Scope with Phosphor Decay
 * - 2D Time-Frequency Spectrogram Waterfall Heatmap (Thermal Palette)
 * - Web Audio API RF Demodulator (Sonification: Hear the Radar Chirp, CW Tone, and Anomaly)
 * - Live Continuous Spectrum Sweep Mode
 * - Slide 9 Verification Benchmark Modal
 */

let waveformChart = null;
let spectrumChart = null;
let activeSampleId = null;
let currentSampleData = null;

// Live Sweep Mode State
let isLiveSweepActive = false;
let liveSweepTimer = null;

// Audio Synthesizer State
let audioCtx = null;
let audioNodes = [];
let isAudioPlaying = false;

// Radar Animation State
let radarAngle = 0;
let radarAnimationId = null;
let radarTargets = [];

document.addEventListener("DOMContentLoaded", () => {
    initCharts();
    initRadarScope();
    fetchQueue(true);

    // Header Controls
    document.getElementById("btn-toggle-sweep").addEventListener("click", toggleLiveSweep);
    document.getElementById("btn-inject-anomaly").addEventListener("click", () => injectSingle("ANOMALY_UNKNOWN"));
    document.getElementById("btn-inject-radar").addEventListener("click", () => injectSingle("PULSED_RADAR"));
    document.getElementById("btn-inject-chirp").addEventListener("click", () => injectSingle("CHIRP_LFM"));
    document.getElementById("btn-simulate-batch").addEventListener("click", simulateBatch);
    document.getElementById("btn-clear-queue").addEventListener("click", clearQueue);
    document.getElementById("btn-run-benchmark").addEventListener("click", openBenchmarkModal);
    document.getElementById("btn-mark-reviewed").addEventListener("click", markCurrentReviewed);
    document.getElementById("btn-close-modal").addEventListener("click", closeBenchmarkModal);

    // Audio Demodulator Button
    document.getElementById("btn-toggle-audio").addEventListener("click", toggleAudioPlayback);
});

// ==========================================
// 1. CHART.JS INITIALIZATION
// ==========================================

function initCharts() {
    const commonChartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 300 },
        scales: {
            x: {
                grid: { color: "rgba(0, 240, 255, 0.05)" },
                ticks: { color: "#62788f", font: { size: 9, family: "Courier New" } }
            },
            y: {
                grid: { color: "rgba(0, 240, 255, 0.05)" },
                ticks: { color: "#62788f", font: { size: 9, family: "Courier New" } }
            }
        },
        plugins: {
            legend: { display: false }
        }
    };

    // 1. Time-Domain Oscillogram
    const ctxWave = document.getElementById("waveformCanvas").getContext("2d");
    waveformChart = new Chart(ctxWave, {
        type: "line",
        data: {
            labels: [],
            datasets: [{
                label: "Voltage",
                data: [],
                borderColor: "#00f0ff",
                borderWidth: 1.5,
                pointRadius: 0,
                tension: 0.05
            }]
        },
        options: {
            ...commonChartOptions,
            scales: {
                ...commonChartOptions.scales,
                x: { ...commonChartOptions.scales.x, title: { display: true, text: "TIME (µs)", color: "#62788f", font: { size: 9 } } },
                y: { ...commonChartOptions.scales.y, title: { display: true, text: "AMPLITUDE", color: "#62788f", font: { size: 9 } } }
            }
        }
    });

    // 2. Frequency-Domain FFT Spectrum
    const ctxSpec = document.getElementById("spectrumCanvas").getContext("2d");
    spectrumChart = new Chart(ctxSpec, {
        type: "line",
        data: {
            labels: [],
            datasets: [{
                label: "Power (dB)",
                data: [],
                borderColor: "#0088ff",
                backgroundColor: "rgba(0, 136, 255, 0.12)",
                fill: true,
                borderWidth: 1.5,
                pointRadius: 0,
                tension: 0.05
            }]
        },
        options: {
            ...commonChartOptions,
            scales: {
                ...commonChartOptions.scales,
                x: { ...commonChartOptions.scales.x, title: { display: true, text: "FREQUENCY (MHz)", color: "#62788f", font: { size: 9 } } },
                y: { ...commonChartOptions.scales.y, title: { display: true, text: "POWER (dB)", color: "#62788f", font: { size: 9 } } }
            }
        }
    });
}

// ==========================================
// 2. RADAR PPI SCOPE (CANVAS ANIMATION)
// ==========================================

function initRadarScope() {
    const canvas = document.getElementById("radarCanvas");
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2;
    const cy = h / 2;
    const radius = w / 2 - 8;

    function drawRadar() {
        ctx.fillStyle = "rgba(7, 13, 20, 0.18)";
        ctx.fillRect(0, 0, w, h);

        // Outer Range Rings
        ctx.strokeStyle = "rgba(0, 240, 255, 0.2)";
        ctx.lineWidth = 1;
        for (let r = radius / 3; r <= radius; r += radius / 3) {
            ctx.beginPath();
            ctx.arc(cx, cy, r, 0, Math.PI * 2);
            ctx.stroke();
        }

        // Crosshairs
        ctx.beginPath();
        ctx.moveTo(cx - radius, cy);
        ctx.lineTo(cx + radius, cy);
        ctx.moveTo(cx, cy - radius);
        ctx.lineTo(cx, cy + radius);
        ctx.stroke();

        // Rotating Sweep Beam
        radarAngle += 0.04;
        if (radarAngle >= Math.PI * 2) radarAngle = 0;

        const sweepX = cx + Math.cos(radarAngle) * radius;
        const sweepY = cy + Math.sin(radarAngle) * radius;

        ctx.strokeStyle = "rgba(0, 255, 136, 0.9)";
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(sweepX, sweepY);
        ctx.stroke();

        // Sweep Glow Gradient
        const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
        gradient.addColorStop(0, "rgba(0, 255, 136, 0.2)");
        gradient.addColorStop(1, "rgba(0, 255, 136, 0.0)");
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.arc(cx, cy, radius, radarAngle - 0.35, radarAngle);
        ctx.closePath();
        ctx.fill();

        // Draw Target Blips
        radarTargets.forEach(t => {
            const bx = cx + Math.cos(t.angle) * t.distance;
            const by = cy + Math.sin(t.angle) * t.distance;

            const angleDiff = Math.abs((radarAngle - t.angle + Math.PI * 2) % (Math.PI * 2));
            const isIlluminated = angleDiff < 0.25;

            ctx.fillStyle = t.isAnomaly ? "#ff2a5f" : (t.priority > 60 ? "#ffaa00" : "#00ff88");
            ctx.shadowColor = ctx.fillStyle;
            ctx.shadowBlur = isIlluminated ? 12 : 3;

            ctx.beginPath();
            ctx.arc(bx, by, isIlluminated ? 3.5 : 2.5, 0, Math.PI * 2);
            ctx.fill();
            ctx.shadowBlur = 0;
        });

        radarAnimationId = requestAnimationFrame(drawRadar);
    }

    drawRadar();
}

function updateRadarTargets(items) {
    // Distribute current queue items across radar bearings
    radarTargets = items.slice(0, 10).map((item, idx) => {
        const hash = item.sample_id.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0);
        const angle = (hash % 360) * (Math.PI / 180);
        const distance = 15 + ((hash * 7) % 40);
        return {
            id: item.sample_id,
            angle: angle,
            distance: distance,
            isAnomaly: item.is_anomaly,
            priority: item.priority_score
        };
    });
}

// ==========================================
// 3. 2D TIME-FREQUENCY SPECTROGRAM HEATMAP
// ==========================================

function renderSpectrogram(spectrogramData) {
    const canvas = document.getElementById("waterfallCanvas");
    if (!canvas || !spectrogramData || !spectrogramData.matrix) return;

    const ctx = canvas.getContext("2d");
    const matrix = spectrogramData.matrix;
    const numFreqs = matrix.length;
    const numTimes = matrix[0].length;

    // Set internal resolution matching DOM size
    canvas.width = canvas.parentElement.clientWidth || 300;
    canvas.height = canvas.parentElement.clientHeight || 110;

    const w = canvas.width;
    const h = canvas.height;
    const cellW = w / numTimes;
    const cellH = h / numFreqs;

    for (let r = 0; r < numFreqs; r++) {
        for (let c = 0; c < numTimes; c++) {
            const val = matrix[r][c]; // [0.0, 1.0]
            ctx.fillStyle = getThermalColor(val);
            // Flip Y so low frequencies are at the bottom
            ctx.fillRect(c * cellW, h - (r + 1) * cellH, cellW + 1, cellH + 1);
        }
    }
}

// Thermal / Inferno Colormap
function getThermalColor(val) {
    if (val < 0.2) {
        return `rgb(${Math.floor(val * 5 * 20)}, 5, ${Math.floor(val * 5 * 60)})`;
    } else if (val < 0.5) {
        const t = (val - 0.2) / 0.3;
        return `rgb(${Math.floor(20 + t * 140)}, ${Math.floor(5 + t * 40)}, ${Math.floor(60 + t * 180)})`;
    } else if (val < 0.8) {
        const t = (val - 0.5) / 0.3;
        return `rgb(${Math.floor(160 + t * 90)}, ${Math.floor(45 + t * 140)}, 40)`;
    } else {
        const t = (val - 0.8) / 0.2;
        return `rgb(255, ${Math.floor(185 + t * 70)}, ${Math.floor(40 + t * 215)})`;
    }
}

// ==========================================
// 4. WEB AUDIO RF DEMODULATOR (SONIFICATION)
// ==========================================

function toggleAudioPlayback() {
    if (isAudioPlaying) {
        stopAudio();
    } else {
        playSignalAudio();
    }
}

function stopAudio() {
    audioNodes.forEach(node => {
        try { node.stop(); } catch (e) {}
        try { node.disconnect(); } catch (e) {}
    });
    audioNodes = [];
    isAudioPlaying = false;
    document.getElementById("btn-toggle-audio").innerHTML = "🔊 PLAY AUDIO";
    document.getElementById("btn-toggle-audio").classList.remove("active");
}

function playSignalAudio() {
    if (!currentSampleData) return;

    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === "suspended") {
        audioCtx.resume();
    }

    stopAudio();
    isAudioPlaying = true;
    document.getElementById("btn-toggle-audio").innerHTML = "⏹️ STOP AUDIO";
    document.getElementById("btn-toggle-audio").classList.add("active");

    const stype = currentSampleData.signal_type;
    const now = audioCtx.currentTime;

    if (stype === "CW") {
        // Pure sinusoidal tone with gentle amplitude
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(880, now);
        gain.gain.setValueAtTime(0.15, now);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start(now);
        audioNodes.push(osc, gain);

    } else if (stype === "CHIRP_LFM") {
        // Ascending frequency chirp
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = "sawtooth";
        gain.gain.setValueAtTime(0.12, now);

        for (let i = 0; i < 8; i++) {
            const t = now + i * 0.4;
            osc.frequency.setValueAtTime(400, t);
            osc.frequency.exponentialRampToValueAtTime(2400, t + 0.35);
        }

        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start(now);
        audioNodes.push(osc, gain);

    } else if (stype === "PULSED_RADAR") {
        // High-frequency clicking pulse train
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(1200, now);
        gain.gain.setValueAtTime(0, now);

        // 8 pulses per second
        for (let i = 0; i < 20; i++) {
            const t = now + i * 0.15;
            gain.gain.setValueAtTime(0.2, t);
            gain.gain.setValueAtTime(0, t + 0.03);
        }

        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start(now);
        audioNodes.push(osc, gain);

    } else if (stype === "FREQ_HOPPING") {
        // Fast musical jumping arpeggio
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = "square";
        gain.gain.setValueAtTime(0.08, now);

        const notes = [500, 750, 1100, 620, 950, 1300];
        for (let i = 0; i < 24; i++) {
            const t = now + i * 0.08;
            const freq = notes[i % notes.length];
            osc.frequency.setValueAtTime(freq, t);
        }

        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start(now);
        audioNodes.push(osc, gain);

    } else if (stype === "ANOMALY_UNKNOWN") {
        // Exotic FM modulation warble with pitch wobble
        const carrier = audioCtx.createOscillator();
        const mod = audioCtx.createOscillator();
        const modGain = audioCtx.createGain();
        const mainGain = audioCtx.createGain();

        carrier.type = "sawtooth";
        carrier.frequency.setValueAtTime(450, now);

        mod.type = "sine";
        mod.frequency.setValueAtTime(15, now);
        modGain.gain.setValueAtTime(280, now);

        mod.connect(carrier.frequency);
        carrier.connect(mainGain);
        mainGain.gain.setValueAtTime(0.18, now);
        mainGain.connect(audioCtx.destination);

        mod.start(now);
        carrier.start(now);
        audioNodes.push(carrier, mod, modGain, mainGain);

    } else {
        // Background noise static
        const bufferSize = audioCtx.sampleRate * 2;
        const buffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
        const data = buffer.getChannelData(0);
        for (let i = 0; i < bufferSize; i++) {
            data[i] = (Math.random() * 2 - 1) * 0.08;
        }

        const whiteNoise = audioCtx.createBufferSource();
        whiteNoise.buffer = buffer;
        whiteNoise.loop = true;
        whiteNoise.connect(audioCtx.destination);
        whiteNoise.start(now);
        audioNodes.push(whiteNoise);
    }
}

// ==========================================
// 5. QUEUE FETCHING & SELECTION
// ==========================================

async function fetchQueue(selectFirst = false) {
    try {
        const response = await fetch("/api/queue");
        const data = await response.json();
        if (data.status === "success") {
            renderQueue(data.queue, selectFirst);
            updateRadarTargets(data.queue);
        }
    } catch (err) {
        console.error("Failed to fetch queue:", err);
    }
}

function renderQueue(items, selectFirst) {
    const queueList = document.getElementById("queue-list");
    document.getElementById("queue-count").textContent = `${items.length} SIGNALS`;
    queueList.innerHTML = "";

    if (items.length === 0) {
        queueList.innerHTML = `<div style="text-align: center; color: #62788f; padding: 30px; font-family: var(--font-mono); font-size: 11px;">[ SPECTRUM QUEUE VACANT ]<br>CLICK 'BATCH' OR 'LIVE SWEEP'</div>`;
        return;
    }

    items.forEach((item, index) => {
        const card = document.createElement("div");
        const badgeLevel = item.priority_level.toLowerCase();
        card.className = `queue-card ${badgeLevel}-badge ${item.sample_id === activeSampleId ? "active" : ""} ${item.reviewed ? "reviewed" : ""}`;
        card.dataset.id = item.sample_id;

        card.innerHTML = `
            <div class="card-top">
                <span class="card-rank">#${index + 1} &bull; ARR #${item.original_arrival_order}</span>
                <span class="hud-badge badge-${badgeLevel}">${item.priority_level}</span>
            </div>
            <div class="card-title">${item.predicted_type}</div>
            <div class="card-bottom">
                <span>PRIORITY: <strong class="card-score">${item.priority_score}</strong></span>
                <span>ANOMALY: ${(item.anomaly_score * 100).toFixed(0)}%</span>
            </div>
        `;

        card.addEventListener("click", () => selectSample(item.sample_id));
        queueList.appendChild(card);
    });

    if (selectFirst && items.length > 0) {
        selectSample(items[0].sample_id);
    } else if (activeSampleId) {
        const activeCard = queueList.querySelector(`[data-id="${activeSampleId}"]`);
        if (activeCard) activeCard.classList.add("active");
    }
}

async function selectSample(sampleId) {
    activeSampleId = sampleId;

    document.querySelectorAll(".queue-card").forEach(c => c.classList.remove("active"));
    const selectedCard = document.querySelector(`.queue-card[data-id="${sampleId}"]`);
    if (selectedCard) selectedCard.classList.add("active");

    try {
        const res = await fetch(`/api/sample/${sampleId}`);
        const result = await res.json();
        if (result.status === "success") {
            currentSampleData = result.data;
            updateDashboardWithSample(result.data);
            if (isAudioPlaying) {
                playSignalAudio(); // Switch audio to new signal
            }
        }
    } catch (err) {
        console.error("Error loading sample details:", err);
    }
}

function updateDashboardWithSample(sampleData) {
    const feat = sampleData.features;
    const pred = sampleData.prediction;
    const prio = sampleData.prioritization;

    // 1. Diagnostics Pane
    document.getElementById("diag-sample-id").textContent = sampleData.sample_id;
    document.getElementById("diag-pred-type").textContent = prio.predicted_type;
    document.getElementById("diag-prio-score").textContent = prio.priority_score;
    document.getElementById("diag-anomaly-score").textContent = `${(pred.anomaly_score * 100).toFixed(1)}%`;
    document.getElementById("diag-confidence").textContent = `${(pred.confidence * 100).toFixed(1)}%`;
    document.getElementById("diag-center-freq").textContent = `${feat.center_frequency_mhz} MHz`;
    document.getElementById("diag-bandwidth").textContent = `${feat.bandwidth_3db_mhz} MHz`;
    document.getElementById("diag-snr").textContent = `${feat.estimated_snr_db} dB`;
    document.getElementById("diag-entropy").textContent = feat.spectral_entropy;

    // 2. Explainability
    const explainList = document.getElementById("explain-list");
    explainList.innerHTML = "";
    prio.explanations.forEach(e => {
        const el = document.createElement("div");
        el.className = "explain-card";
        el.innerHTML = `
            <div class="explain-head">
                <span>${e.factor}</span>
                <span class="explain-score">${e.points}</span>
            </div>
            <div class="explain-text">${e.description}</div>
        `;
        explainList.appendChild(el);
    });

    // 3. Time-Domain Waveform Chart
    const timeLabels = sampleData.time_preview.map(t => (t * 1e6).toFixed(1));
    waveformChart.data.labels = timeLabels;
    waveformChart.data.datasets[0].data = sampleData.waveform_preview;
    waveformChart.data.datasets[0].borderColor = pred.is_anomaly ? "#ff2a5f" : "#00f0ff";
    waveformChart.update();

    // 4. Frequency-Domain FFT Spectrum Chart
    spectrumChart.data.labels = sampleData.frequencies_mhz.map(f => f.toFixed(2));
    spectrumChart.data.datasets[0].data = sampleData.power_db;
    spectrumChart.update();

    // 5. 2D Spectrogram Waterfall Heatmap
    if (sampleData.spectrogram) {
        renderSpectrogram(sampleData.spectrogram);
    }
}

// ==========================================
// 6. ACTION CONTROLS & LIVE SWEEP
// ==========================================

function toggleLiveSweep() {
    isLiveSweepActive = !isLiveSweepActive;
    const btn = document.getElementById("btn-toggle-sweep");
    const statusText = document.getElementById("hud-sweep-status");

    if (isLiveSweepActive) {
        btn.textContent = "⏹️ LIVE SWEEP: ON";
        btn.classList.add("active");
        statusText.textContent = "SCANNING";
        statusText.style.color = "#00ff88";

        liveSweepTimer = setInterval(async () => {
            await simulateBatch();
        }, 3500);
    } else {
        btn.textContent = "▶ LIVE SWEEP: OFF";
        btn.classList.remove("active");
        statusText.textContent = "PAUSED";
        statusText.style.color = "#62788f";
        clearInterval(liveSweepTimer);
    }
}

async function injectSingle(signalType) {
    try {
        const res = await fetch("/api/simulate/single", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ signal_type: signalType })
        });
        const data = await res.json();
        if (data.status === "success") {
            await fetchQueue(false);
            selectSample(data.sample.sample_id);
        }
    } catch (err) {
        alert("Failed to inject signal: " + err);
    }
}

async function simulateBatch() {
    try {
        const res = await fetch("/api/simulate/batch", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ count: 4, anomaly_rate: 0.25 })
        });
        const data = await res.json();
        if (data.status === "success") {
            await fetchQueue(!activeSampleId);
        }
    } catch (err) {
        console.error("Batch simulate error:", err);
    }
}

async function clearQueue() {
    stopAudio();
    try {
        await fetch("/api/queue/clear", { method: "POST" });
        await fetchQueue(true);
    } catch (err) {
        console.error("Failed to clear queue:", err);
    }
}

async function markCurrentReviewed() {
    if (!activeSampleId) return;
    try {
        await fetch(`/api/sample/${activeSampleId}/review`, { method: "POST" });
        await fetchQueue(false);
    } catch (err) {
        console.error("Failed to mark reviewed:", err);
    }
}

// ==========================================
// 7. SLIDE 9 BENCHMARK MODAL
// ==========================================

async function openBenchmarkModal() {
    const modal = document.getElementById("benchmark-modal");
    modal.style.display = "flex";
    document.getElementById("benchmark-results-container").innerHTML = `<div style="text-align:center; padding:30px; font-family:var(--font-mono); color:#62788f;">[ EXECUTING EMPIRICAL VALIDATION ACROSS 30 SIGNALS... ]</div>`;

    try {
        const res = await fetch("/api/benchmark?count=30");
        const data = await res.json();
        if (data.status === "success") {
            renderBenchmarkResults(data.benchmark);
        }
    } catch (err) {
        document.getElementById("benchmark-results-container").innerHTML = `<div style="color:#ff2a5f;">Failed to run benchmark: ${err}</div>`;
    }
}

function renderBenchmarkResults(b) {
    const container = document.getElementById("benchmark-results-container");
    container.innerHTML = `
        <div class="hud-stat-grid" style="grid-template-columns: repeat(4, 1fr); margin-bottom: 20px;">
            <div class="hud-tile">
                <div class="hud-tile-label">QUEUE SPEEDUP</div>
                <div class="hud-tile-value" style="color: #00f0ff;">+${b.position_improvement_pct}%</div>
            </div>
            <div class="hud-tile">
                <div class="hud-tile-label">CLASSIFIER ACCURACY</div>
                <div class="hud-tile-value" style="color: #00ff88;">${b.classification_accuracy_pct}%</div>
            </div>
            <div class="hud-tile">
                <div class="hud-tile-label">FALSE-ALARM RATE</div>
                <div class="hud-tile-value" style="color: #ffaa00;">${b.false_alarm_rate_pct}%</div>
            </div>
            <div class="hud-tile">
                <div class="hud-tile-label">DSP+AI LATENCY</div>
                <div class="hud-tile-value" style="color: #fff;">${b.average_latency_ms} ms</div>
            </div>
        </div>

        <div style="background: #080d14; padding: 14px; border-radius: 4px; border: 1px solid var(--border-hud); margin-bottom: 16px;">
            <h4 style="font-family: var(--font-mono); font-size: 12px; color: #fff; margin-bottom: 6px;">EMPIRICAL PROOF (SLIDE 9 VERIFICATION):</h4>
            <p style="font-size: 11px; color: var(--text-muted); line-height: 1.6;">
                In traditional fixed-order sweeps, high-priority threats and anomalies waited until an average position of <strong>#${b.fixed_order_avg_position}</strong>. 
                Under SmartScan AI's adaptive queue, they were promoted to an average position of <strong>#${b.adaptive_avg_position}</strong>, reducing critical review wait times by <strong>${b.position_improvement_pct}%</strong> without sacrificing real-time throughput (${b.average_latency_ms} ms / sample).
            </p>
        </div>

        <table style="width: 100%; font-family: var(--font-mono); font-size: 10px; border-collapse: collapse; text-align: left;">
            <thead>
                <tr style="border-bottom: 1px solid var(--border-hud); color: var(--text-muted);">
                    <th style="padding: 6px;">TARGET ID</th>
                    <th style="padding: 6px;">SIGNAL EMITTER</th>
                    <th style="padding: 6px;">SCORE</th>
                    <th style="padding: 6px;">FIXED POS</th>
                    <th style="padding: 6px;">SMARTSCAN POS</th>
                    <th style="padding: 6px;">PROMOTION</th>
                </tr>
            </thead>
            <tbody>
                ${b.samples_summary.map(s => {
                    const diff = s.fixed_pos - s.adaptive_pos;
                    const changeHtml = diff > 0 
                        ? `<span style="color: #00ff88;">▲ +${diff} RANKS</span>` 
                        : (diff < 0 ? `<span style="color: #ff2a5f;">▼ ${diff}</span>` : `<span style="color: var(--text-muted);">-</span>`);
                    return `
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                            <td style="padding: 6px; color: var(--accent-cyan);">${s.sample_id}</td>
                            <td style="padding: 6px; font-weight: 700;">${s.type}</td>
                            <td style="padding: 6px; color: #fff;">${s.score}</td>
                            <td style="padding: 6px;">#${s.fixed_pos}</td>
                            <td style="padding: 6px; font-weight: 800; color: #00ff88;">#${s.adaptive_pos}</td>
                            <td style="padding: 6px;">${changeHtml}</td>
                        </tr>
                    `;
                }).join("")}
            </tbody>
        </table>
    `;
}

function closeBenchmarkModal() {
    document.getElementById("benchmark-modal").style.display = "none";
}
