# Astronaut Physiological Simulation: Earth to ISS
## Using the BioGears Physiology Engine

### Project Overview
A time-driven, multi-phase simulation that monitors an astronaut's physiological response
during a 60-minute mission from Earth to the International Space Station.
Uses the **BioGears v7.5 Physiology Engine** with real DataRequests for 1-second logging.

---

## Project Structure
```
dt final/
├── biogears/bin/
│   ├── bg-scenario.exe              # BioGears simulation engine
│   ├── patients/
│   │   └── Astronaut_Male_28.xml    # Custom astronaut patient profile
│   ├── Scenarios/AstronautMission/
│   │   └── AstronautMission_ISS.xml # Main 60-minute scenario (5 phases)
│   └── environments/                # BioGears environment XMLs
├── results/
│   ├── AstronautMission_ISS.csv     # Real BioGears output (3600 rows)
│   ├── phase_statistics.json        # Per-phase statistical summary
│   ├── simulation_log.txt           # BioGears engine log
│   └── plots/
│       ├── 00_mission_overview.png  # All vitals combined
│       ├── 01_cardiovascular.png    # HR + Blood Pressure
│       ├── 02_respiratory_thermal.png # SpO2, RR, Temperature
│       └── 03_cardiac_metabolic.png # Cardiac Output, BV, Epinephrine
├── run_simulation.py    # MAIN SCRIPT – runs BioGears + analysis
├── analyze_results.py   # Standalone analysis + plot generator
├── dashboard.html       # Interactive web dashboard (Chart.js)
└── requirements.txt     # Python dependencies
```

---

## Mission Phases

| Phase | Name                   | Time      | G-Force     | Pressure       |
|-------|------------------------|-----------|-------------|----------------|
| 1     | Earth Pre-Launch       | 0–10 min  | 1g          | 101.3 kPa      |
| 2     | Rocket Launch & Ascent | 10–20 min | 1g → 3g     | Decreasing     |
| 3     | Upper Atm. Transition  | 20–30 min | 3g → 0g     | Very low ext.  |
| 4     | Space Microgravity     | 30–50 min | ~0g         | Controlled int.|
| 5     | ISS Environment        | 50–60 min | ~0g         | 101.3 kPa      |

---

## BioGears DataRequests (1-second interval)
- `HeartRate(1/min)` — bpm
- `SystolicArterialPressure(mmHg)` — systolic BP
- `DiastolicArterialPressure(mmHg)` — diastolic BP
- `MeanArterialPressure(mmHg)` — MAP
- `OxygenSaturation` — SpO2
- `RespirationRate(1/min)` — breathing rate
- `CoreTemperature(degC)` — internal body temperature
- `CardiacOutput(L/min)` — cardiac pump output
- `BloodVolume(L)` — total blood volume
- `Epinephrine-BloodConcentration(ug/L)` — stress hormone

---

## How to Run

### Step 1 – Install Python dependencies
```powershell
pip install matplotlib numpy
```

### Step 2 – Run full simulation pipeline
```powershell
python run_simulation.py
```
This will:
1. Run `bg-scenario.exe` with the astronaut scenario (takes ~30–50 min)
2. Save CSV output to `results/AstronautMission_ISS.csv`
3. Auto-run `analyze_results.py` to generate plots

### Step 3 – Run analysis only (if CSV exists)
```powershell
python analyze_results.py
```

### Step 4 – View the web dashboard
Open `dashboard.html` via a local server (required for CSV loading):
```powershell
python -m http.server 8080
```
Then open: http://localhost:8080/dashboard.html

---

## Simulation Results (BioGears Engine Output)

| Phase              | HR (bpm) | SBP (mmHg) | SpO2 (%) | RR (br/min) |
|--------------------|----------|------------|----------|-------------|
| Earth Pre-Launch   | 84.3     | 114.6      | 98.0     | 16.3        |
| Launch & Ascent    | 156.4    | 121.2      | 89.0     | 21.2        |
| Upper Atmosphere   | 105.8    | 118.9      | 96.0     | 21.4        |
| Microgravity       | 82.6     | 117.7      | 97.0     | 21.4        |
| ISS Environment    | 81.6     | 118.1      | 97.0     | 21.6        |

---

## Key Physiological Findings

### G-Force & Cardiovascular Response (Phase 2)
During 3g G-force, heart rate peaked at **~156 bpm** (2x baseline). Blood is
shifted to lower extremities, triggering the baroreceptor reflex. Epinephrine
surges drive the cardiovascular response. SpO2 drops to **89%** at peak G-force.

### Microgravity Fluid Redistribution (Phases 3–4)
Without gravity, hydrostatic gradients disappear. Blood redistributes headward
(cephalad shift), increasing central venous pressure. The kidneys excrete fluid,
reducing blood volume. Heart rate normalizes to **~82 bpm** — slightly below
Earth baseline due to reduced cardiac preload.

### ISS Stabilization (Phase 5)
In the controlled ISS environment, vitals stabilize: HR **~81 bpm**, SpO2 **97%**,
pressure normal. The astronaut has reached a new microgravity equilibrium.

---

## Technical Details
- **Engine**: BioGears Physiology Engine v7.5.0
- **Patient**: Male, 28 yr, 75 kg, HR baseline 62 bpm (fit athlete profile)
- **Simulation time**: 3600 seconds (60 minutes)
- **Sampling**: 1 sample/second = 3600 data points
- **Environment changes**: via BioGears `EnvironmentChangeData` XML actions
- **Exercise/Stress**: via BioGears `ExerciseData` `GenericExercise` intensity model
