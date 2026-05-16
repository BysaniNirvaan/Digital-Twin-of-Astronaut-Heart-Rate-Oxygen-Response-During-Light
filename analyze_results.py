#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Astronaut Mission - Results Analysis & Visualization
Reads the BioGears simulation CSV and generates publication-quality plots.
Usage:  python analyze_results.py [csv_path]
"""

import sys
import io
import csv
import json
import statistics
from pathlib import Path

# Force UTF-8 output for Windows console compatibility
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ── resolve CSV path ──────────────────────────────────────────────────────────
RESULTS_DIR = Path(__file__).parent / "results"
PLOTS_DIR   = RESULTS_DIR / "plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else RESULTS_DIR / "AstronautMission_ISS.csv"

PHASES = [
    {"id":1,"name":"Earth Pre-Launch","short":"Baseline",    "start":0,   "end":600,  "color":"#00B4D8"},
    {"id":2,"name":"Launch & Ascent", "short":"Launch",      "start":600, "end":1200, "color":"#FF6B6B"},
    {"id":3,"name":"Upper Atmosphere","short":"Transition",  "start":1200,"end":1800, "color":"#C77DFF"},
    {"id":4,"name":"Microgravity",    "short":"Space Cruise","start":1800,"end":3000, "color":"#888888"},
    {"id":5,"name":"ISS Environment", "short":"ISS Recovery","start":3000,"end":3600, "color":"#06D6A0"},
]

# ── load CSV ──────────────────────────────────────────────────────────────────
print(f"[READ] {csv_path}")
if not csv_path.exists():
    print("[ERROR] CSV not found. Run run_simulation.py first.")
    sys.exit(1)

with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
    reader = csv.DictReader(f)
    rows   = list(reader)
    cols   = reader.fieldnames or []

print(f"   {len(rows)} rows | {len(cols)} columns")

# ── print column names to help identify the correct keys ─────────────────────
print("[COLS] Available columns:")
for c in cols[:30]:
    print(f"       {c}")

def col(rows, name):
    candidates = [c for c in cols if name.lower() in c.lower()]
    if not candidates:
        return []
    key = candidates[0]
    out = []
    for r in rows:
        try:
            out.append(float(r[key]))
        except Exception:
            out.append(None)
    return out

time_s  = col(rows, "Time")
hr      = col(rows, "HeartRate")
sbp     = col(rows, "SystolicArterial")
dbp     = col(rows, "DiastolicArterial")
map_v   = col(rows, "MeanArterial")
rr      = col(rows, "RespirationRate")
spo2    = col(rows, "OxygenSaturation")
temp    = col(rows, "CoreTemperature")
co      = col(rows, "CardiacOutput")
bv      = col(rows, "BloodVolume")
epi     = col(rows, "Epinephrine")

time_min = [t/60 for t in time_s] if time_s else []

# ── per-phase statistics ──────────────────────────────────────────────────────
def phase_stats(values, time_seconds):
    stats = {}
    for ph in PHASES:
        subset = [v for v,t in zip(values, time_seconds)
                  if v is not None and ph["start"] <= t < ph["end"]]
        if subset:
            stats[ph["id"]] = {
                "mean": round(statistics.mean(subset), 2),
                "max":  round(max(subset), 2),
                "min":  round(min(subset), 2),
            }
    return stats

stats = {
    "HeartRate":       phase_stats(hr,   time_s),
    "SystolicBP":      phase_stats(sbp,  time_s),
    "DiastolicBP":     phase_stats(dbp,  time_s),
    "SpO2":            phase_stats(spo2, time_s),
    "RespirationRate": phase_stats(rr,   time_s),
    "CoreTemperature": phase_stats(temp, time_s),
    "CardiacOutput":   phase_stats(co,   time_s),
}

summary_path = RESULTS_DIR / "phase_statistics.json"
with open(summary_path, "w") as f:
    json.dump({"phases": PHASES, "statistics": stats}, f, indent=2)
print(f"[OK] Statistics saved: {summary_path}")

# ── try matplotlib ────────────────────────────────────────────────────────────
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("[WARN] matplotlib not installed. Run: pip install matplotlib numpy")

if not HAS_MPL or not time_min:
    print("[SKIP] Plotting skipped.")
    sys.exit(0)

plt.style.use("dark_background")
DARK_BG   = "#0D0D1A"
PANEL_BG  = "#111122"

def add_phase_bands(ax):
    for ph in PHASES:
        ax.axvspan(ph["start"]/60, ph["end"]/60, alpha=0.08, color=ph["color"])
        ax.axvline(ph["start"]/60, color=ph["color"], linewidth=0.7,
                   linestyle="--", alpha=0.5)

def add_phase_legend(ax):
    patches = [mpatches.Patch(color=ph["color"], label=f"P{ph['id']}: {ph['short']}")
               for ph in PHASES]
    ax.legend(handles=patches, loc="upper right", fontsize=7, framealpha=0.3, ncol=2)

# ── FIGURE 1: Heart Rate & Blood Pressure ─────────────────────────────────────
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
fig.patch.set_facecolor(DARK_BG)
for ax in (ax1, ax2):
    ax.set_facecolor(PANEL_BG)

fig.suptitle("Astronaut Mission - Cardiovascular Response  (Earth to ISS)",
             fontsize=14, fontweight="bold", color="white", y=0.98)

add_phase_bands(ax1)
if hr:
    ax1.plot(time_min, hr, color="#FF6B6B", linewidth=1.5, label="Heart Rate")
ax1.set_ylabel("Heart Rate (bpm)", color="white", fontsize=11)
ax1.set_ylim(50, 190)
ax1.tick_params(colors="white")
ax1.grid(axis="y", alpha=0.2)
for ph in PHASES:
    mid = (ph["start"] + ph["end"]) / 120
    ax1.text(mid, 183, f"P{ph['id']}", ha="center",
             fontsize=8, color=ph["color"], fontweight="bold")
add_phase_legend(ax1)

add_phase_bands(ax2)
if sbp:
    ax2.plot(time_min, sbp, color="#00B4D8", linewidth=1.5, label="Systolic BP")
if dbp:
    ax2.plot(time_min, dbp, color="#90E0EF", linewidth=1.5, label="Diastolic BP", alpha=0.8)
if map_v:
    ax2.plot(time_min, map_v, color="#ADE8F4", linewidth=1,
             linestyle=":", label="MAP", alpha=0.7)
if sbp and dbp:
    ax2.fill_between(time_min, dbp, sbp, alpha=0.12, color="#00B4D8")
ax2.set_ylabel("Blood Pressure (mmHg)", color="white", fontsize=11)
ax2.set_xlabel("Mission Time (minutes)", color="white", fontsize=11)
ax2.legend(loc="upper right", fontsize=8, framealpha=0.3)
ax2.tick_params(colors="white")
ax2.grid(axis="y", alpha=0.2)

plt.tight_layout()
out = PLOTS_DIR / "01_cardiovascular.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.close()
print(f"[PLOT] Saved: {out.name}")

# ── FIGURE 2: SpO2, Respiration Rate, Temperature ────────────────────────────
fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
fig.patch.set_facecolor(DARK_BG)
for ax in axes:
    ax.set_facecolor(PANEL_BG)
fig.suptitle("Astronaut Mission - Respiratory & Thermal Response",
             fontsize=14, fontweight="bold", color="white", y=0.99)

ax = axes[0]
add_phase_bands(ax)
spo2_pct = [v*100 if v is not None and v < 2 else v for v in spo2]
if spo2_pct:
    ax.plot(time_min, spo2_pct, color="#06D6A0", linewidth=1.5)
ax.axhline(95, color="#FF6B6B", linestyle="--", linewidth=0.8,
           alpha=0.6, label="Clinical threshold 95%")
ax.set_ylabel("SpO2 (%)", color="white", fontsize=11)
ax.set_ylim(88, 101)
ax.legend(fontsize=8, framealpha=0.3)
ax.tick_params(colors="white")
ax.grid(axis="y", alpha=0.2)

ax = axes[1]
add_phase_bands(ax)
if rr:
    ax.plot(time_min, rr, color="#C77DFF", linewidth=1.5)
ax.set_ylabel("Resp. Rate (br/min)", color="white", fontsize=11)
ax.tick_params(colors="white")
ax.grid(axis="y", alpha=0.2)

ax = axes[2]
add_phase_bands(ax)
if temp:
    ax.plot(time_min, temp, color="#FFB703", linewidth=1.5)
ax.set_ylabel("Core Temp (degC)", color="white", fontsize=11)
ax.set_xlabel("Mission Time (minutes)", color="white", fontsize=11)
ax.tick_params(colors="white")
ax.grid(axis="y", alpha=0.2)

plt.tight_layout()
out = PLOTS_DIR / "02_respiratory_thermal.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.close()
print(f"[PLOT] Saved: {out.name}")

# ── FIGURE 3: Cardiac Output, Blood Volume, Epinephrine ──────────────────────
fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
fig.patch.set_facecolor(DARK_BG)
for ax in axes:
    ax.set_facecolor(PANEL_BG)
fig.suptitle("Astronaut Mission - Cardiac & Metabolic Response",
             fontsize=14, fontweight="bold", color="white", y=0.99)

for data, label, color, ax in [
    (co,  "Cardiac Output (L/min)", "#FF9F1C", axes[0]),
    (bv,  "Blood Volume (L)",       "#2EC4B6", axes[1]),
    (epi, "Epinephrine (ug/L)",     "#E71D36", axes[2]),
]:
    add_phase_bands(ax)
    if data:
        ax.plot(time_min, data, color=color, linewidth=1.5)
    ax.set_ylabel(label, color="white", fontsize=10)
    ax.tick_params(colors="white")
    ax.grid(axis="y", alpha=0.2)

axes[2].set_xlabel("Mission Time (minutes)", color="white", fontsize=11)
add_phase_legend(axes[0])

plt.tight_layout()
out = PLOTS_DIR / "03_cardiac_metabolic.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.close()
print(f"[PLOT] Saved: {out.name}")

# ── FIGURE 4: Mission Overview (all vitals) ───────────────────────────────────
fig = plt.figure(figsize=(16, 12))
fig.patch.set_facecolor("#0A0A1A")
fig.suptitle("ASTRONAUT MISSION: EARTH to ISS  |  Complete Physiological Overview",
             fontsize=13, fontweight="bold", color="white", y=0.98)

gs = fig.add_gridspec(3, 2, hspace=0.45, wspace=0.35,
                      left=0.08, right=0.97, top=0.93, bottom=0.07)
plot_defs = [
    (hr,       "Heart Rate (bpm)",         "#FF6B6B", gs[0, 0]),
    (sbp,      "Systolic BP (mmHg)",       "#00B4D8", gs[0, 1]),
    (spo2_pct, "SpO2 (%)",                 "#06D6A0", gs[1, 0]),
    (rr,       "Resp. Rate (br/min)",      "#C77DFF", gs[1, 1]),
    (temp,     "Core Temperature (degC)",  "#FFB703", gs[2, 0]),
    (co,       "Cardiac Output (L/min)",   "#FF9F1C", gs[2, 1]),
]
for data, label, color, spec in plot_defs:
    ax = fig.add_subplot(spec)
    ax.set_facecolor(PANEL_BG)
    add_phase_bands(ax)
    if data:
        ax.plot(time_min, data, color=color, linewidth=1.2)
    ax.set_title(label, color="white", fontsize=9, pad=4)
    ax.tick_params(colors="#AAAAAA", labelsize=7)
    ax.set_xlabel("Time (min)", color="#AAAAAA", fontsize=7)
    ax.grid(axis="y", alpha=0.15)
    for spine in ax.spines.values():
        spine.set_edgecolor("#333355")

patches = [mpatches.Patch(color=ph["color"], label=f"Phase {ph['id']}: {ph['name']}")
           for ph in PHASES]
fig.legend(handles=patches, loc="lower center", ncol=5,
           fontsize=8, framealpha=0.2, bbox_to_anchor=(0.5, 0.01))

out = PLOTS_DIR / "00_mission_overview.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.close()
print(f"[PLOT] Saved: {out.name}")

# ── Phase summary table ───────────────────────────────────────────────────────
print("\n" + "="*70)
print(f"  {'PHASE':<28}  {'HR(bpm)':>9}  {'SBP(mmHg)':>10}  {'SpO2(%)':>8}  {'RR(br)':>7}")
print("-"*70)
for ph in PHASES:
    pid = ph["id"]
    def g(key):
        return stats.get(key, {}).get(pid, {}).get("mean", "-")
    spo2_v = g("SpO2")
    spo2_display = round(spo2_v * 100, 1) if isinstance(spo2_v, float) else spo2_v
    print(f"  P{pid} {ph['name']:<26}  {g('HeartRate'):>9}  {g('SystolicBP'):>10}  "
          f"{spo2_display:>8}  {g('RespirationRate'):>7}")
print("="*70)
print(f"\n[DONE] All plots saved to: {PLOTS_DIR}")
