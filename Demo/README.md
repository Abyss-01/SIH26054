# 🛸 Rotax 915 iS UAV Digital Twin Platform (SIH26054)

> **SIH 2026 Problem Statement SIH26054** — MALE UAV Piston Engine Health Telemetry, Physics Digital Twin, Unsupervised Anomaly Detection & Autonomous AI Diagnostic Engine.

---

## 📂 Project Architecture & Directory Structure

The codebase is organized into a modular, clean multi-file architecture to ensure maintainability, clear separation of concerns, and clean testing.

```text
SIH/
├── app.py                      # Application Entry Point & Router
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git tracking exclusion rules (hidden file)
├── README.md                   # Complete system documentation
│
├── config/                     # Engine Configuration & Operational Limits
│   ├── __init__.py
│   └── engine_specs.py        # Rotax 915 iS envelope limits & specs constants
│
├── styles/                     # Dark Aerospace UI Theme
│   ├── __init__.py
│   └── theme.py               # Custom Grafana/Palantir CSS style injector
│
├── telemetry/                  # Physics Telemetry Data Generator
│   ├── __init__.py
│   └── generator.py           # 7-Stage Flight Profile & Anomaly data engine
│
├── clustering/                 # Unsupervised ML Anomaly Detection
│   ├── __init__.py
│   └── visualizer.py          # 160-point baseline model & 2D scatter plots
│
├── ai_engine/                  # Autonomous AI Diagnostic Copilot
│   ├── __init__.py
│   └── copilot.py             # Google Gemini 2.5 Flash SDK wrapper & fallback rules
│
├── components/                 # Reusable Streamlit UI Components
│   ├── __init__.py
│   ├── flight_path.py         # 7-Stage MALE UAV Flight Profile graphic
│   ├── metrics.py             # Top 4 Health & Status metric cards
│   ├── charts.py              # 4 Real-time Plotly telemetry line charts
│   └── statistics_table.py    # Sensor compliance summary table
│
└── views/                      # Application Page Views
    ├── __init__.py
    ├── dashboard.py           # Main Digital Twin Telemetry Dashboard
    └── settings.py            # API Settings & Key Configuration View
```

---

## 🔍 Module Breakdown: What Each Part Does

### 1. `app.py` (Main Router)
- **Role**: Entry point for Streamlit execution.
- **Functionality**:
  - Initializes session state variables (`active_page`, `gemini_api_key`).
  - Calls `apply_custom_theme()` to render the aerospace dark theme.
  - Controls top header toolbar and sidebar view switching between **Dashboard** and **API Settings**.

### 2. `config/engine_specs.py`
- **Role**: Centralized constants definition.
- **Functionality**: Defines Rotax 915 iS operational limits for Engine Speed (1,800–5,800 RPM), EGT (750–950°C), CHT (100–120°C), MAP (30–45 inHg), Fuel Rail Pressure (2.9–3.2 bar), Oil Pressure (2.0–5.0 bar), and Vibration (1.5–2.5 G).

### 3. `styles/theme.py`
- **Role**: Custom CSS stylesheet.
- **Functionality**: Hides default Streamlit menus, footers, and toolbar toggles; applies dark slate aerospace styling with custom status badges (`.status-normal`, `.status-warning`, `.status-critical`) and metric containers.

### 4. `telemetry/generator.py`
- **Role**: Physics-based mathematical data simulator (NumPy / Pandas).
- **Functionality**:
  - Simulates 30 seconds of 1 Hz time-series data matching the **7 MALE UAV Flight Profile Stages**:
    1. Warm-Up (ground idle)
    2. Take-Off (104 kW POWER mode)
    3. Climb
    4. Cruise (99 kW ECO mode)
    5. Loiter / Endurance (racetrack loop)
    6. Descent / Return
    7. Landing / Cooldown
  - Injects candidate Rotax 915 iS fault profiles from `rotax_915is_anomalies.txt`:
    1. Fuel Rail Pressure Instability
    2. Cooling Degradation / Thermal Overheating
    3. Coolant Sensor Drift / False-Low Plausibility Anomaly
    4. Gearbox High-Frequency Vibration
    5. Cylinder 2 EGT Combustion Imbalance
    6. Lubrication Oil Pressure Loss
    7. Turbocharger Boost Air-Path Collapse

### 5. `clustering/visualizer.py`
- **Role**: Unsupervised ML Anomaly Classifier.
- **Functionality**: Generates a 160-sample reference cluster baseline for nominal operations (`Cluster 0`) and renders 2D scatter plots comparing live engine telemetry against normal boundaries.

### 6. `ai_engine/copilot.py`
- **Role**: Autonomous AI Diagnostic Reasoning Engine.
- **Functionality**: Connects to `google-genai` SDK (`gemini-2.5-flash`) to generate engineering fault analysis, citing Rotax 915 iS Manual sections (73-00-00, 75-00-00, 79-00-00, 72-00-00, 78-00-00). Includes high-fidelity offline fallback rules when unconfigured.

### 7. `components/` & `views/`
- **`components/flight_path.py`**: Interactive altitude corridor graphic with active UAV tracking marker.
- **`components/metrics.py`**: Metric cards for Health Index (%), RUL (Hours), Status, and ML Cluster State.
- **`components/charts.py`**: Plotly line charts for EGT, MAP & RPM, CHT & Fuel Pressure, Oil Pressure & Vibration.
- **`views/settings.py`**: API Key entry field with connection test functionality.

---

## 👁️ Why is `.gitignore` Hidden by Default?

In Linux/Unix operating systems and IDE file explorers (like VS Code), **any file starting with a dot `.` is classified as a hidden configuration file** (a "dotfile").

- **To view hidden files in Linux File Manager (Nautilus)**: Press `Ctrl + H`.
- **To view hidden files in VS Code / Cursor**:
  1. Open VS Code Settings (`Ctrl + ,`).
  2. Search for `Files: Exclude`.
  3. Ensure `**/.git` or hidden files are toggled visible in your File Explorer panel.

---

## 🚀 Running the Project

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run application
streamlit run app.py
```
