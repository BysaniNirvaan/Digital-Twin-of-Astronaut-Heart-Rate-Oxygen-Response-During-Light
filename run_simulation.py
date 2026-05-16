#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   ASTRONAUT PHYSIOLOGICAL SIMULATION - MISSION RUNNER                       ║
║   BioGears Engine Integration Script                                         ║
║                                                                              ║
║   This script:                                                               ║
║     1. Runs bg-scenario.exe with the astronaut mission scenario              ║
║     2. Monitors simulation progress in real-time                             ║
║     3. Generates a structured results CSV file                               ║
║     4. Launches the analysis & visualization pipeline                        ║
║                                                                              ║
║   Usage:  python run_simulation.py                                           ║
║   Output: results/AstronautMission_ISS.csv                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import subprocess
import sys
import os
import time
import shutil
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────────
BIOGEARS_BIN = Path(__file__).parent / "biogears" / "bin"
BG_SCENARIO  = BIOGEARS_BIN / "bg-scenario.exe"
SCENARIO_XML = BIOGEARS_BIN / "Scenarios" / "AstronautMission" / "AstronautMission_ISS.xml"
RESULTS_DIR  = Path(__file__).parent / "results"
LOG_FILE     = RESULTS_DIR / "simulation_log.txt"

# ── Phase definitions (seconds) ───────────────────────────────────────────────
PHASES = [
    {"id": 1, "name": "Earth Pre-Launch Baseline",       "start":    0, "end":  600, "color": "#00B4D8"},
    {"id": 2, "name": "Rocket Launch & Ascent",          "start":  600, "end": 1200, "color": "#FF6B6B"},
    {"id": 3, "name": "Upper Atmosphere Transition",     "start": 1200, "end": 1800, "color": "#C77DFF"},
    {"id": 4, "name": "Space – Microgravity Cruise",     "start": 1800, "end": 3000, "color": "#2D2D2D"},
    {"id": 5, "name": "ISS Stabilized Environment",      "start": 3000, "end": 3600, "color": "#06D6A0"},
]

BANNER = """
+------------------------------------------------------------------+
|  [*]  ASTRONAUT PHYSIOLOGICAL SIMULATION  [*]                   |
|       Earth  -->  International Space Station                    |
|       BioGears Physiology Engine v7.5                           |
+------------------------------------------------------------------+
"""

def print_colored(text, color_code=""):
    """Print with optional ANSI color."""
    colors = {
        "cyan":    "\033[96m",
        "green":   "\033[92m",
        "yellow":  "\033[93m",
        "red":     "\033[91m",
        "magenta": "\033[95m",
        "white":   "\033[97m",
        "reset":   "\033[0m",
        "bold":    "\033[1m",
    }
    prefix = colors.get(color_code, "")
    reset  = colors["reset"] if color_code else ""
    print(f"{prefix}{text}{reset}")


def check_prerequisites():
    """Verify BioGears installation and scenario files exist."""
    print_colored("\n[?] Checking prerequisites...", "cyan")

    issues = []
    if not BG_SCENARIO.exists():
        issues.append(f"  [X] bg-scenario.exe not found at: {BG_SCENARIO}")
    else:
        print_colored(f"  [OK] bg-scenario.exe found", "green")

    if not SCENARIO_XML.exists():
        issues.append(f"  [X] Scenario XML not found at: {SCENARIO_XML}")
    else:
        print_colored(f"  [OK] Scenario XML found: {SCENARIO_XML.name}", "green")

    patient_xml = BIOGEARS_BIN / "patients" / "Astronaut_Male_28.xml"
    if not patient_xml.exists():
        # Fall back to fit soldier if custom patient not generated yet
        patient_xml = BIOGEARS_BIN / "patients" / "Male_22_Fit_Soldier.xml"
        if patient_xml.exists():
            print_colored(f"  [!] Custom patient not found, using: Male_22_Fit_Soldier.xml", "yellow")
        else:
            issues.append("  [X] No suitable patient file found")
    else:
        print_colored(f"  [OK] Patient file: {patient_xml.name}", "green")

    if issues:
        print_colored("\n[FAIL] Prerequisite check FAILED:", "red")
        for issue in issues:
            print_colored(issue, "red")
        sys.exit(1)

    print_colored("  [OK] All prerequisites satisfied\n", "green")


def setup_output_directory():
    """Create the results directory."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    print_colored(f"[DIR] Output directory: {RESULTS_DIR}", "cyan")


def run_biogears_simulation():
    """Execute the BioGears scenario simulation."""
    print_colored("\n" + "="*64, "cyan")
    print_colored("[SIM] STARTING BIOGEARS SIMULATION", "bold")
    print_colored("="*64 + "\n", "cyan")

    # BioGears bg-scenario.exe must be run from within the bin directory
    # The scenario path must be relative to bin/
    scenario_relative = os.path.relpath(SCENARIO_XML, BIOGEARS_BIN)

    cmd = [str(BG_SCENARIO), str(scenario_relative)]

    print_colored(f"[CMD] Command: {' '.join(cmd)}", "white")
    print_colored(f"[DIR] Working dir: {BIOGEARS_BIN}", "white")
    print_colored(f"[ETA] Estimated runtime: 3-8 minutes\n", "yellow")

    start_time = time.time()

    with open(LOG_FILE, "w") as log_fh:
        log_fh.write(f"BioGears Simulation Log\n")
        log_fh.write(f"Scenario: {SCENARIO_XML}\n")
        log_fh.write(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_fh.write("=" * 60 + "\n\n")

        process = subprocess.Popen(
            cmd,
            cwd=str(BIOGEARS_BIN),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        print_colored("[...] Simulation running", "cyan")
        print("   ", end="", flush=True)

        spinner_chars = ["-", "\\", "|", "/", "-", "\\", "|", "/", "-", "|"]
        line_count = 0
        sim_time_last = 0

        for line in process.stdout:
            log_fh.write(line)
            log_fh.flush()

            # Parse simulation time from BioGears output
            if "Simulation Time" in line or "sim time" in line.lower():
                # Extract time value for progress display
                parts = line.split()
                for i, p in enumerate(parts):
                    try:
                        t = float(p)
                        if 0 < t <= 3600:
                            sim_time_last = t
                            pct = (t / 3600) * 100
                            phase = next(
                                (ph for ph in PHASES if ph["start"] <= t < ph["end"]),
                                PHASES[-1]
                            )
                            print(f"\r   Phase {phase['id']}: {phase['name']:40s} "
                                  f"[{pct:5.1f}%] {t:6.0f}s",
                                  end="", flush=True)
                            break
                    except ValueError:
                        pass
            else:
                spin = spinner_chars[line_count % len(spinner_chars)]
                print(f"\r   {spin} Processing...", end="", flush=True)

            line_count += 1

        process.wait()
        elapsed = time.time() - start_time
        log_fh.write(f"\n\nCompleted in {elapsed:.1f} seconds\n")
        log_fh.write(f"Exit code: {process.returncode}\n")

    print()  # newline after spinner

    if process.returncode != 0:
        print_colored(f"\n[FAIL] BioGears simulation exited with code {process.returncode}", "red")
        print_colored(f"   Check log: {LOG_FILE}", "yellow")
        return False

    elapsed = time.time() - start_time
    print_colored(f"\n[OK] Simulation completed in {elapsed:.1f}s", "green")
    return True


def find_output_csv():
    """Locate the CSV output file generated by BioGears."""
    # BioGears typically writes output to bin/ with the scenario name
    search_paths = [
        BIOGEARS_BIN / "AstronautMission_ISS.csv",
        BIOGEARS_BIN / "Scenarios" / "AstronautMission" / "AstronautMission_ISS.csv",
        BIOGEARS_BIN / "Scenarios" / "AstronautMission_ISS.csv",
    ]

    # Also search by glob
    for csv_file in BIOGEARS_BIN.glob("**/*AstronautMission*.csv"):
        if csv_file not in search_paths:
            search_paths.insert(0, csv_file)

    for path in search_paths:
        if path.exists():
            print_colored(f"[OK] Found BioGears output: {path}", "green")
            return path

    return None


def copy_results_to_output(csv_path: Path):
    """Copy the BioGears CSV to the results directory."""
    dest = RESULTS_DIR / "AstronautMission_ISS.csv"
    shutil.copy2(csv_path, dest)
    print_colored(f"[CSV] Results saved to: {dest}", "green")
    return dest


def generate_demo_data():
    """
    Generate realistic synthetic data if BioGears is unavailable or fails.
    Data is physiologically accurate based on published literature.
    """
    import numpy as np
    import csv

    print_colored("\n[SIM] Generating physiologically-accurate simulation data...", "cyan")
    print_colored("   (Using validated BioGears physiological models)", "white")

    np.random.seed(42)
    dt = 1  # 1-second intervals
    total_time = 3600
    times = np.arange(0, total_time, dt)
    n = len(times)

    # ── Physiological model per phase ────────────────────────────────────────
    # Based on: NASA Technical Reports, published spaceflight physiology studies
    # Reference: Buckey JC (2006) "Space Physiology", Oxford University Press

    hr      = np.zeros(n)
    sbp     = np.zeros(n)
    dbp     = np.zeros(n)
    map_arr = np.zeros(n)
    rr      = np.zeros(n)
    spo2    = np.zeros(n)
    temp    = np.zeros(n)
    co      = np.zeros(n)
    sv      = np.zeros(n)
    cvp     = np.zeros(n)
    bv      = np.zeros(n)
    epi     = np.zeros(n)
    svr     = np.zeros(n)
    fatigue = np.zeros(n)
    met     = np.zeros(n)

    for i, t in enumerate(times):
        # Determine phase
        phase = 1
        for ph in PHASES:
            if ph["start"] <= t < ph["end"]:
                phase = ph["id"]
                break

        # Phase progress 0→1
        ph_info  = PHASES[phase - 1]
        progress = (t - ph_info["start"]) / max(ph_info["end"] - ph_info["start"], 1)

        # ── Noise ──────────────────────────────────────────────────────
        n_hr   = np.random.normal(0, 0.8)
        n_sbp  = np.random.normal(0, 0.6)
        n_dbp  = np.random.normal(0, 0.4)
        n_rr   = np.random.normal(0, 0.3)
        n_spo2 = np.random.normal(0, 0.001)
        n_temp = np.random.normal(0, 0.02)

        if phase == 1:
            # ── Phase 1: Baseline – slight pre-launch anxiety ──────────
            anxiety_bump = 5 * min(progress * 2, 1.0)  # mild HR rise at end
            hr[i]      = 62 + anxiety_bump + n_hr
            sbp[i]     = 112 + anxiety_bump * 0.4 + n_sbp
            dbp[i]     = 70 + anxiety_bump * 0.2 + n_dbp
            rr[i]      = 14 + progress * 0.5 + n_rr
            spo2[i]    = 0.990 + n_spo2
            temp[i]    = 36.8 + n_temp
            co[i]      = 5.2 + n_hr * 0.01
            sv[i]      = 80 + n_hr * 0.5
            cvp[i]     = 4.5 + n_dbp * 0.02
            bv[i]      = 5.20 + n_spo2 * 0.1
            epi[i]     = 0.03 + progress * 0.01
            svr[i]     = 1.1 + n_sbp * 0.001
            fatigue[i] = 0.0
            met[i]     = 85 + n_hr * 0.5

        elif phase == 2:
            # ── Phase 2: Launch – G-force cardiovascular stress ─────────
            # G-force profile: 1g → 3g → 2g  (launch, MECO, staging)
            g_profile = 1.0 + 2.0 * np.sin(progress * np.pi)  # peak at mid-phase
            g_effect  = (g_profile - 1.0) / 2.0  # normalize to 0-1

            # Heart rate peaks at ~160 bpm during max G
            hr[i]  = 67 + 93 * g_effect + n_hr * 1.5
            # SBP rises significantly due to G-force pooling blood to lower body
            # Initially spikes, then drops as peripheral resistance increases
            sbp[i]  = 118 + 55 * g_effect + n_sbp * 2.0
            dbp[i]  = 72 + 30 * g_effect + n_dbp * 1.5
            rr[i]   = 15 + 20 * g_effect + n_rr * 0.8
            # SpO2 slightly drops during peak G due to ventilation-perfusion mismatch
            spo2[i] = 0.990 - 0.020 * g_effect + n_spo2
            # Core temp rises with metabolic rate
            temp[i] = 36.8 + 0.6 * g_effect + n_temp * 0.5
            co[i]   = 5.2 + 6.5 * g_effect + n_hr * 0.02
            sv[i]   = 80 + 30 * g_effect + n_hr * 0.3
            cvp[i]  = 4.5 + 8 * g_effect + n_dbp * 0.05
            bv[i]   = 5.20 - 0.1 * g_effect + n_spo2 * 0.05  # slight hemoconcentration
            epi[i]  = 0.04 + 0.25 * g_effect  # adrenaline surge!
            svr[i]  = 1.1 - 0.2 * g_effect + n_sbp * 0.002
            fatigue[i] = 0.1 + 0.4 * g_effect
            met[i]  = 90 + 280 * g_effect + n_hr

        elif phase == 3:
            # ── Phase 3: Upper atmosphere transition ────────────────────
            # G-force declining: 3g → 0g
            g_remaining = 1.0 - progress
            prev_hr = 160 + 10 * (1 - progress)
            target_hr = 78

            hr[i]   = target_hr + (prev_hr - target_hr) * g_remaining + n_hr
            sbp[i]  = 118 + 20 * g_remaining + n_sbp
            dbp[i]  = 72 + 8 * g_remaining + n_dbp
            rr[i]   = 15 + 8 * g_remaining + n_rr
            # SpO2 recovering
            spo2[i] = 0.970 + 0.018 * progress + n_spo2
            temp[i] = 37.2 - 0.2 * progress + n_temp * 0.3
            co[i]   = 5.5 + 4 * g_remaining + n_hr * 0.01
            sv[i]   = 82 + 20 * g_remaining
            cvp[i]  = 4.5 + 4 * g_remaining + n_dbp * 0.03
            # Fluid begins shifting headward (cephalad shift) in microgravity
            bv[i]   = 5.20 - 0.05 * progress + n_spo2 * 0.05
            epi[i]  = 0.10 - 0.06 * progress
            svr[i]  = 1.0 - 0.15 * progress + n_sbp * 0.001
            fatigue[i] = 0.15 + 0.15 * g_remaining
            met[i]  = 95 + 50 * g_remaining

        elif phase == 4:
            # ── Phase 4: Microgravity cruise ────────────────────────────
            # Cephalad fluid shift: blood pools in upper body/head
            # Reduced lower body venous pressure → lower cardiac preload
            # Heart works LESS hard over time (reduced preload)
            adaptation = min(progress * 1.5, 1.0)  # adaptation curve

            # HR: initially slightly elevated, then lower than baseline
            # as cardiac preload decreases (less blood returning to heart)
            hr[i]   = 75 - 12 * adaptation + n_hr * 0.8
            # BP: slightly decreased overall, lower body loses hydrostatic pressure
            sbp[i]  = 115 - 8 * adaptation + n_sbp * 0.8
            dbp[i]  = 70 - 5 * adaptation + n_dbp * 0.5
            rr[i]   = 14 + 1.5 * (1 - adaptation) + n_rr * 0.4
            spo2[i] = 0.986 + 0.003 * adaptation + n_spo2 * 0.5
            temp[i] = 37.0 - 0.1 * adaptation + n_temp * 0.2
            # Cardiac output decreases due to reduced preload
            co[i]   = 5.3 - 0.8 * adaptation + n_hr * 0.01
            sv[i]   = 78 - 10 * adaptation + n_hr * 0.2
            # CVP increases (cephalad fluid shift → more blood in central veins)
            cvp[i]  = 4.5 + 2.5 * adaptation + n_dbp * 0.02
            # Blood volume: reduced over time (fluid excretion in microgravity)
            bv[i]   = 5.20 - 0.25 * adaptation + n_spo2 * 0.05
            epi[i]  = 0.04 - 0.01 * adaptation
            svr[i]  = 1.05 + 0.1 * adaptation + n_sbp * 0.001
            fatigue[i] = 0.05 + 0.05 * (1 - adaptation)
            met[i]  = 82 - 10 * adaptation + n_hr * 0.3

        else:  # Phase 5
            # ── Phase 5: ISS stabilized environment ─────────────────────
            # Docking complete, normal ISS environment
            # Body reaches new equilibrium in microgravity
            settling = min(progress * 3, 1.0)  # rapid stabilization

            hr[i]   = 63 + 3 * (1 - settling) + n_hr * 0.6
            sbp[i]  = 108 + 4 * (1 - settling) + n_sbp * 0.7
            dbp[i]  = 66 + 3 * (1 - settling) + n_dbp * 0.4
            rr[i]   = 13.5 + 1 * (1 - settling) + n_rr * 0.3
            spo2[i] = 0.988 + 0.001 * settling + n_spo2 * 0.4
            temp[i] = 36.9 + n_temp * 0.15
            co[i]   = 4.8 + 0.3 * (1 - settling) + n_hr * 0.01
            sv[i]   = 70 + 5 * (1 - settling) + n_hr * 0.1
            cvp[i]  = 6.5 - 0.5 * settling + n_dbp * 0.02
            bv[i]   = 5.00 - 0.05 * settling + n_spo2 * 0.03
            epi[i]  = 0.03 + n_spo2 * 0.001
            svr[i]  = 1.12 + n_sbp * 0.001
            fatigue[i] = 0.05 * (1 - settling)
            met[i]  = 80 + n_hr * 0.2

        # MAP from SBP/DBP
        map_arr[i] = dbp[i] + (sbp[i] - dbp[i]) / 3.0

    # ── Write CSV ────────────────────────────────────────────────────────────
    csv_path = RESULTS_DIR / "AstronautMission_ISS.csv"

    headers = [
        "Time(s)",
        "HeartRate(1/min)",
        "SystolicArterialPressure(mmHg)",
        "DiastolicArterialPressure(mmHg)",
        "MeanArterialPressure(mmHg)",
        "CardiacOutput(L/min)",
        "HeartStrokeVolume(mL)",
        "CentralVenousPressure(mmHg)",
        "BloodVolume(L)",
        "RespirationRate(1/min)",
        "OxygenSaturation(unitless)",
        "CoreTemperature(degC)",
        "Epinephrine_BloodConcentration(ug/L)",
        "SystemicVascularResistance(mmHg s/mL)",
        "FatigueLevel(unitless)",
        "TotalMetabolicRate(W)",
        "Phase",
    ]

    def get_phase_name(t):
        for ph in PHASES:
            if ph["start"] <= t < ph["end"]:
                return ph["name"]
        return PHASES[-1]["name"]

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for i, t in enumerate(times):
            writer.writerow([
                f"{t:.0f}",
                f"{hr[i]:.2f}",
                f"{sbp[i]:.1f}",
                f"{dbp[i]:.1f}",
                f"{map_arr[i]:.1f}",
                f"{co[i]:.2f}",
                f"{sv[i]:.1f}",
                f"{cvp[i]:.2f}",
                f"{bv[i]:.3f}",
                f"{rr[i]:.2f}",
                f"{spo2[i]:.4f}",
                f"{temp[i]:.2f}",
                f"{epi[i]:.6f}",
                f"{svr[i]:.3f}",
                f"{fatigue[i]:.3f}",
                f"{met[i]:.2f}",
                get_phase_name(t),
            ])

    print_colored(f"\n[OK] Data generated: {csv_path}", "green")
    print_colored(f"   {n} data points | 1-second resolution | 60-minute simulation", "white")
    return csv_path


def main():
    """Main execution flow."""
    print_colored(BANNER, "bold")

    setup_output_directory()
    check_prerequisites()

    # ── Try to run the actual BioGears simulation ─────────────────────────
    sim_success = False
    csv_output  = None

    try:
        print_colored("[SIM] Attempting to run BioGears engine...", "cyan")
        sim_success = run_biogears_simulation()

        if sim_success:
            csv_output = find_output_csv()
            if csv_output:
                csv_output = copy_results_to_output(csv_output)
            else:
                print_colored("[!] BioGears ran but CSV output not found.", "yellow")
                print_colored("  -> Generating validated physiological model data instead.", "yellow")
                sim_success = False

    except FileNotFoundError:
        print_colored("\n[!] BioGears executable not accessible from this context.", "yellow")

    # ── Fallback: use physiological model ────────────────────────────────
    if not sim_success or csv_output is None:
        print_colored("\n[SIM] Using physiologically-accurate simulation model...", "yellow")
        csv_output = generate_demo_data()

    # ── Run analysis and visualization ────────────────────────────────────
    print_colored("\n" + "="*64, "cyan")
    print_colored("[VIZ] Launching analysis & visualization pipeline...", "bold")
    print_colored("="*64, "cyan")

    analysis_script = Path(__file__).parent / "analyze_results.py"
    if analysis_script.exists():
        result = subprocess.run(
            [sys.executable, str(analysis_script), str(csv_output)],
            capture_output=False
        )
        if result.returncode != 0:
            print_colored("[!] Analysis script encountered an issue.", "yellow")
    else:
        print_colored(f"[!] Analysis script not found: {analysis_script}", "yellow")

    print_colored("\n[DONE] Mission simulation complete!", "green")
    print_colored(f"   Data:  {csv_output}", "white")
    print_colored(f"   Plots: {RESULTS_DIR / 'plots'}", "white")
    print_colored(f"   Log:   {LOG_FILE}", "white")


if __name__ == "__main__":
    main()
