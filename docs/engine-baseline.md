# Engine Baseline — ROTAX 915 i A / C24 Reference Model

> **Project:** SIH26054 — AI-Enabled Real-Time Digital Twin System for Health Monitoring, Fault Prediction and Mission Reliability Enhancement of Aero Piston Engines used in MALE UAVs  
> **Purpose:** define the healthy-engine reference model, operating limits, telemetry variables, source-backed subsystem relationships, and the initial fault-to-sensor map used by the simulator and digital twin.
>
> **Important:** this is a modelling baseline, not an aircraft operating manual. The official BRP-Rotax manuals remain authoritative for the ROTAX 915 i A / C24.

---

## 0. Evidence labels

Every numerical value or engineering relationship in this project should carry one of these labels:

- **SOURCE** — directly stated by BRP-Rotax documentation.
- **DERIVED** — calculated or transformed from source-backed values/relationships.
- **ASSUMPTION** — introduced for the simulator because the public Rotax documents do not provide the required value or map.
- **TBD** — not yet defined; do not silently replace with a guessed value.

The simulator must not present an **ASSUMPTION** as a manufacturer specification.

---

## 1. Reference engine

### 1.1 Primary reference

**ROTAX 915 i A / C24 series**

The ROTAX 915 is a **4-cylinder, horizontally opposed, turbocharged** aircraft engine.

The official Installation Manual additionally describes the basic engine as:

- 4-stroke
- 4-cylinder horizontally opposed
- spark ignition
- single central camshaft with pushrods / OHV
- liquid-cooled cylinder heads
- ram-air-cooled cylinders
- dry-sump forced lubrication
- fully redundant electronic Engine Management System (EMS)
- electronic fuel injection
- electronic ignition
- turbocharger
- electronic/pneumatic boost-pressure control
- propeller gearbox with torsional vibration absorber and overload clutch

**Classification:** SOURCE  
**Reference:** IM, Chapter 00-00-00, pp. 3-4.

### 1.2 Electrical variants

- **Type A:** 12 V airframe bus version
- **Type C24:** 24 V airframe bus version

**Classification:** SOURCE  
**Reference:** OM, Chapter 1.6, p. 1-15; IM, Chapter 00-00-00, p. 3.

### 1.3 Scope of this project model

The simulator is **not** intended to reproduce every proprietary ECU map or every mechanical detail of the 915 i.

The initial digital twin will model the engine at the level required for:

1. healthy operating-state estimation,
2. telemetry generation/replay,
3. actual-vs-expected residual calculation,
4. anomaly detection,
5. fault classification/prognostics,
6. mission-reliability inputs.

Where the official manuals do not publish a detailed numerical map, that gap is kept explicit as **ASSUMPTION** or **TBD**.

---

## 2. Official source set

This baseline uses only the following BRP-Rotax documents:

1. **Operators Manual — ROTAX 915 i A / C24 Series**  
   Ref. OM-915 i A / C24, Ed. 0 / Rev. 4, Sept. 01 2022.

2. **Installation Manual — ROTAX 915 i A / C24 Series**  
   Ref. IM-915 i A / C24, Ed. 0 / Rev. 5, Feb. 01 2024.

3. **Maintenance Manual Heavy — ROTAX 915 i A / C24 Series**  
   Ed. 1 / Rev. 0, Nov. 01 2025.

For operating limits, the **Operators Manual** is the primary authority.  
For installation interfaces and CAN/electrical/fuel/cooling interfaces, the **Installation Manual** is preferred.  
For detailed sensor/ECU/component and maintenance relationships, the **Maintenance Manual Heavy** is preferred.

---

## 3. Core operating limits

| Parameter | Rotax value | Classification | Reference |
|---|---:|---|---|
| Idle engine speed | **1800 rpm minimum** | SOURCE | OM 2.1, p. 2-2 |
| Maximum engine speed | **5800 rpm, max. 5 min** | SOURCE | OM 2.1, p. 2-2 |
| Take-off performance | **104 kW @ 5800 rpm** | SOURCE | OM 2.1, p. 2-2 |
| Continuous performance | **99 kW @ 5500 rpm** (without governor) | SOURCE | OM 2.1, p. 2-2 |
| Critical altitude | **15,000 ft** at MAT ≤ 50 °C | SOURCE | OM 2.1, p. 2-2 |
| Maximum operating altitude | **23,000 ft** | SOURCE | OM 2.1, p. 2-3 |
| Static roll angle | **40° max** | SOURCE | OM 2.1, p. 2-3 |
| Negative-g operation | **-0.5 g, max. 5 s** | SOURCE | OM 2.1, p. 2-3 |
| Normal manifold temperature max. | **50 °C** | SOURCE | OM 2.1, p. 2-3 |
| Extended manifold temperature | **>50 to 80 °C**, reduced power | SOURCE | OM 2.1, pp. 2-3 to 2-4 |
| Manifold pressure range | **60–1730 hPa** | SOURCE | OM 2.1, p. 2-4 |
| Target manifold pressure @ 5800 rpm, 25–35 °C | **1520 mbar** | SOURCE | OM 2.1, p. 2-4 |
| Target manifold pressure @ 5500 rpm, 25–35 °C | **1450 mbar** | SOURCE | OM 2.1, p. 2-4 |
| Oil pressure, normal >3500 rpm | **2.0–5.0 bar** | SOURCE | OM 2.1, p. 2-4 |
| Oil pressure minimum <3500 rpm | **0.8 bar** | SOURCE | OM 2.1, p. 2-4 |
| Oil pressure max. at cold start / warm-up | **7.0 bar** | SOURCE | OM 2.1, p. 2-4 |
| Oil temperature at engine start | **≥ -20 °C** | SOURCE | OM 2.1, p. 2-5 |
| Oil temperature before take-off | **≥ 50 °C** | SOURCE | OM 2.1, p. 2-5 |
| Oil temperature normal operation | **50–130 °C** | SOURCE | OM 2.1, p. 2-5 |
| Coolant temperature at start/warm-up | **≥ -20 °C** | SOURCE | OM 2.1, p. 2-5 |
| Coolant temperature normal-operation max. | **120 °C** | SOURCE | OM 2.1, p. 2-5 |
| Exhaust gas temperature max. | **950 °C** | SOURCE | OM 2.1, p. 2-5 |
| EGT split at fuel consumption >3 L/h | **≤ 200 °C** | SOURCE | OM 2.1, p. 2-6 |
| EGT split at fuel consumption <3 L/h | **≤ 500 °C** | SOURCE | OM 2.1, p. 2-6 |
| Ambient temperature, normal operation | **-40 to 50 °C** | SOURCE | OM 2.1, p. 2-6 |
| Fuel pressure at fuel rail | **2.9–3.2 bar** | SOURCE | OM 2.1, p. 2-6 |
| Temporary fuel-pressure excursion | **2.5–3.5 bar, max. 3 s after power-setting change** | SOURCE | OM 2.1, p. 2-6 |

### 3.1 Important interpretation rule

A published **limit is not automatically a healthy target**.

Examples:

- 5800 rpm is a maximum take-off-speed condition, not a universal healthy RPM.
- 120 °C coolant temperature is an upper operating limit, not the desired coolant temperature.
- 950 °C EGT is a maximum limit, not a normal EGT setpoint.
- 130 °C oil temperature is a maximum normal-operation limit, not the nominal cruise temperature.

The simulator must therefore use operating-condition-dependent targets instead of sampling uniformly inside the legal limits.

---

## 4. Engine Management System and telemetry architecture

### 4.1 EMS functions

The official Operators Manual describes the EMS as providing:

- ignition control,
- fuel injection control,
- fault detection,
- internal-generator management.

The ECU consists of **Lane A and Lane B**. Both are active during normal operation; each is capable of engine control, regulation and monitoring.

Many sensors/actuators are redundant. Non-redundant sensors may be connected to only one lane, with values exchanged internally between lanes when both lanes are healthy.

**Classification:** SOURCE  
**Reference:** OM 7.5.1, p. 7-14.

### 4.2 ECU input logic

The Maintenance Manual Heavy states that the ECU receives measurements of:

- pressure,
- rotation speed,
- temperature,
- load,
- knock,

and uses them to determine:

- mixture,
- fuel injection point,
- ignition point,

for each cylinder.

**Classification:** SOURCE  
**Reference:** MMH, Engine Control Unit system description, p. 408 of PDF.

### 4.3 Fuel-injection inputs

The Operators Manual identifies the key fuel-injection input variables as:

- throttle valve position,
- engine speed,
- intake air temperature,
- ambient pressure,
- manifold pressure,
- exhaust temperature.

The ECU determines fuel quantity / injection period using the calculated air density in the airbox and continuously monitors the process.

**Classification:** SOURCE  
**Reference:** OM 7.5.3, p. 7-16.

### 4.4 CAN interfaces

Each EMS lane has:

- **Maintenance CAN**
- **Display CAN**

The Display CAN is intended for visualization of engine parameters.  
The Installation Manual states that the Display CAN uses the **CAN Aerospace protocol**.

Two independent Display CAN interfaces are provided for displaying or recording engine data.

If one Display CAN bus fails, engine information remains available on the other bus.

**Classification:** SOURCE  
**References:** OM 7.5.4, p. 7-17; IM 77-00-00; OM abnormal operation.

### 4.5 Airflow on CAN

The Operators Manual explicitly states that **airflow information is available on the Display CAN Bus**.

**Classification:** SOURCE  
**Reference:** OM 2.1, p. 2-3.

### 4.6 CAN telemetry caution

The uploaded public manuals do **not** provide the complete public Display CAN parameter dictionary / arbitration map.

Therefore:

- availability of **airflow** on Display CAN is SOURCE,
- existence of Display CAN A/B is SOURCE,
- exact CAN identifiers and full field list are **TBD**,
- do not claim that every simulator variable is directly available over Display CAN until verified.

---

## 5. Sensor baseline

### 5.1 Sensors explicitly identified in the Rotax documentation

| Sensor / signal | Role in project | Classification | Source note |
|---|---|---|---|
| Engine speed / crankshaft position | rotational state, RPM | SOURCE | CPS 1/2 documented |
| Throttle position | engine command/load input | SOURCE | TPS documented; ECU throttle used in performance model |
| Ambient pressure + temperature | environmental correction | SOURCE | AAPTS |
| Manifold air pressure | load / boost / air-path state | SOURCE | MAPS 1/2 |
| Manifold air temperature | thermal/air-path state | SOURCE | MATS 1/2 |
| Boost pressure | turbocharger/boost state | SOURCE | BPS |
| EGT 1–4 | combustion/exhaust state | SOURCE | four EGT sensors |
| Coolant temperature | cooling state | SOURCE | CTS |
| Oil temperature | lubrication thermal state | SOURCE | OTS |
| Oil pressure | lubrication pressure state | SOURCE | OPS |
| Knock | combustion abnormality input | SOURCE | KNOCK |
| Lane A/B status | EMS redundancy/health | SOURCE | dual-lane EMS |
| Display CAN A/B status | telemetry link health | SOURCE | dual Display CAN |
| Generator / electrical state | electrical health | SOURCE | generator management documented |

### 5.2 EGT sensors

The Maintenance Manual Heavy states that there are **four exhaust-gas-temperature sensors** and that they are used to regulate injection quantity.

**Classification:** SOURCE  
**Reference:** MMH, Sensors and Actuators, p. 483 of PDF.

### 5.3 Coolant temperature vs. “CHT”

Rotax documents a **Coolant Temperature Sensor (CTS)**.  
The Maintenance Manual Heavy states that the CTS measures coolant temperature **directly in the cylinder head of cylinder 4**.

The SIH problem statement requests **CHT (Cylinder Head Temperature)**, but the official Rotax baseline does not publish a separate conventional cylinder-head-metal-temperature operating limit.

Therefore the project must not write:

> “ROTAX 915 CHT max = 120 °C”

The source-backed statement is:

> “ROTAX 915 coolant temperature normal-operation max = 120 °C; the CTS measures coolant in the cylinder head of cylinder 4.”

For the generic product schema:

- `coolant_temp` = SOURCE-backed Rotax signal.
- `cht` = **TBD / ASSUMPTION** if a separate direct CHT variable is required for engine-agnostic support.

### 5.4 Lane-specific sensor availability during checks

The Operators Manual notes that during Lane/Ignition checks:

With **Lane A OFF / Lane B active**, the following values are unavailable:

- coolant temperature,
- EGT cyl. 1–4,
- ambient temperature,
- throttle lever position.

With **Lane B OFF / Lane A active**, the following are unavailable:

- oil temperature,
- oil pressure.

**Classification:** SOURCE  
**Reference:** OM Lane and Ignition Check, p. 4-16.

This is useful for later **sensor availability / plausibility / redundancy logic**.

---

## 6. Air, turbocharger and manifold baseline

### 6.1 Air path

Source-backed air path:

`Ambient → Air filter → Turbocharger → Intercooler → Airbox → Intake manifolds → Cylinders`

The throttle controls pressure in the airbox.

**Classification:** SOURCE  
**Reference:** OM 7.6, pp. 7-18 to 7-20.

### 6.2 Boost-pressure control

The wastegate controls the fraction of exhaust gas driving the turbocharger turbine.

Pneumatic valves controlled by the ECU regulate the boost pressure required to position the wastegate.

An overboost valve opens during overboost conditions to relieve excessive pressure.

**Classification:** SOURCE  
**Reference:** OM 7.6, p. 7-19.

### 6.3 Air-path residual checks

The Rotax performance-model documentation provides useful source-backed residual thresholds at **5800 rpm / sea level**:

- `p_plenum` deviation **> +20 mbar** indicates a failure in the air supply to the engine.
- `T_plenum` deviation **> +5 °C** indicates a failure in the air supply to the engine.

These are excellent candidates for early digital-twin residual rules.

**Classification:** SOURCE  
**Reference:** OM 5.2, p. 5-3.

---

## 7. Fuel-system baseline

### 7.1 Fuel pressure

Normal fuel pressure at the fuel rail:

**2.9–3.2 bar**

Temporary pressure excursion after a power-setting change:

**2.5–3.5 bar for max. 3 seconds**

**Classification:** SOURCE  
**Reference:** OM 2.1, p. 2-6.

### 7.2 Installation-interface flow requirement is NOT fuel consumption

The Installation Manual gives a fuel-system interface flow range of:

**56–150 L/h**

This is an **installation/interface requirement**, not the engine's normal fuel burn.

It must **not** be used as the simulated fuel-consumption range.

**Classification:** SOURCE with interpretation  
**Reference:** IM 73-00-00, p. 6.

### 7.3 Actual fuel-consumption modelling

Rotax provides a Performance and Fuel Consumption Model in the electronic Operators Manual package.

The model uses:

- ambient pressure,
- ambient temperature,
- RPM,
- linearized ECU throttle position.

The OM states that actual power and fuel consumption depend on installation, maintenance compliance and engine operation.

Fuel-flow data in the model is given in **kg/h** and has a stated **10% tolerance range** under specified stationary-flight conditions.

**Classification:** SOURCE  
**Reference:** OM 5.1-5.2, pp. 5-2 to 5-3.

### 7.4 Fuel-flow calibration strategy

For the initial simulator:

1. Use the official Rotax fuel-flow / power curves as the reference shape.
2. Prefer the official electronic Performance and Fuel Consumption Model over manually eyeballing graph points.
3. Preserve the model inputs:
   - RPM,
   - throttle position,
   - ambient pressure / altitude,
   - ambient temperature.
4. Add dynamic lag separately as a **DERIVED/ASSUMED** transient model.

### 7.5 ECO and POWER modes

Below approximately **97% throttle**, the ECU operates in **ECO mode**, optimizing injection/ignition for economy.

Above approximately **97% throttle**, the ECU switches to **POWER mode**, using fuel enrichment for maximum performance, especially for **take-off and climb**.

In single-lane operation, POWER mode is always active.

**Classification:** SOURCE  
**Reference:** OM 5.3, p. 5-7.

This means the simulator should include a mode transition near 97% throttle rather than using one linear fuel-flow equation across the whole throttle range.

### 7.6 Fuel-system fault clues in the Installation Manual

The Installation Manual states:

- an additional fuel-pressure sensor before the fine filter can be used to assess filter load;
- increased pressure beyond the allowed limit can indicate a contaminated fine filter;
- pressure fluctuations may originate from a clogged filter, line pulsation, kinks/restrictions, etc.

**Classification:** SOURCE  
**Reference:** IM 73-00-00, p. 12.

---

## 8. Lubrication and thermal baseline

### 8.1 Oil system

The engine uses a dry-sump forced-lubrication system.

The MMH gives approximate oil delivery rates at 5500 rpm:

- main oil pump: **~9 L/min**
- suction pump circuit: **~1.3 L/min**

**Classification:** SOURCE  
**Reference:** MMH technical data, p. 129 of PDF.

### 8.2 Oil-temperature behaviour

Source-backed constraints:

- start: ≥ -20 °C
- take-off: ≥ 50 °C
- normal operation: 50–130 °C

Rotax notes that operation below approximately **90–110 °C** may promote condensation in the lubrication system and requires the engine to reach **100 °C at least once per day** to evaporate accumulated condensation.

**Classification:** SOURCE  
**Reference:** OM 2.1, p. 2-5.

This does **not** define one universal “normal oil temperature target”; the simulator should model thermal evolution over time.

### 8.3 Coolant system

Source-backed operational limit:

- coolant normal-operation maximum: **120 °C**

Installation-interface data additionally gives:

- coolant flow at 5800 rpm: **70 L/min**
- installation hydraulic-interface temperatures up to **125 °C inlet / 130 °C outlet**

These installation figures must not be confused with the Operators Manual's normal-operation limit.

**Classification:** SOURCE  
**References:** OM 2.1, p. 2-5; IM 75-00-00, p. 5.

### 8.4 Coolant-sensor plausibility issue

The Installation Manual warns that loss of coolant can expose the sensor to air, causing the displayed temperature to be **falsely low**.

This creates a useful future fault rule:

> low/declining CTS does not always mean the engine is cooling; it may be a sensor-immersion / coolant-loss plausibility problem.

**Classification:** SOURCE  
**Reference:** IM 75-00-00, p. 13.

---

## 9. EGT baseline

### 9.1 Maximum EGT

Maximum exhaust-gas temperature:

**950 °C**

**Classification:** SOURCE  
**Reference:** OM 2.1, p. 2-5.

### 9.2 EGT split

Define:

`EGT_split = max(EGT_1, EGT_2, EGT_3, EGT_4) - min(EGT_1, EGT_2, EGT_3, EGT_4)`

Source-backed limits:

- fuel consumption >3 L/h: **EGT_split ≤ 200 °C**
- fuel consumption <3 L/h: **EGT_split ≤ 500 °C**

**Classification:** SOURCE + DERIVED formula  
**Reference:** OM 2.1, p. 2-6.

### 9.3 Simulator implication

The healthy simulator should output **four EGT channels**, not a single global EGT.

Initial healthy behaviour should maintain EGT spread within the Rotax limits.

Exact phase-specific nominal EGT values are **not published in the uploaded manuals**.

Therefore:

- EGT max = SOURCE
- EGT split max = SOURCE
- exact healthy EGT setpoint by phase = **TBD / ASSUMPTION**

---

## 10. Electrical baseline

### 10.1 Generator architecture

The 915 i uses two internal generators.

The MMH describes two permanent-magnet three-phase generators rated **200 W and 400 W**.

The Operators Manual explains that the generators and electrical-management system provide power to the EMS and, depending on configuration/state, the airframe.

**Classification:** SOURCE  
**References:** MMH technical data, p. 129 of PDF; OM 7.5, pp. 7-13 to 7-14.

### 10.2 Type A electrical interface

The Installation Manual gives the Type A airframe output as approximately:

- output voltage: **13.9–14.5 V**
- nominal: **14.2 V**
- output capacity: **max. 420 W DC at 20 °C**

**Classification:** SOURCE  
**Reference:** IM 24-00-00, p. 7.

### 10.3 Generator switching behaviour

The OM states that:

- external electrical power is needed during engine start,
- after engine speed is sufficient, Generator 2 can power the EMS,
- after a defined threshold/time, Generator 1 takes over EMS supply,
- Generator 2 can fully power the airframe when reaching **3000 rpm**,
- if Generator 1 fails, Generator 2 becomes the fail-safe EMS supply.

**Classification:** SOURCE  
**Reference:** OM 7.5, p. 7-13.

### 10.4 Electrical-health variables for the project

Source-backed state variables:

- generator selection/state,
- EMS power-source state,
- bus/output voltage where available,
- caution/warning state,
- Lane A/B state.

Exact battery state-of-charge is **not defined by these engine manuals** and should be an aircraft-side variable if later required.

---

## 11. Vibration baseline

### 11.1 Source-backed mechanical relationship

The propeller gearbox includes mechanical vibration damping / torsional vibration absorption.

**Classification:** SOURCE  
**Reference:** IM 00-00-00, p. 4; MMH technical data, p. 129 of PDF.

### 11.2 Documented vibration fault

The MMH states that **gearbox pitting can cause high-frequency vibrations**, which can be detected by dynamic engine analysis.

**Classification:** SOURCE  
**Reference:** MMH, gearbox pitting section, p. 181 of PDF.

### 11.3 Numerical vibration representation

The uploaded manuals do **not** provide a simple universal healthy vibration-amplitude range suitable for our simulator.

Therefore:

- vibration presence / gearbox-pitting relationship = SOURCE
- exact healthy RMS amplitude = **TBD**
- exact fault amplitudes = **TBD**
- initial normalized vibration signal = **ASSUMPTION**, until calibrated using another approved source or experimental data

Recommended future representation:

- RMS amplitude
- engine-order / RPM-correlated component
- high-frequency component
- optional spectral features

These representation choices are **project modelling choices**, not Rotax specifications.

---

## 12. Healthy operating profile for the simulator

> This section maps the project's mission phases to source-backed Rotax constraints.  
> The Rotax manuals do **not** publish a MALE-UAV mission profile.

| Project phase | Source-backed Rotax behaviour | Modelling status |
|---|---|---|
| Start / warm-up | Idle ≥1800 rpm; oil pressure may be high during cold start (≤7 bar); oil temp must reach ≥50 °C before take-off; coolant warms from starting condition | Mostly SOURCE |
| Take-off | 5800 rpm max; 104 kW; max 5 min; POWER mode likely at >~97% throttle; oil temp ≥50 °C | SOURCE constraints |
| Climb | POWER mode uses enrichment especially for take-off/climb; exact climb RPM/load schedule is aircraft-specific | SOURCE + TBD |
| High-altitude continuous operation | Max continuous power 99 kW @5500 rpm; critical altitude 15,000 ft; operating altitude max 23,000 ft | SOURCE constraints |
| Cruise | No universal Rotax “cruise RPM” is defined in the uploaded manuals; below ~97% throttle the engine may operate in ECO mode | TBD within SOURCE limits |
| Loiter/endurance | No Rotax loiter schedule is published | ASSUMPTION/TBD |
| Descent | No phase-specific Rotax target table is published | ASSUMPTION/TBD |
| Landing / cooldown | OM says descent/taxi normally provide cooling; at increased operating temperature, perform at least 2 min cooling run before shutdown | SOURCE |

### 12.1 Rule for Issue #2

The healthy simulator must **not** assign one constant “normal” value to each sensor.

Healthy values should be functions of at least:

- time,
- throttle,
- RPM,
- ambient pressure / altitude,
- ambient temperature,
- manifold pressure,
- manifold temperature,
- operating mode (ECO/POWER),
- thermal state.

---

## 13. Initial fault-to-sensor relationships supported by Rotax manuals

| Fault / degradation | Source-backed observable | Status |
|---|---|---|
| Fine-filter contamination / fuel restriction | abnormal upstream fuel pressure; pressure can rise as filter load increases | SOURCE |
| Fuel-pressure out of range | rail pressure outside 2.9–3.2 bar; OM prescribes reduced power / precautionary landing logic | SOURCE |
| Air-path fault | p_plenum deviation >+20 mbar at 5800 rpm / sea level; T_plenum deviation >+5 °C under same stated condition | SOURCE |
| Cooling-system / coolant-loss plausibility issue | CTS may falsely read low if sensor is no longer submerged in coolant | SOURCE |
| Gearbox pitting | high-frequency vibration | SOURCE |
| Generator 1 malfunction | Generator 2 takes over EMS supply in fail-safe mode | SOURCE |
| Display CAN A or B failure | data remains available on the working Display CAN | SOURCE |
| Dual Display CAN failure | engine parameters unavailable; OM says aircraft should land | SOURCE |
| Lane / sensor availability change | specific sensors unavailable depending on active lane during checks | SOURCE |
| Overboost condition | overboost valve opens to relieve excessive pressure | SOURCE |

### 13.1 Faults still required by the project but not yet numerically characterized

The following project fault classes are **not sufficiently quantified by these three manuals alone**:

- injector degradation / injector partial blockage,
- cylinder misfire signature,
- cooling-efficiency degradation rate,
- lubrication degradation progression,
- bearing degradation,
- generic mechanical imbalance,
- sensor drift magnitude/rate,
- exact RUL degradation laws.

Keep them as **TBD** until supported by another approved source, test data or an explicitly documented simulation assumption.

---

## 14. Injection timing representation

The MMH states that the ECU uses sensor measurements to determine the optimum **fuel injection point** and ignition points for each cylinder.

However, the uploaded manuals do **not** publish the proprietary injection-timing map.

Therefore:

- ECU-controlled injection timing = SOURCE
- existence of per-cylinder injection logic = SOURCE
- exact timing map = **TBD / proprietary**
- initial simulator timing-deviation feature = **ASSUMPTION** if needed

Do not invent a manufacturer timing table.

---

## 15. Proposed simulator state vector

### 15.1 Source-backed inputs/state

```text
time
rpm
throttle_position
ambient_pressure
ambient_temperature
altitude
airflow
manifold_pressure
manifold_temperature
boost_pressure
oil_pressure
oil_temperature
coolant_temperature
egt_1
egt_2
egt_3
egt_4
egt_split
fuel_pressure
lane_a_state
lane_b_state
display_can_a_state
display_can_b_state
generator_state
operating_mode   # ECO / POWER
```

### 15.2 Derived variables

```text
egt_split
air_path_pressure_residual
air_path_temperature_residual
expected_power
expected_fuel_flow
thermal_residuals
health_features
```

### 15.3 Variables not yet source-confirmed as live Display-CAN fields

Do **not** claim the following are all directly available on Display CAN until the interface dictionary is obtained:

- calculated fuel flow,
- all internal ECU timing values,
- battery SOC,
- vibration,
- separate direct CHT.

They may still exist in the simulator/product schema, but their acquisition method remains **TBD**.

---

## 16. Healthy digital-twin residuals

The first physics/digital-twin layer should produce expected values from the current operating condition.

Recommended first residuals:

```text
rpm_residual
manifold_pressure_residual
manifold_temperature_residual
oil_pressure_residual
oil_temperature_residual
coolant_temperature_residual
egt_1_residual
egt_2_residual
egt_3_residual
egt_4_residual
fuel_pressure_residual
fuel_flow_residual
```

For the air path, Rotax already provides two source-backed diagnostic deviations at 5800 rpm / sea level:

```text
p_plenum residual > +20 mbar → air-supply failure indication
T_plenum residual > +5 °C   → air-supply failure indication
```

These should be implemented as explicit condition-specific checks before any ML model is added.

---

## 17. What can be implemented in Issue #2 without inventing data

### Ready from source material

- RPM operating boundaries
- take-off / continuous power anchors
- altitude limits
- MAT limits
- MAP targets at 5500/5800 rpm
- oil pressure boundaries
- oil temperature boundaries
- coolant temperature limit
- EGT maximum
- EGT split calculation and limits
- ambient temperature range
- fuel pressure boundaries
- ECO / POWER transition logic
- official fuel-flow curve/model inputs
- air-path residual checks
- dual-lane / dual-CAN state logic
- generator switching logic

### Still needs an explicit assumption or another approved source

- exact thermal time constants
- exact healthy temperature targets by every mission phase
- exact EGT nominal values by RPM/load
- direct CHT numeric model
- vibration amplitude scale
- detailed injector/misfire signatures
- mechanical degradation rates
- RUL laws

---

## 18. Issue #1 completion checklist

- [x] Reference engine defined
- [x] Engine architecture documented
- [x] Official RPM / power limits documented
- [x] Oil pressure documented
- [x] Oil temperature documented
- [x] Coolant temperature documented
- [x] EGT max documented
- [x] EGT split documented
- [x] Fuel pressure documented
- [x] Ambient / altitude / manifold limits documented
- [x] Fuel-consumption model inputs documented
- [x] ECO / POWER logic documented
- [x] EMS / Lane A-B architecture documented
- [x] Display CAN architecture documented
- [x] Airflow CAN availability documented
- [x] Electrical/generator architecture documented
- [x] Vibration fault evidence documented
- [x] CHT-vs-CTS distinction documented
- [x] SOURCE / DERIVED / ASSUMPTION policy documented
- [ ] Obtain / inspect complete Display CAN parameter dictionary if publicly accessible
- [ ] Obtain the electronic Rotax Performance & Fuel Consumption Model if available in the official package
- [ ] Decide initial numerical thermal time constants and label them ASSUMPTION
- [ ] Decide initial vibration representation and label unsourced amplitudes ASSUMPTION
- [ ] Decide whether direct CHT is required in the Rotax-specific simulator or only in the generic product schema

---

## 19. Source references

### [OM]
**BRP-Rotax Operators Manual for ROTAX Engine Type 915 i A / C24 Series**  
Ref. No. OM-915 i A / C24, Part No. 898851  
Edition 0 / Revision 4 — September 01, 2022.

Main sections used:
- Chapter 2.1 — Operating Limits
- Chapter 3 — Abnormal Operation
- Chapter 4 — Standard Operation
- Chapter 5 — Performance and Fuel Consumption
- Chapter 7.5 — Electrical / EMS
- Chapter 7.6 — Air Intake and Boost Pressure Control

### [IM]
**BRP-Rotax Installation Manual for ROTAX Engine Type 915 i A / C24 Series**  
Ref. No. IM-915 i A / C24, Part No. 898871  
Edition 0 / Revision 5 — February 01, 2024.

Main sections used:
- Chapter 00-00-00 — General / engine architecture
- Chapter 24-00-00 — Electrical Power
- Chapter 73-00-00 — Engine Fuel and Control
- Chapter 75-00-00 — Cooling System
- Chapter 77-00-00 — Engine Indicating / CAN interfaces
- Chapter 79-00-00 — Lubrication

### [MMH]
**BRP-Rotax Maintenance Manual Heavy — 915 i A / C24**  
Edition 1 / Revision 0 — November 01, 2025.

Main sections used:
- technical data
- gearbox / pitting
- Engine Control Unit system description
- Sensors and Actuators

---

## 20. Modelling principle

The initial simulator should be built around this hierarchy:

```text
Official Rotax operating constraints
            ↓
Official Rotax performance relationships
            ↓
Condition-dependent healthy target
            ↓
Dynamic response model
            ↓
Simulated telemetry
            ↓
Physics/digital-twin expected state
            ↓
Residuals
            ↓
ML / fault / prognostic layers
```

The goal is not to create a fake “perfect Rotax clone”.

The goal is to create a **traceable, source-backed aero-piston-engine reference model** whose assumptions are explicit enough that later ML results can be defended.
