"""
Generate project summary PNG for fixed-income-monitor.
"""
import sys, os
sys.path.insert(0, "/home/user/2nd-ML100Days/fixed-income-monitor")
os.chdir("/home/user/2nd-ML100Days/fixed-income-monitor")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd

# ── Load inventory ────────────────────────────────────────────────────────────
inv = pd.read_csv("field_inventory.csv")
reb = pd.read_csv("rebuild_feasibility.csv")

# ── Colour palette ────────────────────────────────────────────────────────────
BG      = "#0F1923"
PANEL   = "#172130"
BORDER  = "#1E3048"
ACCENT  = "#3A9AD9"
GREEN   = "#2ECC71"
AMBER   = "#F39C12"
RED     = "#E74C3C"
GREY    = "#95A5A6"
WHITE   = "#ECF0F1"
LIGHT   = "#BDC3C7"
GRADE_COLORS = {"A": GREEN, "B": AMBER, "C": "#E67E22", "D": RED}

# ── Figure layout ─────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(22, 14), facecolor=BG)
fig.subplots_adjust(left=0.03, right=0.97, top=0.93, bottom=0.04, hspace=0.45, wspace=0.35)

gs = gridspec.GridSpec(3, 4, figure=fig,
                       height_ratios=[0.35, 0.35, 0.30],
                       hspace=0.50, wspace=0.38)

# ── Title ─────────────────────────────────────────────────────────────────────
fig.text(0.5, 0.965, "Fixed Income Market Monitor — Non-Bloomberg Replacement",
         ha="center", va="center", fontsize=17, fontweight="bold",
         color=WHITE, fontfamily="monospace")
fig.text(0.5, 0.945, "Project Summary  |  45 Tests ✓  |  2026-04-29",
         ha="center", va="center", fontsize=10, color=ACCENT)

# helper: style axes
def style_ax(ax, title=""):
    ax.set_facecolor(PANEL)
    for spine in ax.spines.values():
        spine.set_edgecolor(BORDER)
    ax.tick_params(colors=LIGHT, labelsize=8)
    if title:
        ax.set_title(title, color=ACCENT, fontsize=9, fontweight="bold", pad=6)

# ── 1. Grade donut (top-left) ─────────────────────────────────────────────────
ax1 = fig.add_subplot(gs[0, 0])
style_ax(ax1, "Rebuild Feasibility Grade")

grade_counts = reb["rebuild_grade"].value_counts().reindex(["A","B","C","D"], fill_value=0)
colors_donut = [GRADE_COLORS[g] for g in grade_counts.index]
wedges, texts, autotexts = ax1.pie(
    grade_counts.values,
    labels=grade_counts.index,
    colors=colors_donut,
    autopct="%d",
    startangle=90,
    wedgeprops=dict(width=0.55, edgecolor=BG, linewidth=1.5),
    textprops=dict(color=WHITE, fontsize=9, fontweight="bold"),
    pctdistance=0.72,
)
for at in autotexts:
    at.set_color(BG); at.set_fontsize(8); at.set_fontweight("bold")

legend_labels = [f"  {g}  {n} fields" for g, n in grade_counts.items()]
ax1.legend(
    handles=[mpatches.Patch(color=c) for c in colors_donut],
    labels=legend_labels,
    loc="lower center", bbox_to_anchor=(0.5, -0.22),
    ncol=2, frameon=False, fontsize=7.5,
    labelcolor=LIGHT,
)

# ── 2. Asset class bar (top second) ──────────────────────────────────────────
ax2 = fig.add_subplot(gs[0, 1])
style_ax(ax2, "Fields by Asset Class")

ac_counts = inv["asset_class"].value_counts()
ac_colors = {"rates": ACCENT, "credit": "#9B59B6", "equity": GREEN,
             "fx": AMBER, "commodity": "#E67E22"}
bars = ax2.barh(ac_counts.index, ac_counts.values,
                color=[ac_colors.get(x, GREY) for x in ac_counts.index],
                height=0.55, edgecolor=BG, linewidth=0.5)
for bar, val in zip(bars, ac_counts.values):
    ax2.text(val + 0.3, bar.get_y() + bar.get_height()/2,
             str(val), va="center", ha="left", fontsize=8.5,
             color=WHITE, fontweight="bold")
ax2.set_xlim(0, ac_counts.max() * 1.3)
ax2.set_xlabel("# fields", color=LIGHT, fontsize=8)
ax2.tick_params(axis="y", labelsize=8.5, colors=WHITE)

# ── 3. Source coverage table (top third+fourth, spanning 2 cols) ─────────────
ax3 = fig.add_subplot(gs[0, 2:])
style_ax(ax3, "Data Sources — Coverage & Risk")
ax3.axis("off")

src_data = [
    ["FRED",          "US Tsy / TIPS / BEI\nICE BofA credit (IG/HY/BBB/BB/B/CCC)", "34", "Low",  "Free API key"],
    ["TREASURY.GOV",  "US yield curve 1M–30Y\n(official XML)",                      "11", "Low",  "No auth"],
    ["YAHOO FINANCE", "Equity (16) / FX (12)\nCommodities (7)",                      "35", "Med",  "Unofficial API"],
    ["ECB SDMX",      "Euribor / ESTR\nECB yield curve",                             "12", "Low",  "No auth"],
    ["CBOE",          "VIX daily history",                                            " 1", "Low",  "Public CSV"],
]

col_widths = [0.15, 0.35, 0.07, 0.15, 0.22]
col_labels = ["Source", "Coverage", "Fields", "Legal Risk", "Auth"]
col_x = np.cumsum([0] + col_widths[:-1])

# Header
for xi, label, w in zip(col_x, col_labels, col_widths):
    ax3.text(xi + w/2, 0.95, label, transform=ax3.transAxes,
             ha="center", va="top", fontsize=8.5, fontweight="bold",
             color=ACCENT)

# Separator line
ax3.axhline(y=0.88, xmin=0.0, xmax=1.0, color=BORDER, linewidth=0.8)

# Rows
row_y = [0.80, 0.63, 0.46, 0.29, 0.12]
row_colors = [PANEL, "#1A2A3A", PANEL, "#1A2A3A", PANEL]

for i, (row, ry) in enumerate(zip(src_data, row_y)):
    # Row background
    rect = FancyBboxPatch((0, ry - 0.10), 1.0, 0.16,
                           boxstyle="round,pad=0.01", linewidth=0,
                           facecolor=row_colors[i], transform=ax3.transAxes, zorder=0)
    ax3.add_patch(rect)
    for xi, cell, w in zip(col_x, row, col_widths):
        color = WHITE if i % 2 == 0 else LIGHT
        if col_labels[col_x.tolist().index(xi)] == "Fields":
            color = ACCENT
        ax3.text(xi + w/2, ry, cell, transform=ax3.transAxes,
                 ha="center", va="center", fontsize=7.8, color=color,
                 multialignment="center", linespacing=1.3)

# ── 4. Pipeline diagram (middle-left, spanning 2 cols) ───────────────────────
ax4 = fig.add_subplot(gs[1, :2])
style_ax(ax4, "Pipeline Architecture")
ax4.set_xlim(0, 10); ax4.set_ylim(0, 3); ax4.axis("off")

boxes = [
    (0.5,  1.5, "COLLECTORS\nFRED · Treasury.gov\nYahoo · ECB · CBOE", ACCENT),
    (3.2,  1.5, "SCHEMA\nMarketDataPoint\n(Pydantic)",                  "#9B59B6"),
    (5.5,  1.5, "STORAGE\nParquet / CSV\nper field",                    GREEN),
    (7.8,  1.5, "CALCULATOR\nD1·WTD·MTD\nYTD·pct_rank",               AMBER),
]
report_box = (9.3, 1.5, "REPORT\nCSV + XLSX\n(openpyxl)", "#E67E22")
all_boxes = boxes + [report_box]

for bx, by, label, color in all_boxes:
    rect = FancyBboxPatch((bx - 0.95, by - 0.75), 1.90, 1.50,
                           boxstyle="round,pad=0.08", linewidth=1.5,
                           edgecolor=color, facecolor=PANEL, zorder=2)
    ax4.add_patch(rect)
    ax4.text(bx, by + 0.08, label, ha="center", va="center",
             fontsize=7.5, color=WHITE, fontweight="bold", linespacing=1.4,
             zorder=3, multialignment="center")

# Arrows
arrow_kw = dict(arrowstyle="->", color=BORDER, lw=2.0,
                connectionstyle="arc3,rad=0.0")
arrow_xs = [(1.45, 2.25), (4.15, 4.55), (6.45, 6.85), (8.75, 8.35)]
for x1, x2 in arrow_xs:
    ax4.annotate("", xy=(x2, 1.5), xytext=(x1, 1.5),
                 arrowprops=arrow_kw)

# Label below: "All perf changes computed from history — never from source"
ax4.text(4.7, 0.35,
         "⚡ All D1/WTD/MTD/YTD computed from local history — never from source website",
         ha="center", va="center", fontsize=7.5, color=AMBER,
         style="italic")

# ── 5. Sample snapshot table (middle-right, spanning 2 cols) ─────────────────
ax5 = fig.add_subplot(gs[1, 2:])
style_ax(ax5, "Sample Output — Snapshot (illustrative)")
ax5.axis("off")

snap_data = {
    "Field":        ["US_TREASURY_10Y","US_HY_OAS","EU_EURIBOR_3M",
                     "EQ_SP500",       "CMD_GOLD",  "VIX",
                     "US_TIPS_10Y",    "FX_USDJPY"],
    "Value":        ["4.32%","317 bp","2.54%","5,204","3,350","17.7","2.15%","142.5"],
    "Unit":         ["pct","bps","pct","idx","USD","idx","pct","FX"],
    "D1":           ["+0.03","+8","-0.01","+0.8%","+0.4%","-0.9","+0.02","-0.3"],
    "YTD":          ["+0.32","+85","-0.41","+4.2%","+15%","+2.1","+0.25","+5.8"],
    "1Y Pct":       ["72%","68%","31%","61%","88%","22%","65%","78%"],
    "Grade":        ["A","A","A","A","A","A","A","A"],
    "Source":       ["FRED","FRED","ECB","Yahoo","Yahoo","CBOE","FRED","Yahoo"],
}
df_snap = pd.DataFrame(snap_data)

col_w2  = [0.19, 0.09, 0.07, 0.08, 0.08, 0.09, 0.08, 0.10]
col_x2  = np.cumsum([0.0] + col_w2[:-1])
headers2 = list(df_snap.columns)

for xi, label, w in zip(col_x2, headers2, col_w2):
    ax5.text(xi + w/2, 0.97, label, transform=ax5.transAxes,
             ha="center", va="top", fontsize=8, fontweight="bold", color=ACCENT)

ax5.axhline(y=0.90, xmin=0, xmax=1, color=BORDER, linewidth=0.8)

step = 0.85 / len(df_snap)
for i, row in df_snap.iterrows():
    ry = 0.88 - i * step
    bg = PANEL if i % 2 == 0 else "#1A2A3A"
    rect = FancyBboxPatch((0, ry - step * 0.45), 1.0, step * 0.90,
                           boxstyle="round,pad=0.005", linewidth=0,
                           facecolor=bg, transform=ax5.transAxes, zorder=0)
    ax5.add_patch(rect)
    for xi, val, w, col in zip(col_x2, row.values, col_w2, headers2):
        if col == "D1":
            color = GREEN if val.startswith("+") else RED
        elif col == "YTD":
            color = GREEN if val.startswith("+") else RED
        elif col == "Grade":
            color = GRADE_COLORS.get(val, WHITE)
        elif col == "Source":
            color = ACCENT
        elif col == "Field":
            color = WHITE
        else:
            color = LIGHT
        ax5.text(xi + w/2, ry, str(val), transform=ax5.transAxes,
                 ha="center", va="center", fontsize=7.5, color=color)

# ── 6. Test summary (bottom-left) ────────────────────────────────────────────
ax6 = fig.add_subplot(gs[2, 0])
style_ax(ax6, "Test Coverage (45 tests)")
ax6.axis("off")

test_rows = [
    ("test_fred.py",       8, GREEN),
    ("test_treasury.py",   8, GREEN),
    ("test_yahoo.py",      8, GREEN),
    ("test_ecb.py",        7, GREEN),
    ("test_cboe.py",       6, GREEN),
    ("test_calculator.py", 8, GREEN),
]
total_tests = sum(n for _, n, _ in test_rows)

y0 = 0.88
for fname, n, color in test_rows:
    ax6.text(0.05, y0, f"✓  {fname}", transform=ax6.transAxes,
             ha="left", va="center", fontsize=8.0, color=LIGHT)
    ax6.text(0.88, y0, f"{n}", transform=ax6.transAxes,
             ha="right", va="center", fontsize=8.0, color=color, fontweight="bold")
    y0 -= 0.135

ax6.axhline(y=0.07, xmin=0.05, xmax=0.95, color=BORDER, lw=0.8)
ax6.text(0.5, 0.02, f"Total: {total_tests} passed  |  0 failed  |  offline only",
         transform=ax6.transAxes, ha="center", va="bottom",
         fontsize=8.5, color=GREEN, fontweight="bold")

# ── 7. Key design choices (bottom-middle) ────────────────────────────────────
ax7 = fig.add_subplot(gs[2, 1])
style_ax(ax7, "Key Design Decisions")
ax7.axis("off")

decisions = [
    "Schema: Pydantic v2 — single contract for all layers",
    "Storage: Parquet per field (CSV fallback w/o pyarrow)",
    "D1/WTD/MTD/YTD: all from stored history, never source",
    "rates/credit → absolute Δ;  equity/FX/CMD → %return",
    "robots.txt checked before every collector runs",
    "tenacity retry (exp. backoff) on all HTTP requests",
    "D-grade fields (JPM EMBI/CEMBI): excluded, documented",
]
y0 = 0.90
for d in decisions:
    ax7.text(0.04, y0, f"▸  {d}", transform=ax7.transAxes,
             ha="left", va="center", fontsize=7.5, color=LIGHT,
             wrap=True)
    y0 -= 0.127

# ── 8. Cannot-rebuild note (bottom right, spanning 2 cols) ───────────────────
ax8 = fig.add_subplot(gs[2, 2:])
style_ax(ax8, "Grade D — Cannot Rebuild (Proprietary)")
ax8.axis("off")

d_items = [
    ("JPM EMBI Global Spread",   "JPEIGLBL Index",  "Sovereign EM USD bond spread",
     "ICE BofA EM (Grade B) — different universe"),
    ("JPM CEMBI Broad IG OAS",   "JBCDGIG Index",   "EM corporate bond IG spread",
     "ICE BofA EM IG OAS (Grade B) — partial proxy"),
    ("JPM CEMBI Broad HY OAS",   "JBCDGHY Index",   "EM corporate bond HY spread",
     "ICE BofA EM HY OAS (Grade B) — partial proxy"),
]

col_w3  = [0.23, 0.17, 0.25, 0.32]
col_x3  = np.cumsum([0.0] + col_w3[:-1])
headers3 = ["Proprietary Field", "Bloomberg ID", "Definition", "Best Free Proxy"]

for xi, label, w in zip(col_x3, headers3, col_w3):
    ax8.text(xi + w/2, 0.96, label, transform=ax8.transAxes,
             ha="center", va="top", fontsize=8, fontweight="bold", color=RED)

ax8.axhline(y=0.88, xmin=0, xmax=1, color=BORDER, lw=0.8)

for i, row in enumerate(d_items):
    ry = 0.76 - i * 0.24
    for xi, cell, w, col in zip(col_x3, row, col_w3, headers3):
        color = RED if col == "Bloomberg ID" else (AMBER if col == "Best Free Proxy" else LIGHT)
        ax8.text(xi + w/2, ry, cell, transform=ax8.transAxes,
                 ha="center", va="center", fontsize=7.5, color=color,
                 multialignment="center", linespacing=1.3)

ax8.text(0.5, 0.04,
         "⚠  These indices require Bloomberg Terminal or JPMorgan commercial license",
         transform=ax8.transAxes, ha="center", va="bottom",
         fontsize=7.8, color=RED, style="italic")

# ── Save ──────────────────────────────────────────────────────────────────────
out_path = "/home/user/2nd-ML100Days/fixed-income-monitor/project_summary.png"
fig.savefig(out_path, dpi=160, bbox_inches="tight", facecolor=BG)
print(f"Saved: {out_path}")
plt.close(fig)
