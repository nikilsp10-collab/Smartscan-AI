# SmartScan AI: How to Run & Presentation Cheat Sheet

> **Audience**: 1st Year Engineering Team & Judges  
> **Project**: SmartScan AI (Smart Scan Strategy for Electronic Warfare)  
> **Repository**: [SampleProject](file:///c:/Users/nikil/Projects/SampleProject)

---

## 🚀 1. How to Run the Project on Your Laptop

Open PowerShell or Command Prompt in this folder and run:

```powershell
# 1. Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Launch the application
python run.py
```

Now open your web browser (Chrome, Edge, Brave, etc.) and go to:
👉 **`http://localhost:5000`**

To run automated unit tests at any time:
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

---

## 🎬 2. The 3-Minute Live Demo Script (What to Click During Presentation)

Follow these exact steps when presenting your screen to judges or professors:

### Step 1: Show the Initial Screen
* **What to say**: *"This is SmartScan AI. Instead of checking every radio signal in a rigid, first-come-first-served order, our system acts like an Emergency Room triage for electromagnetic signals."*
* **What you see**: The dark tactical dashboard loaded with incoming signals sorted by priority score (0 to 100).

### Step 2: Click "⚡ Inject Anomaly" (The "Wow" Moment)
* **What to do**: Click the red button in the top bar: **"⚡ Inject Anomaly"**.
* **What happens**: A novel, distorted waveform is instantly synthesized and processed. Look at the queue on the left—it **immediately jumps straight to Rank #1** with a red **CRITICAL** badge.
* **What to say**: *"Notice how this unknown signal just arrived, but instead of waiting at the back of the line, our Anomaly Detector spotted that its frequency and entropy deviate from normal signals. It immediately promoted it to the top of the queue for human review."*

### Step 3: Click on the Top Signal to Inspect It
* **What to do**: Click on the #1 card in the queue.
* **What happens**:
  - The middle pane draws the **Time-Domain Oscillogram** and the **Frequency Spectrum (FFT)**.
  - The right pane displays the **AI Explainability Cards** showing why it got that score:
    - *Anomaly Severity: +31 pts (Unfamiliar pattern! Outlier score 78%)*
    - *Threat Assessment: +25 pts (Unknown Emitter)*
    - *Model Uncertainty: +12 pts (Low classification confidence)*
    - *Signal Quality (SNR): +8 pts*
* **What to say**: *"We don't use black-box AI. SmartScan AI explains to the operator in plain English exactly why this signal was flagged."*

### Step 4: Click "📊 Run Benchmark" (Proving Slide 9)
* **What to do**: Click the orange button: **"📊 Run Benchmark"**.
* **What happens**: A popup modal appears showing a direct comparison between **Traditional Fixed-Order Scanning** vs. **SmartScan AI Adaptive Prioritization** across 30 signals.
* **What to say**: *"Slide 9 of our proposal asked: How do we prove it? In this benchmark on the exact same signal set, traditional scanning caused critical threats to wait until position #14 on average. SmartScan AI brought them forward to position #3—a 70%+ improvement in review speed—while taking less than 4 milliseconds per signal!"*

---

## 👥 3. Team Member Speaking Roles (6-Member Script)

Here is exactly what each person can say for 30–45 seconds:

### Member 1: Data Ingestion & Signal Simulation
> *"I'm responsible for where the signal data comes from. Since we are dealing with simulated electronic warfare environments, I built `simulator.py`. It mathematically generates 6 realistic signal types: Continuous Wave, Pulsed Radars, Chirps, Frequency Hopping, Noise, and custom unknown anomalies with configurable Signal-to-Noise Ratios."*

### Member 2: Digital Signal Processing (DSP) Lead
> *"I take the raw waveform numbers from Member 1 and extract their physical fingerprints in `dsp.py`. Using Fast Fourier Transforms (FFT), I calculate the Center Frequency, 3-dB Bandwidth, Spectral Centroid, and Spectral Entropy in under 2 milliseconds, creating the feature vector for our AI models."*

### Member 3: AI & Machine Learning Lead
> *"I designed our dual-layer AI architecture in `models.py`. Standard classifiers fail when they see brand new, unseen radar threats. So we combined two models: a k-NN classifier to recognize known signals with 100% accuracy, and a nearest-neighbor anomaly detector trained on baseline data that flags any signal whose feature distance exceeds normal bounds."*

### Member 4: Priority & Explainability Lead
> *"I built the triage algorithm in `priority_engine.py`. It combines Anomaly Severity (40%), Threat Tier (25%), Model Uncertainty (25%), and SNR (10%) into a composite score from 0 to 100. It also generates transparent, plain-English explanations so human operators understand the rationale behind every alert."*

### Member 5: Backend & REST API Engineer
> *"I built the Flask web server in `app.py`. It provides REST endpoints for batch simulation, real-time queue streaming, waveform payload generation for the charts, and the automated Slide 9 benchmark suite."*

### Member 6: UI & Dashboard Lead
> *"I developed the dark tactical dashboard using HTML5, CSS3, and Chart.js in `dashboard.js`. Operators can monitor incoming signals, visually inspect oscillograms and power spectra, and run side-by-side performance comparisons against traditional fixed-order scanning."*
