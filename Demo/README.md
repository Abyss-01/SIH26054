# AERIS · UAV engine telemetry demo

An interactive Rotax 915 iS engine monitoring prototype for **SIH26054**. Explore a seven-stage mission, inject faults, compare sensor traces with a nominal reference, and export a telemetry review. All mission data is generated locally; the core demo works without an API key.

## Run locally

Use **Python 3.10+**. From the repository root:

```bash
cd Demo
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL printed by Streamlit, normally `http://localhost:8501`. Run from `Demo/` so Streamlit loads `.streamlit/config.toml` and the matching dark theme. Streamlit 1.63 or later is required; the demo uses timed fragments and the current widget sizing API.

## A quick presentation

1. The console opens at cruise with **Guided flight tour**, demonstrating fuel pressure instability. Compare the solid sensor traces with the dotted nominal reference.
2. Select **Nominal operation** to see the same stage without an injected fault. Then try **Oil pressure loss** or **Cylinder 2 EGT imbalance**.
3. Return to **Guided flight tour** and press **Play mission**. Progress advances 5 km every two seconds. Pause, scrub the distance slider, or use **Previous / Next** to inspect a stage. Playback stops at 300 km; playing again restarts at zero.
4. Open **Anomaly Analysis** to see individual flagged samples, the first departure, and the most affected sensor. **Table Summary** lists current values, ranges, and excursions for every channel, with a summary CSV download. Enable **Show table summary** in the sidebar to also display this table beneath the telemetry charts.
5. In **AI Diagnostics**, select **Generate telemetry review**. This pauses playback and creates a local evidence summary, with optional Gemini interpretation when configured. Download the review as Markdown, or use **Export CSV** and **Snapshot JSON** beneath the tabs.

**New snapshot** changes the random seed and pauses playback. Ordinary reruns preserve the same data. **Reset demo** restores the initial mission, scenario, noise, and seed. Scenario and noise changes pause playback; mission settings survive a visit to AI configuration.

### Guided tour

| Stage | Mission distance | Injected pattern |
| --- | --- | --- |
| Warm-up | 0–20 km | Nominal |
| Take-off | >20–50 km | Nominal |
| Climb | >50–110 km | Cooling degradation |
| Cruise | >110–180 km | Fuel pressure instability |
| Loiter | >180–240 km | Elevated vibration |
| Descent | >240–280 km | Boost pressure loss |
| Landing | >280–300 km | Oil pressure loss |

All seven faults, including temperature sensor drift and cylinder 2 imbalance, are selectable manually at any flight stage.

## What the analysis means

Each snapshot contains **30 samples at 1 Hz**. The generator uses stage-specific targets and a local NumPy random generator. The observed and nominal windows share the same noise, making the effect of an injection easy to compare. Faults begin at `t = 8 s` and develop through the window. Replay changes the selected mission position; these are separate illustrative windows, not a continuous flight recording.

For each sensor, the score is its absolute departure from the stage target divided by its demo tolerance. The largest sensor score becomes that sample's anomaly score; samples above **1×** are flagged. The status is normal with no flags, warning with flags, or critical when flags exist and the 95th-percentile score reaches **3×**. The displayed demo health score is:

```text
clip(100 − 12 × max(p95_score − 0.5, 0) − 35 × flagged_fraction, 0, 100)
```

The plots, per-sample flags, and table use the same stage reference bands. EGT spread is calculated from the simultaneous maximum minus minimum across all four cylinders. A noisy nominal window can also produce flags.

This is a **synthetic demonstrator**, with illustrative reference bands and heuristic scores. It does not implement a trained ML model, validated aircraft physics, OEM compliance checks, remaining useful life prediction, or a live aircraft connection. The 1 Hz vibration index illustrates changes in magnitude, not high-frequency vibration dynamics. Diagnostic reports describe observed patterns and hypotheses, without presenting invented manual citations or component diagnoses.

## Optional Gemini interpretation

Install the optional integration into the same environment:

```bash
python -m pip install -r requirements-ai.txt
```

In **AI configuration**, enter a Gemini key and select **Save key**. **Test connection** makes an explicit test request. You can also initialize the key with the `GEMINI_API_KEY` environment variable before launching the app.

A generated Gemini review sends the scenario, stage, demo score, and aggregate synthetic sensor statistics to Google using the **Model** selected in AI configuration. The default is [`gemini-3.8-flash`](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash); set `GEMINI_MODEL` before launch to override that initial value. Missing SDKs, missing keys, failed requests, and empty responses fall back to the local report. Where supported by the SDK, requests use a 15-second timeout. A configured key is distinguished from a successfully tested connection.

If a model returns **HTTP 404**, click **Load available models**, choose a text model returned for your saved key, then click **Use selected model** and **Test connection**. Discovery calls Google's models API only when clicked; listing a model does not verify generation access or available quota. Connection tests and AI diagnostics always use the same selected model. Changing it invalidates earlier connection results and diagnostic reports.

Failed connection tests and reviews show a credential-free error category, HTTP code when available, and a suggested next step. For example, HTTP 429 reports a quota or rate limit and HTTP 403 reports denied access. Provider exception payloads and request URLs are never displayed. See [Google's troubleshooting guide](https://ai.google.dev/gemini-api/docs/troubleshooting) for account-side checks.

Keys remain in Streamlit session memory and can be removed with **Clear key**. Reports persist across reruns, are tied to the displayed data and API configuration, and become unavailable when those inputs change. No report is regenerated automatically.

## Project layout

```text
Demo/
├── app.py                      # Navigation, sidebar controls, session state
├── .streamlit/config.toml       # Theme and usage-statistics setting
├── config/
│   ├── engine_specs.py         # Synthetic stage targets and reference bands
│   └── scenarios.py            # Shared scenarios and guided-tour routing
├── telemetry/generator.py      # Reproducible samples and measured scoring
├── components/
│   ├── flight_path.py          # Mission profile and playback controls
│   ├── metrics.py              # Snapshot status cards
│   ├── charts.py               # Telemetry and nominal comparison plots
│   └── statistics_table.py     # Per-sensor excursion counts and statistics
├── clustering/visualizer.py    # Rule-based score and residual visualization
├── ai_engine/copilot.py        # Evidence reports and optional Gemini client
├── views/                      # Mission console and AI configuration
├── styles/theme.py             # Responsive console styling
├── tests/                      # Unit and Streamlit interaction regressions
├── requirements.txt            # Core offline demo dependencies
└── requirements-ai.txt         # Optional Gemini dependencies
```

`rotax_915is_anomalies.txt` is retained as the original scenario brainstorming document; the running demo uses the shared Python configuration.

## Verification

From the repository root, after installing the core dependencies:

```bash
python -m unittest discover -s Demo/tests -v
```

The suite covers reproducibility, stage boundaries, fault injection, measured scoring, reference excursions, chart rendering, mission controls, navigation, report persistence, and simulated provider failures. Tests make no live Gemini requests. From inside `Demo/`, use `python -m unittest discover -s tests -v`.
