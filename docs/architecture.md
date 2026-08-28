# System Architecture — SIH26054

## 1. Overview

This project implements an AI-enabled real-time digital twin system for monitoring the health, predicting faults, and estimating the remaining useful life of aero piston engines used in MALE UAVs.

The overall system follows the flow:

**Engine / Engine Simulation → Sensor Data → Data Processing → Digital Twin → AI/ML Analysis → Backend → Operator Dashboard**

For the initial prototype, real engine hardware is not required. Engine behaviour and sensor values will be generated using a physics-based simulation with controlled fault injection.

---

## 2. High-Level Architecture

```text
┌─────────────────────────────┐
│   Aero Piston Engine Model  │
│   / Engine Simulation       │
└──────────────┬──────────────┘
               │
               │ Simulated Sensor Data
               ▼
┌─────────────────────────────┐
│      Data Acquisition       │
│                             │
│ RPM                         │
│ Temperature                 │
│ Pressure                    │
│ Vibration                   │
│ Fuel Flow                   │
│ Engine Load                 │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│     Data Preprocessing      │
│                             │
│ Validation                  │
│ Filtering                   │
│ Normalization               │
│ Time-Series Processing      │
└──────────────┬──────────────┘
               │
               ├────────────────────┐
               ▼                    ▼
┌──────────────────────┐   ┌──────────────────────┐
│    Digital Twin      │   │      Database        │
│                      │   │                      │
│ Expected Behaviour   │   │ Sensor History       │
│ Current Engine State │   │ Fault History        │
│ Health State         │   │ Health/RUL Records   │
└──────────┬───────────┘   └──────────────────────┘
           │
           │ Expected vs Observed Behaviour
           ▼
┌─────────────────────────────┐
│        AI / ML Layer        │
│                             │
│ Anomaly Detection           │
│ Fault Classification        │
│ Health Assessment           │
│ Degradation Tracking        │
│ RUL Estimation              │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│       Backend / APIs        │
│                             │
│ Data Management             │
│ Model Integration           │
│ Alert Management            │
│ Dashboard API               │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│     Operator Dashboard      │
│                             │
│ Live Sensor Charts          │
│ Engine Health Score         │
│ Fault Alerts                │
│ Fault Probability           │
│ RUL Estimate                │
│ Mission Replay              │
│ Reports                     │
└─────────────────────────────┘
```

---

## 3. Engine Simulation Layer

The simulation layer represents the behaviour of an aero piston engine under different operating conditions.

The engine model will simulate parameters such as:

* Engine RPM
* Cylinder/head temperature
* Oil or engine pressure
* Vibration
* Fuel flow
* Engine load
* Efficiency

Different mission phases can be simulated:

```text
Takeoff → Climb → Cruise → High Load → Descent → Landing
```

Faults can then be deliberately introduced into the simulated engine.

Examples include:

* Abnormal vibration
* Overheating
* Pressure loss
* Fuel-flow abnormalities
* Reduced engine efficiency
* Progressive component degradation

The simulation produces continuous time-series data similar to sensor readings from a real engine.

---

## 4. Data Pipeline

The data pipeline transfers sensor information from the engine simulation to the digital twin and AI systems.

### Pipeline

```text
Raw Sensor Data
       ↓
Data Validation
       ↓
Noise Filtering
       ↓
Normalization
       ↓
Time-Series Processing
       ↓
Digital Twin / ML / Database
```

The pipeline must support continuous sensor updates so that the system behaves as a real-time monitoring platform.

---

## 5. Digital Twin

The digital twin represents the expected state and behaviour of the physical engine.

For every simulation step, the system compares:

```text
Expected Engine Behaviour
            vs
Observed Engine Behaviour
```

Differences between the expected and observed state can indicate abnormal engine behaviour.

The digital twin maintains information such as:

* Current engine state
* Expected engine parameters
* Current health condition
* Operating history
* Degradation state
* Mission/load conditions

---

## 6. AI / ML Layer

The AI/ML layer analyses the time-series engine data.

### Anomaly Detection

Determines whether current engine behaviour differs significantly from normal behaviour.

```text
Normal Data → Normal Operation

Abnormal Data → Anomaly Detected
```

### Fault Classification

Once an anomaly is detected, the model attempts to determine the likely fault responsible for it.

Example:

```text
High Vibration
+
Increasing Temperature
+
Reduced Efficiency
        ↓
Possible Mechanical Fault
```

### Health Assessment

The system produces an engine health indicator or health score based on sensor behaviour and detected degradation.

### Degradation Tracking

Historical engine data is analysed to determine whether engine performance is deteriorating over time.

### Remaining Useful Life Estimation

The model estimates how much operating life may remain before maintenance or component failure becomes likely.

---

## 7. Backend

The backend connects the simulation, digital twin, machine-learning models, database, and frontend.

Responsibilities include:

* Receiving engine telemetry
* Storing sensor data
* Calling ML models
* Maintaining engine health state
* Generating alerts
* Serving data to the frontend
* Managing mission history
* Providing replay data

Example API structure:

```text
/api/telemetry
/api/engine/status
/api/health
/api/anomalies
/api/faults
/api/rul
/api/missions
```

---

## 8. Database

The database stores historical and current system information.

Possible data categories include:

```text
Engine Telemetry
Mission Information
Detected Anomalies
Predicted Faults
Health Scores
RUL Predictions
Fault Injection Events
System Alerts
```

Historical data is particularly important for degradation tracking and mission replay.

---

## 9. Operator Dashboard

The dashboard provides a visual interface for monitoring engine condition.

The dashboard should display:

* Current RPM
* Temperature
* Pressure
* Vibration
* Fuel flow
* Engine load
* Engine health score
* Detected anomalies
* Predicted faults
* Fault severity
* Remaining Useful Life
* Mission phase

Historical graphs should allow the operator to observe how engine behaviour changes over time.

The dashboard should also support mission replay so previous engine behaviour can be analysed.

---

## 10. Example Fault Detection Workflow

An example system event may occur as follows:

```text
Engine operating normally
        ↓
Vibration begins increasing
        ↓
Temperature begins increasing
        ↓
Efficiency decreases
        ↓
Digital Twin detects deviation
        ↓
AI detects anomaly
        ↓
Fault classifier identifies likely fault
        ↓
Engine health score decreases
        ↓
RUL estimate is updated
        ↓
Backend generates warning
        ↓
Dashboard alerts operator
```

---

## 11. Development Workflow

The project will be developed through six connected workflows:

```text
1. Engine Research & Validation
              ↓
2. Physics Simulation & Digital Twin
              ↓
3. AI / ML Predictive Maintenance
              ↓
4. Backend & Data Pipeline
              ↓
5. Dashboard & Visualization
              ↓
6. Integration & Testing
```

These workflows are not fully independent.

Engine research defines realistic behaviour for the simulation.

The simulation generates data required by the ML and backend systems.

The AI/ML models analyse this data and generate predictions.

The backend connects these services and exposes their outputs.

The dashboard visualizes the complete system.

Integration and testing verify that all components operate together correctly.

---

## 12. Repository Mapping

```text
SIH26054/
│
├── docs/
│   ├── project-brief.md
│   └── architecture.md
│
├── simulation/
│   └── Engine physics and fault simulation
│
├── ml/
│   └── Anomaly detection, fault prediction and RUL
│
├── backend/
│   └── APIs, database and service integration
│
├── frontend/
│   └── Dashboard and visualization
│
├── data/
│   └── Generated and processed datasets
│
└── tests/
    └── Component and integration testing
```

---

## 13. Initial MVP Architecture

The first working version will focus on:

1. One representative aero piston engine model
2. Simulated real-time sensor data
3. Multiple engine operating conditions
4. Basic fault injection
5. Digital-twin state comparison
6. Anomaly detection
7. A small number of fault classes
8. Basic degradation and RUL estimation
9. Backend integration
10. Real-time dashboard visualization

The MVP will prioritize a complete working system rather than attempting highly detailed CFD, full physical-engine integration, every possible engine fault, or unnecessarily complex deep-learning models.
