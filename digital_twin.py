#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
  CARDIO-RESPIRATORY DIGITAL TWIN
  Astronaut Mission: Earth -> International Space Station
=============================================================================
  Mirrors BioGears physiological data through a rule-based digital twin model.
  Models: Heart | Lungs | Oxygen Delivery System | Overall Health Scorer

  Input:  results/AstronautMission_ISS.csv  (BioGears DataRequests output)
  Output: results/digital_twin_results.csv  (per-second derived metrics)

  Usage:
    python digital_twin.py [optional_csv_path]
=============================================================================
"""

import sys
import io
import csv
import json
import math
from pathlib import Path

# Windows console UTF-8 fix
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
RESULTS_DIR = Path(__file__).parent / "results"
INPUT_CSV   = Path(sys.argv[1]) if len(sys.argv) > 1 else RESULTS_DIR / "AstronautMission_ISS.csv"
OUTPUT_CSV  = RESULTS_DIR / "digital_twin_results.csv"
OUTPUT_JSON = RESULTS_DIR / "digital_twin_summary.json"

PHASES = [
    {"id": 1, "name": "Earth Pre-Launch",    "start":    0, "end":  600},
    {"id": 2, "name": "Launch & Ascent",     "start":  600, "end": 1200},
    {"id": 3, "name": "Upper Atmosphere",    "start": 1200, "end": 1800},
    {"id": 4, "name": "Microgravity Cruise", "start": 1800, "end": 3000},
    {"id": 5, "name": "ISS Environment",     "start": 3000, "end": 3600},
]

# Normal physiological reference ranges (NASA & clinical standards)
NORMAL = {
    "hr_rest":     62,   # bpm  (fit astronaut baseline)
    "hr_max":     120,   # bpm  (warning threshold)
    "hr_critical":160,   # bpm
    "sbp_normal": 120,   # mmHg
    "sbp_high":   140,
    "sbp_max":    160,
    "dbp_normal":  80,
    "dbp_high":    90,
    "spo2_normal":  97,  # %
    "spo2_warn":    90,
    "spo2_critical":85,
    "rr_normal":    16,  # breaths/min
    "rr_high":      22,
    "rr_critical":  30,
    "co_normal":   5.5,  # L/min
    "co_low":      4.0,
}


# ===========================================================================
# MODULE 1: HEART MODEL
# ===========================================================================

def compute_heart_model(hr: float, sbp: float, dbp: float, co: float) -> dict:
    """
    Computes cardiovascular digital twin state.

    Cardiovascular Stress Index (CSI):
      - Derived from heart rate deviation from resting baseline,
        pulse pressure (SBP-DBP), and rate-pressure product.
      - Normalized 0-100 scale.

    Formulas:
      HR deviation score   = (HR - HR_rest) / (HR_critical - HR_rest) * 50
      Pulse pressure score = (PP - 40) / 60 * 25   [PP = SBP - DBP]
      Rate-Pressure Product= (HR * SBP) / 1000       [clinical risk marker]
      RPP score            = (RPP - 6) / 24 * 25
      CSI = clamp(HR_dev + PP_score + RPP_score, 0, 100)
    """
    hr   = hr   or NORMAL["hr_rest"]
    sbp  = sbp  or NORMAL["sbp_normal"]
    dbp  = dbp  or NORMAL["dbp_normal"]
    co   = co   or NORMAL["co_normal"]

    # Heart Rate deviation
    hr_dev = max(0.0, hr - NORMAL["hr_rest"])
    hr_score = (hr_dev / (NORMAL["hr_critical"] - NORMAL["hr_rest"])) * 50

    # Pulse Pressure
    pp = sbp - dbp
    pp_score = max(0.0, (pp - 40) / 60) * 25

    # Rate-Pressure Product (x1000) – cardiac workload
    rpp = (hr * sbp) / 1000.0
    rpp_score = max(0.0, (rpp - 6.0) / 24.0) * 25

    csi = min(100.0, hr_score + pp_score + rpp_score)

    # Stroke volume efficiency: actual CO vs expected CO at this HR
    expected_co = (hr / NORMAL["hr_rest"]) * NORMAL["co_normal"]
    sv_efficiency = min(1.0, co / expected_co) * 100 if expected_co > 0 else 80.0

    # Heart stress level label
    if hr > NORMAL["hr_critical"] or csi > 75:
        heart_status = "CRITICAL"
    elif hr > NORMAL["hr_max"] or csi > 45:
        heart_status = "WARNING"
    else:
        heart_status = "NORMAL"

    return {
        "CardioStressIndex":   round(csi, 2),
        "HeartRateDeviation":  round(hr_dev, 2),
        "PulsePressure":       round(pp, 2),
        "RatePressureProduct": round(rpp, 3),
        "StrokeVolEfficiency": round(sv_efficiency, 2),
        "HeartStatus":         heart_status,
        # Flags
        "HighHR_Flag":         hr > NORMAL["hr_max"],
        "CriticalHR_Flag":     hr > NORMAL["hr_critical"],
        "HighBP_Flag":         sbp > NORMAL["sbp_high"],
        "CriticalBP_Flag":     sbp > NORMAL["sbp_max"],
    }


# ===========================================================================
# MODULE 2: LUNG MODEL
# ===========================================================================

def compute_lung_model(spo2_raw: float, rr: float, co2_pp: float = None) -> dict:
    """
    Computes pulmonary/respiratory digital twin state.

    SpO2 is stored as fraction (0.98) in BioGears -> convert to %.

    Oxygen Exchange Efficiency (OEE):
      - Measures how well the lungs are oxygenating the blood.
      - OEE = SpO2_pct * (1 - respiratory_penalty) * 100
        where respiratory_penalty penalises abnormal RR.

    Formulas:
      SpO2 penalty   = max(0, (100-SpO2) - 3) / 15   [3% below 97 is acceptable]
      RR penalty     = max(0, (RR - rr_normal) / rr_critical) * 0.3
      OEE            = (SpO2_pct / 100) * (1 - RR_penalty) * 100
    """
    # Convert fraction -> percent if needed
    spo2 = (spo2_raw * 100) if spo2_raw is not None and spo2_raw < 2 else (spo2_raw or 97)
    rr   = rr or NORMAL["rr_normal"]

    # Oxygen Exchange Efficiency
    rr_penalty = max(0.0, (rr - NORMAL["rr_normal"]) / NORMAL["rr_critical"]) * 0.3
    oee = (spo2 / 100.0) * (1.0 - rr_penalty) * 100.0
    oee = max(0.0, min(100.0, oee))

    # Hypoxia severity (0-100): how far below 97%
    hypoxia_index = max(0.0, (97 - spo2) / (97 - NORMAL["spo2_critical"]) * 100)
    hypoxia_index = min(100.0, hypoxia_index)

    # Lung status
    if spo2 < NORMAL["spo2_critical"] or rr > NORMAL["rr_critical"]:
        lung_status = "CRITICAL"
    elif spo2 < NORMAL["spo2_warn"] or rr > NORMAL["rr_high"]:
        lung_status = "WARNING"
    else:
        lung_status = "NORMAL"

    return {
        "OxygenExchangeEfficiency": round(oee, 2),
        "SpO2_Percent":             round(spo2, 2),
        "HypoxiaIndex":             round(hypoxia_index, 2),
        "RespirationRateRaw":       round(rr, 2),
        "LungStatus":               lung_status,
        # Flags
        "LowSpO2_Flag":             spo2 < NORMAL["spo2_warn"],
        "CriticalSpO2_Flag":        spo2 < NORMAL["spo2_critical"],
        "HighRR_Flag":              rr > NORMAL["rr_high"],
        "CriticalRR_Flag":          rr > NORMAL["rr_critical"],
    }


# ===========================================================================
# MODULE 3: OXYGEN DELIVERY MODEL
# ===========================================================================

def compute_oxygen_delivery(co: float, spo2_pct: float, bv: float = None) -> dict:
    """
    Estimates systemic oxygen transport efficiency.

    Oxygen Delivery Index (ODI):
      - Based on the Fick principle: DO2 = CO * CaO2
        where CaO2 (arterial oxygen content) ~ 1.34 * Hb * SpO2
        Simplified: ODI = (CO / co_normal) * (SpO2 / 100) * 100

    Blood Volume Factor adjusts for fluid shifts in microgravity.

    Oxygen Transport Score (0-100):
      OTS = ODI adjusted for blood volume changes
    """
    co  = co  or NORMAL["co_normal"]
    spo2_pct = spo2_pct or 97.0
    bv  = bv  or 5.2

    # Oxygen Delivery Index (normalised DO2)
    co_norm  = co / NORMAL["co_normal"]
    spo2_norm = spo2_pct / 100.0
    odi = co_norm * spo2_norm * 100.0

    # Blood volume factor (5.2L = baseline for 75kg astronaut)
    bv_factor = bv / 5.2
    ots = min(100.0, odi * bv_factor)

    # Tissue oxygenation sufficiency
    if ots < 60:
        o2_delivery_status = "CRITICAL"
    elif ots < 80:
        o2_delivery_status = "WARNING"
    else:
        o2_delivery_status = "NORMAL"

    return {
        "OxygenDeliveryIndex":    round(odi, 2),
        "OxygenTransportScore":   round(ots, 2),
        "CardiacOutput_Norm":     round(co_norm * 100, 2),
        "BloodVolumeFactor":      round(bv_factor, 4),
        "OxygenDeliveryStatus":   o2_delivery_status,
    }


# ===========================================================================
# MODULE 4: OVERALL HEALTH SCORER
# ===========================================================================

def compute_health_score(heart: dict, lung: dict, oxygen: dict) -> dict:
    """
    Computes overall physiological health state (0-100) and status label.

    Weighted composite score:
      Health = 0.40 * heart_score + 0.35 * lung_score + 0.25 * o2_score

    Anomaly detection:
      - High HR (>120 bpm)
      - Low SpO2 (<90%)
      - Elevated RR (>22 br/min)
      - Critical BP
      - Low O2 Delivery
    """
    # Invert stress/hypoxia to get "health" scores
    heart_health = max(0.0, 100 - heart["CardioStressIndex"])
    lung_health  = lung["OxygenExchangeEfficiency"]
    o2_health    = oxygen["OxygenTransportScore"]

    # Weighted composite
    overall = (0.40 * heart_health + 0.35 * lung_health + 0.25 * o2_health)
    overall = max(0.0, min(100.0, overall))

    # Anomaly list
    anomalies = []
    if heart["HighHR_Flag"]:
        anomalies.append("HIGH_HEART_RATE")
    if heart["CriticalHR_Flag"]:
        anomalies.append("CRITICAL_HEART_RATE")
    if lung["LowSpO2_Flag"]:
        anomalies.append("LOW_OXYGEN_SATURATION")
    if lung["CriticalSpO2_Flag"]:
        anomalies.append("CRITICAL_HYPOXIA")
    if lung["HighRR_Flag"]:
        anomalies.append("ELEVATED_RESPIRATION")
    if heart["CriticalBP_Flag"]:
        anomalies.append("CRITICAL_BLOOD_PRESSURE")
    if oxygen["OxygenTransportScore"] < 70:
        anomalies.append("IMPAIRED_O2_DELIVERY")

    # Overall status (most severe system drives overall)
    statuses = [heart["HeartStatus"], lung["LungStatus"], oxygen["OxygenDeliveryStatus"]]
    if "CRITICAL" in statuses:
        overall_status = "CRITICAL"
        status_color   = "RED"
    elif "WARNING" in statuses or overall < 70:
        overall_status = "WARNING"
        status_color   = "YELLOW"
    else:
        overall_status = "NORMAL"
        status_color   = "GREEN"

    return {
        "HealthScore":        round(overall, 2),
        "HealthStatus":       overall_status,
        "StatusColor":        status_color,
        "HeartHealthScore":   round(heart_health, 2),
        "LungHealthScore":    round(lung_health, 2),
        "O2HealthScore":      round(o2_health, 2),
        "AnomalyCount":       len(anomalies),
        "Anomalies":          "|".join(anomalies) if anomalies else "NONE",
    }


# ===========================================================================
# HELPER: get phase name from time
# ===========================================================================

def get_phase(t: float) -> str:
    for ph in PHASES:
        if ph["start"] <= t < ph["end"]:
            return ph["name"]
    return PHASES[-1]["name"]


# ===========================================================================
# MAIN PIPELINE
# ===========================================================================

def run_digital_twin():
    print("[DT] Cardio-Respiratory Digital Twin")
    print("[DT] BioGears Astronaut Mission: Earth -> ISS")
    print("=" * 60)

    if not INPUT_CSV.exists():
        print(f"[ERROR] Input CSV not found: {INPUT_CSV}")
        print("        Run run_simulation.py first.")
        sys.exit(1)

    print(f"[READ] {INPUT_CSV}")

    with open(INPUT_CSV, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        rows   = list(reader)
        cols   = reader.fieldnames or []

    print(f"[INFO] {len(rows)} rows, {len(cols)} columns")

    # Column name resolver (fuzzy match)
    def find_col(keyword):
        matches = [c for c in cols if keyword.lower() in c.lower()]
        return matches[0] if matches else None

    col_time  = find_col("Time")
    col_hr    = find_col("HeartRate")
    col_sbp   = find_col("SystolicArterial")
    col_dbp   = find_col("DiastolicArterial")
    col_co    = find_col("CardiacOutput")
    col_spo2  = find_col("OxygenSaturation")
    col_rr    = find_col("RespirationRate")
    col_bv    = find_col("BloodVolume")

    print(f"[COLS] HR={col_hr} | SBP={col_sbp} | SpO2={col_spo2} | RR={col_rr}")

    # Output CSV header
    out_headers = [
        "Time(s)", "Phase",
        # Raw inputs (echoed)
        "HeartRate(bpm)", "SystolicBP(mmHg)", "DiastolicBP(mmHg)",
        "CardiacOutput(L/min)", "SpO2(%)", "RespirationRate(br/min)",
        # Heart model
        "CardioStressIndex(0-100)", "PulsePressure(mmHg)", "RatePressureProduct",
        "StrokeVolEfficiency(%)", "HeartStatus",
        # Lung model
        "OxygenExchangeEfficiency(0-100)", "HypoxiaIndex(0-100)", "LungStatus",
        # O2 delivery
        "OxygenDeliveryIndex(0-100)", "OxygenTransportScore(0-100)",
        "BloodVolumeFactor", "OxygenDeliveryStatus",
        # Health
        "HealthScore(0-100)", "HealthStatus", "StatusColor",
        "HeartHealthScore", "LungHealthScore", "O2HealthScore",
        "AnomalyCount", "Anomalies",
    ]

    def safe_float(row, col):
        if col is None:
            return None
        try:
            return float(row.get(col, ""))
        except (ValueError, TypeError):
            return None

    output_rows = []
    phase_accum = {ph["name"]: {
        "CSI": [], "OEE": [], "OTS": [], "Health": [],
        "StatusCounts": {"NORMAL": 0, "WARNING": 0, "CRITICAL": 0}
    } for ph in PHASES}

    print("[DT]  Processing time series...")

    for row in rows:
        t    = safe_float(row, col_time)
        if t is None:
            continue

        hr   = safe_float(row, col_hr)
        sbp  = safe_float(row, col_sbp)
        dbp  = safe_float(row, col_dbp)
        co   = safe_float(row, col_co)
        spo2 = safe_float(row, col_spo2)
        rr   = safe_float(row, col_rr)
        bv   = safe_float(row, col_bv)

        # Run digital twin modules
        heart  = compute_heart_model(hr, sbp, dbp, co)
        lung   = compute_lung_model(spo2, rr)
        oxygen = compute_oxygen_delivery(co, lung["SpO2_Percent"], bv)
        health = compute_health_score(heart, lung, oxygen)
        phase  = get_phase(t)

        # Accumulate for summary
        if phase in phase_accum:
            pa = phase_accum[phase]
            pa["CSI"].append(heart["CardioStressIndex"])
            pa["OEE"].append(lung["OxygenExchangeEfficiency"])
            pa["OTS"].append(oxygen["OxygenTransportScore"])
            pa["Health"].append(health["HealthScore"])
            pa["StatusCounts"][health["HealthStatus"]] = \
                pa["StatusCounts"].get(health["HealthStatus"], 0) + 1

        output_rows.append([
            f"{t:.0f}", phase,
            f"{hr:.2f}" if hr else "", f"{sbp:.1f}" if sbp else "",
            f"{dbp:.1f}" if dbp else "", f"{co:.2f}" if co else "",
            f"{lung['SpO2_Percent']:.2f}", f"{rr:.2f}" if rr else "",
            heart["CardioStressIndex"], heart["PulsePressure"],
            heart["RatePressureProduct"], heart["StrokeVolEfficiency"],
            heart["HeartStatus"],
            lung["OxygenExchangeEfficiency"], lung["HypoxiaIndex"],
            lung["LungStatus"],
            oxygen["OxygenDeliveryIndex"], oxygen["OxygenTransportScore"],
            oxygen["BloodVolumeFactor"], oxygen["OxygenDeliveryStatus"],
            health["HealthScore"], health["HealthStatus"], health["StatusColor"],
            health["HeartHealthScore"], health["LungHealthScore"],
            health["O2HealthScore"], health["AnomalyCount"], health["Anomalies"],
        ])

    # Write output CSV
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(out_headers)
        writer.writerows(output_rows)

    print(f"[OK]  Digital twin CSV: {OUTPUT_CSV}")

    # Build JSON summary
    def avg(lst):
        return round(sum(lst) / len(lst), 2) if lst else 0

    summary = {"phases": []}
    for ph in PHASES:
        pa = phase_accum[ph["name"]]
        dominant = max(pa["StatusCounts"], key=pa["StatusCounts"].get) \
            if any(pa["StatusCounts"].values()) else "NORMAL"
        summary["phases"].append({
            "id": ph["id"],
            "name": ph["name"],
            "time_range": f"{ph['start']}s - {ph['end']}s",
            "avg_CardioStressIndex":        avg(pa["CSI"]),
            "avg_OxygenExchangeEfficiency": avg(pa["OEE"]),
            "avg_OxygenTransportScore":     avg(pa["OTS"]),
            "avg_HealthScore":              avg(pa["Health"]),
            "dominant_HealthStatus":        dominant,
            "status_distribution":          pa["StatusCounts"],
        })

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"[OK]  Phase summary JSON: {OUTPUT_JSON}")

    # Print phase summary table
    print("\n" + "=" * 78)
    print(f"  {'PHASE':<26}  {'CSI':>7}  {'OEE(%)':>8}  {'OTS(%)':>8}  {'Health':>8}  {'Status':<10}")
    print("-" * 78)
    for ph_sum in summary["phases"]:
        print(f"  P{ph_sum['id']} {ph_sum['name']:<24}  "
              f"{ph_sum['avg_CardioStressIndex']:>7.1f}  "
              f"{ph_sum['avg_OxygenExchangeEfficiency']:>8.1f}  "
              f"{ph_sum['avg_OxygenTransportScore']:>8.1f}  "
              f"{ph_sum['avg_HealthScore']:>8.1f}  "
              f"{ph_sum['dominant_HealthStatus']:<10}")
    print("=" * 78)
    print(f"\n[DONE] Digital twin complete. {len(output_rows)} time steps processed.")
    print(f"       CSV  : {OUTPUT_CSV}")
    print(f"       JSON : {OUTPUT_JSON}")

    return OUTPUT_CSV, OUTPUT_JSON


if __name__ == "__main__":
    run_digital_twin()
