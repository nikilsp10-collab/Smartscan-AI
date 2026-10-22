/**
 * SmartScan AI - Operator Dashboard JavaScript
 * Author: SmartScan AI Team (Member 6: UI & Dashboard Lead)
 * 
 * Handles real-time queue polling, Chart.js waveform & spectrum rendering,
 * explainability updates, and benchmark comparison modals.
 */

let waveformChart = null;
let spectrumChart = null;
let activeSampleId = null;

// Initialize when page loads
document.addEventListener("DOMContentLoaded", () => {
    initCharts();
    fetchQueue(true);

    // Event Listeners for action buttons
    document.getElementById("btn-inject-anomaly").addEventListener("click", () => injectSingle("ANOMALY_UNKNOWN"));
    document.getElementById("btn-inject-radar").addEventListener("click", () => injectSingle("PULSED_RADAR"));
    document.getElementById("btn-inject-chirp").addEventListener("click", () => injectSingle("CHIRP_LFM"));
    document.getElementById("btn-simulate-batch").addEventListener("click", simulateBatch);
    document.getElementById("btn-clear-queue").addEventListener("click", clearQueue);
    document.getElementById("btn-run-benchmark").addEventListener("click", openBenchmarkModal);
    document.getElementById("btn-mark-reviewed").addEventListener("click", markCurrentReviewed);
    document.getElementById("btn-close-modal").addEventListener("click", closeBenchmarkModal);
});

// --- Chart Initialization ---

function initCharts() {
    const commonChartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 350 },
        scales: {
            x: {
                grid: { color: "rgba(255, 255, 255, 0.05)" },
                ticks: { color: "#8b949e", font: { size: 10 } }
            },
            y: {
                grid: { color: "rgba(255, 255, 255, 0.05)" },
                ticks: { color: "#8b949e", font: { size: 10 } }
            }
        },
        plugins: {
            legend: { display: false }
        }
    };

    // 1. Time-Domain Waveform Chart
    const ctxWave = document.getElementById("waveformCanvas").getContext("2d");
    waveformChart = new Chart(ctxWave, {
        type: "line",
        data: {
            labels: [],
            datasets: [{
                label: "Voltage / Amplitude",
                data: [],
                borderColor: "#00e5ff",
                borderWidth: 1.5,
                pointRadius: 0,
                tension: 0.1
            }]
        },
        options: {
            ...commonChartOptions,
            scales: {
                ...commonChartOptions.scales,
                x: {
                    ...commonChartOptions.scales.x,
                    title: { display: true, text: "Time (µs)", color: "#8b949e", font: { size: 10 } }
                },
                y: {
                    ...commonChartOptions.scales.y,
                    title: { display: true, text: "Amplitude", color: "#8b949e", font: { size: 10 } }
                }
            }
        }
    });

    // 2. Frequency-Domain FFT Spectrum Chart
    const ctxSpec = document.getElementById("spectrumCanvas").getContext("2d");
    spectrumChart = new Chart(ctxSpec, {
        type: "line",
        data: {
            labels: [],
            datasets: [{
                label: "Power (dB)",
                data: [],
                borderColor: "#388bfd",
                backgroundColor: "rgba(56, 139, 253, 0.15)",
                fill: true,
                borderWidth: 1.5,
                pointRadius: 0,
                tension: 0.1
            }]
        },
        options: {
            ...commonChartOptions,
            scales: {
                ...commonChartOptions.scales,
                x: {
                    ...commonChartOptions.scales.x,
                    title: { display: true, text: "Frequency (MHz)", color: "#8b949e", font: { size: 10 } }
                },
                y: {
                    ...commonChartOptions.scales.y,
                    title: { display: true, text: "Power (dB)", color: "#8b949e", font: { size: 10 } }
                }
            }
        }
    });
}

// --- Queue Fetching & Rendering ---

async function fetchQueue(selectFirst = false) {
    try {
        const response = await fetch("/api/queue");
        const data = await response.json();
        if (data.status === "success") {
            renderQueue(data.queue, selectFirst);
        }
    } catch (err) {
        console.error("Failed to fetch queue:", err);
    }
}

function renderQueue(items, selectFirst) {
    const queueList = document.getElementById("queue-list");
    document.getElementById("queue-count").textContent = `${items.length} Signals`;
    queueList.innerHTML = "";

    if (items.length === 0) {
        queueList.innerHTML = `<div style="text-align: center; color: #8b949e; padding: 30px;">Queue Empty. Click 'Simulate Batch' to ingest signals.</div>`;
        return;
    }

    items.forEach((item, index) => {
        const card = document.createElement("div");
        card.className = `queue-card ${item.sample_id === activeSampleId ? "active" : ""} ${item.reviewed ? "reviewed" : ""}`;
        card.dataset.id = item.sample_id;

        const badgeClass = `badge-${item.priority_level.toLowerCase()}`;
        
        card.innerHTML = `
            <div class="queue-card-top">
                <span class="queue-rank">#${index + 1} [Arr #${item.original_arrival_order}]</span>
                <span class="badge ${badgeClass}">${item.priority_level}</span>
            </div>
            <div class="queue-card-title">${item.predicted_type}</div>
            <div class="queue-card-meta">
                <span>Score: <strong class="score-display">${item.priority_score}</strong></span>
                <span>Anom: ${(item.anomaly_score * 100).toFixed(0)}%</span>
            </div>
        `;

        card.addEventListener("click", () => selectSample(item.sample_id));
        queueList.appendChild(card);
    });

    if (selectFirst && items.length > 0) {
        selectSample(items[0].sample_id);
    } else if (activeSampleId) {
        // Highlight active if still in list
        const activeCard = queueList.querySelector(`[data-id="${activeSampleId}"]`);
        if (activeCard) activeCard.classList.add("active");
    }
}

// --- Select Sample & Update Inspector ---

async function selectSample(sampleId) {
    activeSampleId = sampleId;

    // Update active highlight in queue UI
    document.querySelectorAll(".queue-card").forEach(c => c.classList.remove("active"));
    const selectedCard = document.querySelector(`.queue-card[data-id="${sampleId}"]`);
    if (selectedCard) selectedCard.classList.add("active");

    try {
        const res = await fetch(`/api/sample/${sampleId}`);
        const result = await res.json();
        if (result.status === "success") {
            updateDashboardWithSample(result.data);
        }
    } catch (err) {
        console.error("Error loading sample details:", err);
    }
}

function updateDashboardWithSample(sampleData) {
    const feat = sampleData.features;
    const pred = sampleData.prediction;
    const prio = sampleData.prioritization;

    // 1. Update Diagnostics Pane
    document.getElementById("diag-sample-id").textContent = sampleData.sample_id;
    document.getElementById("diag-pred-type").textContent = prio.predicted_type;
    document.getElementById("diag-prio-score").textContent = prio.priority_score;
    document.getElementById("diag-anomaly-score").textContent = `${(pred.anomaly_score * 100).toFixed(1)}%`;
    document.getElementById("diag-confidence").textContent = `${(pred.confidence * 100).toFixed(1)}%`;
    document.getElementById("diag-center-freq").textContent = `${feat.center_frequency_mhz} MHz`;
    document.getElementById("diag-bandwidth").textContent = `${feat.bandwidth_3db_mhz} MHz`;
    document.getElementById("diag-snr").textContent = `${feat.estimated_snr_db} dB`;
    document.getElementById("diag-entropy").textContent = feat.spectral_entropy;

    // 2. Update Explainability List
    const explainList = document.getElementById("explain-list");
    explainList.innerHTML = "";
    prio.explanations.forEach(e => {
        const el = document.createElement("div");
        el.className = "explain-card";
        el.innerHTML = `
            <div class="explain-header">
                <span>${e.factor}</span>
                <span class="explain-points">${e.points}</span>
            </div>
            <div class="explain-desc">${e.description}</div>
        `;
        explainList.appendChild(el);
    });

    // 3. Update Waveform Chart
    // Convert time array from seconds to microseconds
    const timeLabels = sampleData.time_preview.map(t => (t * 1e6).toFixed(1));
    waveformChart.data.labels = timeLabels;
    waveformChart.data.datasets[0].data = sampleData.waveform_preview;
    // Color wave red if anomaly, cyan if normal
    waveformChart.data.datasets[0].borderColor = pred.is_anomaly ? "#ff3b30" : "#00e5ff";
    waveformChart.update();

    // 4. Update Spectrum Chart
    spectrumChart.data.labels = sampleData.frequencies_mhz.map(f => f.toFixed(2));
    spectrumChart.data.datasets[0].data = sampleData.power_db;
    spectrumChart.update();
}

// --- Action Handlers ---

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
            body: JSON.stringify({ count: 6, anomaly_rate: 0.3 })
        });
        const data = await res.json();
        if (data.status === "success") {
            await fetchQueue(true);
        }
    } catch (err) {
        alert("Failed to simulate batch: " + err);
    }
}

async function clearQueue() {
    if (!confirm("Are you sure you want to clear the queue?")) return;
    try {
        await fetch("/api/queue/clear", { method: "POST" });
        await fetchQueue(true);
    } catch (err) {
        alert("Failed to clear queue: " + err);
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

// --- Benchmark Modal ---

async function openBenchmarkModal() {
    const modal = document.getElementById("benchmark-modal");
    modal.style.display = "flex";
    document.getElementById("benchmark-results-container").innerHTML = `<div style="text-align:center; padding:20px; color:#8b949e;">Running empirical comparison across 30 simulated signals...</div>`;

    try {
        const res = await fetch("/api/benchmark?count=30");
        const data = await res.json();
        if (data.status === "success") {
            renderBenchmarkResults(data.benchmark);
        }
    } catch (err) {
        document.getElementById("benchmark-results-container").innerHTML = `<div style="color:#ff3b30;">Failed to run benchmark: ${err}</div>`;
    }
}

function renderBenchmarkResults(b) {
    const container = document.getElementById("benchmark-results-container");
    container.innerHTML = `
        <div class="stat-grid" style="grid-template-columns: repeat(4, 1fr); margin-bottom: 20px;">
            <div class="stat-tile">
                <div class="stat-label">Position Improvement</div>
                <div class="stat-value" style="color: #00e5ff;">+${b.position_improvement_pct}%</div>
            </div>
            <div class="stat-tile">
                <div class="stat-label">Classification Accuracy</div>
                <div class="stat-value" style="color: #34c759;">${b.classification_accuracy_pct}%</div>
            </div>
            <div class="stat-tile">
                <div class="stat-label">False-Alarm Rate</div>
                <div class="stat-value" style="color: #ff9500;">${b.false_alarm_rate_pct}%</div>
            </div>
            <div class="stat-tile">
                <div class="stat-label">Processing Latency</div>
                <div class="stat-value" style="color: #fff;">${b.average_latency_ms} ms</div>
            </div>
        </div>

        <div style="background-color: var(--bg-card); padding: 14px; border-radius: 6px; border: 1px solid var(--border-color); margin-bottom: 16px;">
            <h4 style="font-size: 13px; color: #fff; margin-bottom: 8px;">Key Finding (Slide 9 Verification):</h4>
            <p style="font-size: 12px; color: #8b949e; line-height: 1.6;">
                In traditional fixed-order sweeps, high-priority threats and anomalies waited until an average position of <strong>#${b.fixed_order_avg_position}</strong>. 
                Under SmartScan AI's adaptive queue, they were promoted to an average position of <strong>#${b.adaptive_avg_position}</strong>, reducing critical review wait times by <strong>${b.position_improvement_pct}%</strong> without sacrificing real-time throughput (${b.average_latency_ms} ms / sample).
            </p>
        </div>

        <table style="width: 100%; font-size: 11px; border-collapse: collapse; text-align: left;">
            <thead>
                <tr style="border-bottom: 1px solid var(--border-color); color: var(--text-muted);">
                    <th style="padding: 6px;">ID</th>
                    <th style="padding: 6px;">Signal Type</th>
                    <th style="padding: 6px;">Priority Score</th>
                    <th style="padding: 6px;">Fixed Scan Pos</th>
                    <th style="padding: 6px;">SmartScan Pos</th>
                    <th style="padding: 6px;">Change</th>
                </tr>
            </thead>
            <tbody>
                ${b.samples_summary.map(s => {
                    const diff = s.fixed_pos - s.adaptive_pos;
                    const changeHtml = diff > 0 
                        ? `<span style="color: #34c759;">▲ +${diff}</span>` 
                        : (diff < 0 ? `<span style="color: #ff3b30;">▼ ${diff}</span>` : `<span style="color: #8b949e;">-</span>`);
                    return `
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                            <td style="padding: 6px; font-family: var(--font-mono);">${s.sample_id}</td>
                            <td style="padding: 6px; font-weight: 600;">${s.type}</td>
                            <td style="padding: 6px; font-family: var(--font-mono); color: #00e5ff;">${s.score}</td>
                            <td style="padding: 6px;">#${s.fixed_pos}</td>
                            <td style="padding: 6px; font-weight: 700;">#${s.adaptive_pos}</td>
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
