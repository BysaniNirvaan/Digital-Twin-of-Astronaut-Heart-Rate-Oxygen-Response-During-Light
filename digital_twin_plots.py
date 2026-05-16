#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Digital Twin Visualization – plots derived metrics from digital_twin_results.csv
Usage:  python digital_twin_plots.py
"""
import sys, io, csv
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

RESULTS_DIR = Path(__file__).parent / "results"
DT_CSV      = RESULTS_DIR / "digital_twin_results.csv"
PLOTS_DIR   = RESULTS_DIR / "plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

PHASES = [
    {"id":1,"name":"Earth Pre-Launch","start":0,  "end":600,  "color":"#00B4D8"},
    {"id":2,"name":"Launch & Ascent", "start":600,"end":1200, "color":"#FF6B6B"},
    {"id":3,"name":"Upper Atm.",      "start":1200,"end":1800,"color":"#C77DFF"},
    {"id":4,"name":"Microgravity",    "start":1800,"end":3000,"color":"#888888"},
    {"id":5,"name":"ISS",             "start":3000,"end":3600,"color":"#06D6A0"},
]

if not DT_CSV.exists():
    print(f"[ERROR] {DT_CSV} not found. Run digital_twin.py first.")
    sys.exit(1)

with open(DT_CSV, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows   = list(reader)
    cols   = reader.fieldnames or []

print(f"[READ] {len(rows)} rows from {DT_CSV.name}")

def col(name):
    candidates = [c for c in cols if name.lower() in c.lower()]
    if not candidates: return []
    key = candidates[0]
    out = []
    for r in rows:
        try:    out.append(float(r[key]))
        except: out.append(None)
    return out

time_s   = col("Time")
time_min = [t/60 for t in time_s] if time_s else []
csi      = col("CardioStressIndex")
oee      = col("OxygenExchange")
ots      = col("OxygenTransport")
health   = col("HealthScore")
heart_h  = col("HeartHealth")
lung_h   = col("LungHealth")
o2_h     = col("O2Health")
pp       = col("PulsePressure")
hyp      = col("HypoxiaIndex")
bvf      = col("BloodVolume")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

DARK    = "#0D0D1A"
PANEL   = "#111122"
plt.style.use("dark_background")

def add_bands(ax):
    for ph in PHASES:
        ax.axvspan(ph["start"]/60, ph["end"]/60, alpha=0.07, color=ph["color"])
        ax.axvline(ph["start"]/60, color=ph["color"], lw=0.7, ls="--", alpha=0.45)

def add_legend(ax):
    patches = [mpatches.Patch(color=ph["color"], label=f"P{ph['id']}: {ph['name']}")
               for ph in PHASES]
    ax.legend(handles=patches, fontsize=7, framealpha=0.3, ncol=3, loc="upper right")

# ── FIG 1: Cardio Stress + Oxygen Exchange + Health Score ────────────────────
fig, axes = plt.subplots(3,1,figsize=(14,10), sharex=True)
fig.patch.set_facecolor(DARK)
for ax in axes: ax.set_facecolor(PANEL)
fig.suptitle("Digital Twin – Core Derived Metrics (Heart | Lungs | Health)",
             fontsize=14, fontweight="bold", color="white", y=0.99)

ax = axes[0]
add_bands(ax)
if csi: ax.plot(time_min, csi, color="#FF6B6B", lw=1.8, label="Cardio Stress Index")
ax.axhline(45, color="#FFB703", ls="--", lw=0.9, alpha=0.7, label="WARNING threshold (45)")
ax.axhline(75, color="#FF4444", ls="--", lw=0.9, alpha=0.7, label="CRITICAL threshold (75)")
ax.set_ylabel("Cardio Stress Index (0-100)", color="white", fontsize=10)
ax.set_ylim(0, 105); ax.legend(fontsize=8, framealpha=0.3); ax.grid(axis="y", alpha=0.2)
ax.tick_params(colors="white")

ax = axes[1]
add_bands(ax)
if oee: ax.plot(time_min, oee, color="#06D6A0", lw=1.8, label="O2 Exchange Efficiency")
ax.axhline(80, color="#FFB703", ls="--", lw=0.9, alpha=0.7, label="WARNING threshold (80)")
ax.set_ylabel("O2 Exchange Efficiency (%)", color="white", fontsize=10)
ax.set_ylim(60, 102); ax.legend(fontsize=8, framealpha=0.3); ax.grid(axis="y", alpha=0.2)
ax.tick_params(colors="white")

ax = axes[2]
add_bands(ax)
if health: ax.plot(time_min, health, color="#00B4D8", lw=2.0, label="Overall Health Score")
if heart_h: ax.plot(time_min, heart_h, color="#FF6B6B", lw=1.0, alpha=0.55, label="Heart Health")
if lung_h:  ax.plot(time_min, lung_h,  color="#06D6A0", lw=1.0, alpha=0.55, label="Lung Health")
if o2_h:    ax.plot(time_min, o2_h,    color="#C77DFF", lw=1.0, alpha=0.55, label="O2 Health")
ax.axhline(70, color="#FFB703", ls="--", lw=0.9, alpha=0.7)
ax.set_ylabel("Health Score (0-100)", color="white", fontsize=10)
ax.set_xlabel("Mission Time (minutes)", color="white", fontsize=11)
ax.set_ylim(40, 105); ax.legend(fontsize=8, framealpha=0.3); ax.grid(axis="y", alpha=0.2)
ax.tick_params(colors="white")

plt.tight_layout()
out = PLOTS_DIR / "04_digital_twin_core.png"
plt.savefig(out, dpi=150, bbox_inches="tight"); plt.close()
print(f"[PLOT] Saved: {out.name}")

# ── FIG 2: Anomaly indicators (Pulse Pressure, Hypoxia, BV Factor) ───────────
fig, axes = plt.subplots(3,1,figsize=(14,9), sharex=True)
fig.patch.set_facecolor(DARK)
for ax in axes: ax.set_facecolor(PANEL)
fig.suptitle("Digital Twin – Secondary Indicators (Pulse Pressure | Hypoxia | Blood Volume)",
             fontsize=13, fontweight="bold", color="white", y=0.99)

ax = axes[0]
add_bands(ax)
if pp: ax.plot(time_min, pp, color="#FF9F1C", lw=1.5, label="Pulse Pressure (mmHg)")
ax.axhline(40, color="#FFB703", ls="--", lw=0.9, alpha=0.6, label="Normal lower bound")
ax.axhline(60, color="#FF6B6B", ls="--", lw=0.9, alpha=0.6, label="Elevated")
ax.set_ylabel("Pulse Pressure (mmHg)", color="white", fontsize=10)
ax.legend(fontsize=8, framealpha=0.3); ax.grid(axis="y", alpha=0.2); ax.tick_params(colors="white")

ax = axes[1]
add_bands(ax)
if hyp: ax.fill_between(time_min, 0, hyp, color="#FF4444", alpha=0.45, label="Hypoxia Index")
if hyp: ax.plot(time_min, hyp, color="#FF4444", lw=1.2)
ax.axhline(30, color="#FFB703", ls="--", lw=0.9, alpha=0.6, label="WARNING level")
ax.axhline(70, color="#FF0000", ls="--", lw=0.9, alpha=0.6, label="CRITICAL level")
ax.set_ylabel("Hypoxia Index (0-100)", color="white", fontsize=10)
ax.set_ylim(0, 105); ax.legend(fontsize=8, framealpha=0.3); ax.grid(axis="y", alpha=0.2)
ax.tick_params(colors="white")

ax = axes[2]
add_bands(ax)
if bvf: ax.plot(time_min, bvf, color="#2EC4B6", lw=1.5, label="Blood Volume Factor")
ax.axhline(1.0, color="white", ls="--", lw=0.8, alpha=0.4, label="Baseline (1.0)")
ax.set_ylabel("Blood Volume Factor", color="white", fontsize=10)
ax.set_xlabel("Mission Time (minutes)", color="white", fontsize=11)
ax.legend(fontsize=8, framealpha=0.3); ax.grid(axis="y", alpha=0.2); ax.tick_params(colors="white")

plt.tight_layout()
out = PLOTS_DIR / "05_digital_twin_indicators.png"
plt.savefig(out, dpi=150, bbox_inches="tight"); plt.close()
print(f"[PLOT] Saved: {out.name}")

# ── FIG 3: Phase-by-phase bar chart comparison ───────────────────────────────
import json
summary_path = RESULTS_DIR / "digital_twin_summary.json"
if summary_path.exists():
    with open(summary_path) as f:
        summary = json.load(f)
    phases   = summary["phases"]
    names    = [f"P{p['id']}\n{p['name'][:10]}" for p in phases]
    csi_vals = [p["avg_CardioStressIndex"]        for p in phases]
    oee_vals = [p["avg_OxygenExchangeEfficiency"]  for p in phases]
    ots_vals = [p["avg_OxygenTransportScore"]       for p in phases]
    hlt_vals = [p["avg_HealthScore"]                for p in phases]
    colors   = ["#00B4D8","#FF6B6B","#C77DFF","#888888","#06D6A0"]

    fig, axes = plt.subplots(1,4, figsize=(16,5))
    fig.patch.set_facecolor(DARK)
    for ax in axes: ax.set_facecolor(PANEL); ax.tick_params(colors="white")
    fig.suptitle("Digital Twin – Per-Phase Average Metrics",
                 fontsize=13, fontweight="bold", color="white", y=1.02)

    for ax, vals, title, ylbl, clr in [
        (axes[0], csi_vals,  "Cardio Stress Index",     "CSI (0-100)",   "#FF6B6B"),
        (axes[1], oee_vals,  "O2 Exchange Efficiency",  "OEE (%)",       "#06D6A0"),
        (axes[2], ots_vals,  "O2 Transport Score",      "OTS (%)",       "#00B4D8"),
        (axes[3], hlt_vals,  "Health Score",            "Score (0-100)", "#C77DFF"),
    ]:
        bars = ax.bar(names, vals, color=colors, edgecolor="none", width=0.6)
        ax.set_title(title, color="white", fontsize=9, pad=8)
        ax.set_ylabel(ylbl, color="white", fontsize=8)
        ax.set_ylim(0, 110)
        ax.grid(axis="y", alpha=0.15)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x()+bar.get_width()/2, v+2, f"{v:.0f}",
                    ha="center", va="bottom", color="white", fontsize=8, fontweight="bold")
        for sp in ax.spines.values(): sp.set_edgecolor("#333355")
        ax.set_xticklabels(names, fontsize=7)
        ax.tick_params(axis='x', colors='white')

    plt.tight_layout()
    out = PLOTS_DIR / "06_digital_twin_phase_bars.png"
    plt.savefig(out, dpi=150, bbox_inches="tight"); plt.close()
    print(f"[PLOT] Saved: {out.name}")

print(f"\n[DONE] All digital twin plots saved to: {PLOTS_DIR}")
