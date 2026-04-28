"""
Investment Bank Style Excel Chart Template
外資銀行風格 Excel 圖表模板

Color Palette (IB Standard):
  Primary Navy  : #1F3864
  Mid Blue      : #2E75B6
  Light Blue    : #9DC3E6
  Dark Grey     : #404040
  Mid Grey      : #808080
  Light Grey    : #D9D9D9
  Accent Red    : #C00000
  Accent Green  : #70AD47
  Accent Orange : #ED7D31
  White         : #FFFFFF
"""

import xlsxwriter
import os

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "IB_Chart_Template.xlsx")

# ── Palette ──────────────────────────────────────────────────────────────────
NAVY    = "#1F3864"
BLUE1   = "#2E75B6"
BLUE2   = "#5B9BD5"
BLUE3   = "#9DC3E6"
BLUE4   = "#BDD7EE"
DGREY   = "#404040"
MGREY   = "#808080"
LGREY   = "#D9D9D9"
RED     = "#C00000"
GREEN   = "#70AD47"
ORANGE  = "#ED7D31"
WHITE   = "#FFFFFF"
YELLOW  = "#FFD700"

# Series colours in preferred order
SERIES_COLORS = [NAVY, BLUE1, BLUE2, BLUE3, ORANGE, GREEN, RED]

# ── Shared format helpers ─────────────────────────────────────────────────────

def add_formats(wb):
    """Pre-build all reusable cell formats."""
    base = dict(font_name="Calibri", font_size=10, font_color=DGREY)

    f = {}
    f["title"] = wb.add_format({
        **base, "font_size": 14, "bold": True,
        "font_color": NAVY, "bottom": 2, "bottom_color": NAVY,
    })
    f["section"] = wb.add_format({
        **base, "font_size": 11, "bold": True,
        "font_color": WHITE, "bg_color": NAVY,
        "align": "center", "valign": "vcenter",
    })
    f["header"] = wb.add_format({
        **base, "bold": True, "font_color": WHITE,
        "bg_color": BLUE1, "align": "center", "valign": "vcenter",
        "border": 1, "border_color": WHITE,
    })
    f["data"] = wb.add_format({
        **base, "num_format": "#,##0", "border": 1, "border_color": LGREY,
    })
    f["data_pct"] = wb.add_format({
        **base, "num_format": "0.0%", "border": 1, "border_color": LGREY,
    })
    f["data_dec"] = wb.add_format({
        **base, "num_format": "#,##0.0", "border": 1, "border_color": LGREY,
    })
    f["data_stripe"] = wb.add_format({
        **base, "num_format": "#,##0", "border": 1, "border_color": LGREY,
        "bg_color": "#EBF3FB",
    })
    f["label"] = wb.add_format({
        **base, "bold": True, "border": 1, "border_color": LGREY,
    })
    f["label_stripe"] = wb.add_format({
        **base, "bold": True, "border": 1, "border_color": LGREY,
        "bg_color": "#EBF3FB",
    })
    f["total"] = wb.add_format({
        **base, "bold": True, "num_format": "#,##0",
        "bg_color": NAVY, "font_color": WHITE,
        "border": 1, "border_color": WHITE,
    })
    f["note"] = wb.add_format({
        **base, "font_size": 8, "italic": True, "font_color": MGREY,
    })
    return f


def write_table(ws, row, col, headers, data, fmts, stripe=True):
    """Write a styled data table; returns (last_row, last_col)."""
    for c, h in enumerate(headers):
        ws.write(row, col + c, h, fmts["header"])
    for r, rowdata in enumerate(data):
        is_stripe = stripe and (r % 2 == 1)
        for c, val in enumerate(rowdata):
            if c == 0:
                fmt = fmts["label_stripe"] if is_stripe else fmts["label"]
            elif isinstance(val, float) and val < 5:
                fmt = fmts["data_dec"] if is_stripe else fmts["data_dec"]
            else:
                fmt = fmts["data_stripe"] if is_stripe else fmts["data"]
            ws.write(row + 1 + r, col + c, val, fmt)
    return row + len(data), col + len(headers) - 1


# ── Chart style helper ────────────────────────────────────────────────────────

def style_chart(chart, title="", x_title="", y_title="", legend=True):
    """Apply IB-standard styling to any chart object."""
    chart.set_title({
        "name": title,
        "name_font": {
            "name": "Calibri", "size": 12, "bold": True, "color": NAVY,
        },
    })
    chart.set_x_axis({
        "name": x_title,
        "name_font": {"name": "Calibri", "size": 9, "color": DGREY},
        "num_font":  {"name": "Calibri", "size": 9, "color": DGREY},
        "line": {"color": LGREY},
        "major_gridlines": {"visible": False},
    })
    chart.set_y_axis({
        "name": y_title,
        "name_font": {"name": "Calibri", "size": 9, "color": DGREY},
        "num_font":  {"name": "Calibri", "size": 9, "color": DGREY},
        "line": {"color": LGREY, "none": True},
        "major_gridlines": {
            "visible": True,
            "line": {"color": LGREY, "dash_type": "dash", "width": 0.75},
        },
    })
    chart.set_plotarea({
        "border": {"none": True},
        "fill":   {"color": WHITE},
    })
    chart.set_chartarea({
        "border": {"none": True},
        "fill":   {"color": WHITE},
    })
    if legend:
        chart.set_legend({
            "position": "bottom",
            "font": {"name": "Calibri", "size": 9, "color": DGREY},
        })
    else:
        chart.set_legend({"none": True})
    chart.set_size({"width": 480, "height": 300})


# ══════════════════════════════════════════════════════════════════════════════
# Sheet builders
# ══════════════════════════════════════════════════════════════════════════════

def build_column_chart(wb, fmts):
    """Sheet 1 – Clustered Column Chart (Revenue by Segment)"""
    ws = wb.add_worksheet("1. Column Chart")
    ws.set_column("A:A", 14)
    ws.set_column("B:F", 12)
    ws.hide_gridlines(2)

    ws.write("A1", "Revenue by Business Segment (USD mn)", fmts["title"])
    ws.write("A2", "Source: Company Financials | IB Chart Template", fmts["note"])

    years   = ["2020", "2021", "2022", "2023", "2024E"]
    segs    = ["Equities", "FICC", "Investment Banking", "Asset Mgmt"]
    data    = {
        "Equities":          [2800, 3100, 3450, 3200, 3600],
        "FICC":              [3500, 3800, 4200, 3900, 4100],
        "Investment Banking":[1200, 1500, 1800, 1400, 1700],
        "Asset Mgmt":        [900,  1050, 1150, 1100, 1250],
    }

    headers = ["Segment"] + years
    rows    = [[s] + data[s] for s in segs]
    write_table(ws, 3, 0, headers, rows, fmts)

    chart = wb.add_chart({"type": "column"})
    for i, seg in enumerate(segs):
        chart.add_series({
            "name":       seg,
            "categories": ["1. Column Chart", 4, 1, 4 + len(segs) - 1, 1],
            "values":     ["1. Column Chart", 4 + i, 2, 4 + i, len(years) + 1],
            "fill":       {"color": SERIES_COLORS[i]},
            "border":     {"none": True},
            "gap":        150,
        })
    # Fix categories to use years row
    chart = wb.add_chart({"type": "column"})
    for i, seg in enumerate(segs):
        chart.add_series({
            "name":       seg,
            "categories": ["1. Column Chart", 4, 1, 4, len(years)],
            "values":     ["1. Column Chart", 5 + i, 1, 5 + i, len(years)],
            "fill":       {"color": SERIES_COLORS[i]},
            "border":     {"none": True},
        })
    style_chart(chart, "Revenue by Business Segment", "", "USD mn")
    ws.insert_chart("A11", chart, {"x_offset": 5, "y_offset": 5})


def build_line_chart(wb, fmts):
    """Sheet 2 – Line Chart (Stock Price vs Index)"""
    ws = wb.add_worksheet("2. Line Chart")
    ws.set_column("A:A", 12)
    ws.set_column("B:D", 12)
    ws.hide_gridlines(2)

    ws.write("A1", "Stock Price vs Benchmark Index (Indexed = 100)", fmts["title"])
    ws.write("A2", "Source: Bloomberg | IB Chart Template", fmts["note"])

    quarters = ["Q1'22","Q2'22","Q3'22","Q4'22",
                "Q1'23","Q2'23","Q3'23","Q4'23",
                "Q1'24","Q2'24","Q3'24","Q4'24"]
    stock  = [100,108,103,115,120,118,130,138,142,150,148,160]
    bench  = [100,105,101,110,113,112,120,125,128,133,130,140]
    peers  = [100,102, 98,106,109,108,115,119,122,126,123,132]

    headers = ["Quarter", "Company", "Benchmark", "Peer Avg"]
    rows    = [[quarters[i], stock[i], bench[i], peers[i]] for i in range(len(quarters))]
    write_table(ws, 3, 0, headers, rows, fmts)

    chart = wb.add_chart({"type": "line"})
    series_cfg = [
        ("Company",   NAVY,  2.25, "solid"),
        ("Benchmark", BLUE2, 1.5,  "dash"),
        ("Peer Avg",  MGREY, 1.5,  "dash"),
    ]
    for idx, (name, color, width, dash) in enumerate(series_cfg):
        chart.add_series({
            "name":       name,
            "categories": ["2. Line Chart", 4, 0, 4 + len(quarters) - 1, 0],
            "values":     ["2. Line Chart", 4, 1 + idx, 4 + len(quarters) - 1, 1 + idx],
            "line":       {"color": color, "width": width, "dash_type": dash},
            "marker":     {"type": "none"},
        })
    style_chart(chart, "Relative Stock Performance (Indexed)", "", "Index (100 = Q1'22)")
    ws.insert_chart("A20", chart, {"x_offset": 5, "y_offset": 5})


def build_stacked_bar(wb, fmts):
    """Sheet 3 – 100% Stacked Bar (Revenue Mix)"""
    ws = wb.add_worksheet("3. Stacked Bar")
    ws.set_column("A:A", 14)
    ws.set_column("B:F", 10)
    ws.hide_gridlines(2)

    ws.write("A1", "Revenue Mix by Geography (%)", fmts["title"])
    ws.write("A2", "Source: Company Financials | IB Chart Template", fmts["note"])

    years = ["2020", "2021", "2022", "2023", "2024E"]
    geos  = ["Americas", "EMEA", "Asia-Pacific", "Other"]
    data  = {
        "Americas":    [0.42, 0.43, 0.44, 0.43, 0.45],
        "EMEA":        [0.31, 0.30, 0.29, 0.30, 0.28],
        "Asia-Pacific":[0.22, 0.23, 0.24, 0.24, 0.24],
        "Other":       [0.05, 0.04, 0.03, 0.03, 0.03],
    }

    headers = ["Geography"] + years
    rows    = [[g] + data[g] for g in geos]
    r_end, c_end = write_table(ws, 3, 0, headers, rows, fmts)

    chart = wb.add_chart({"type": "bar", "subtype": "percent_stacked"})
    for i, geo in enumerate(geos):
        chart.add_series({
            "name":       geo,
            "categories": ["3. Stacked Bar", 4, 1, 4, len(years)],
            "values":     ["3. Stacked Bar", 5 + i, 1, 5 + i, len(years)],
            "fill":       {"color": SERIES_COLORS[i]},
            "border":     {"color": WHITE, "width": 0.5},
        })
    style_chart(chart, "Revenue Mix by Geography", "", "% of Total")
    ws.insert_chart("A11", chart, {"x_offset": 5, "y_offset": 5})


def build_waterfall(wb, fmts):
    """Sheet 4 – Waterfall / Bridge Chart (EBITDA Bridge)"""
    ws = wb.add_worksheet("4. Waterfall")
    ws.set_column("A:A", 20)
    ws.set_column("B:E", 11)
    ws.hide_gridlines(2)

    ws.write("A1", "EBITDA Bridge: 2023A → 2024E (USD mn)", fmts["title"])
    ws.write("A2", "Source: Management Estimates | IB Chart Template", fmts["note"])

    items  = ["2023A EBITDA", "Volume", "Price/Mix", "Cost Savings",
              "FX Impact", "One-offs", "2024E EBITDA"]
    values = [1850, 120, 85, 60, -45, -30, 2040]

    # Compute invisible base bars for stacking effect
    base   = []
    running = 0
    for i, (item, val) in enumerate(zip(items, values)):
        if i == 0 or i == len(items) - 1:
            base.append(0)
            running = val
        else:
            if val >= 0:
                base.append(running)
                running += val
            else:
                base.append(running + val)
                running += val

    headers = ["Item", "Base (hidden)", "Positive", "Negative", "Total Bar"]
    rows = []
    for i, (item, val) in enumerate(zip(items, values)):
        if i == 0 or i == len(items) - 1:
            rows.append([item, 0, 0, 0, values[i]])
        elif val >= 0:
            rows.append([item, base[i], val, 0, 0])
        else:
            rows.append([item, base[i], 0, abs(val), 0])

    for r_idx, row in enumerate(rows):
        is_stripe = r_idx % 2 == 1
        ws.write(4 + r_idx, 0, row[0], fmts["label_stripe"] if is_stripe else fmts["label"])
        for c_idx, val in enumerate(row[1:], 1):
            ws.write(4 + r_idx, c_idx, val, fmts["data_stripe"] if is_stripe else fmts["data"])

    ws.write(3, 0, headers[0], fmts["header"])
    for c, h in enumerate(headers[1:], 1):
        ws.write(3, c, h, fmts["header"])

    # Stacked column: invisible base + positive + negative + total
    chart = wb.add_chart({"type": "column", "subtype": "stacked"})
    n = len(items)

    # Base (invisible)
    chart.add_series({
        "name":   "Base",
        "categories": ["4. Waterfall", 4, 0, 4 + n - 1, 0],
        "values":     ["4. Waterfall", 4, 1, 4 + n - 1, 1],
        "fill":   {"none": True},
        "border": {"none": True},
    })
    # Positive
    chart.add_series({
        "name":   "Increase",
        "categories": ["4. Waterfall", 4, 0, 4 + n - 1, 0],
        "values":     ["4. Waterfall", 4, 2, 4 + n - 1, 2],
        "fill":   {"color": GREEN},
        "border": {"none": True},
    })
    # Negative
    chart.add_series({
        "name":   "Decrease",
        "categories": ["4. Waterfall", 4, 0, 4 + n - 1, 0],
        "values":     ["4. Waterfall", 4, 3, 4 + n - 1, 3],
        "fill":   {"color": RED},
        "border": {"none": True},
    })
    # Total bars
    chart.add_series({
        "name":   "Total",
        "categories": ["4. Waterfall", 4, 0, 4 + n - 1, 0],
        "values":     ["4. Waterfall", 4, 4, 4 + n - 1, 4],
        "fill":   {"color": NAVY},
        "border": {"none": True},
    })
    style_chart(chart, "EBITDA Bridge 2023A → 2024E", "", "USD mn")
    chart.set_size({"width": 560, "height": 320})
    ws.insert_chart("A14", chart, {"x_offset": 5, "y_offset": 5})


def build_combo_chart(wb, fmts):
    """Sheet 5 – Combo Chart (Revenue Bar + Margin Line)"""
    ws = wb.add_worksheet("5. Combo Chart")
    ws.set_column("A:A", 10)
    ws.set_column("B:F", 12)
    ws.hide_gridlines(2)

    ws.write("A1", "Revenue & Net Profit Margin (USD mn / %)", fmts["title"])
    ws.write("A2", "Source: Company Financials | IB Chart Template", fmts["note"])

    years   = ["2020", "2021", "2022", "2023", "2024E"]
    revenue = [8400, 9450, 10600, 9800, 11200]
    margin  = [0.182, 0.196, 0.211, 0.193, 0.218]

    headers = ["Year", "Revenue", "Net Margin"]
    rows    = [[years[i], revenue[i], margin[i]] for i in range(len(years))]
    for c, h in enumerate(headers):
        ws.write(3, c, h, fmts["header"])
    for r, row in enumerate(rows):
        is_s = r % 2 == 1
        ws.write(4 + r, 0, row[0], fmts["label_stripe"] if is_s else fmts["label"])
        ws.write(4 + r, 1, row[1], fmts["data_stripe"] if is_s else fmts["data"])
        ws.write(4 + r, 2, row[2], fmts["data_pct"])

    # Column chart for revenue
    bar = wb.add_chart({"type": "column"})
    bar.add_series({
        "name":       "Revenue",
        "categories": ["5. Combo Chart", 4, 0, 4 + len(years) - 1, 0],
        "values":     ["5. Combo Chart", 4, 1, 4 + len(years) - 1, 1],
        "fill":       {"color": BLUE1},
        "border":     {"none": True},
        "y2_axis":    False,
    })

    # Line chart for margin
    line = wb.add_chart({"type": "line"})
    line.add_series({
        "name":       "Net Margin",
        "categories": ["5. Combo Chart", 4, 0, 4 + len(years) - 1, 0],
        "values":     ["5. Combo Chart", 4, 2, 4 + len(years) - 1, 2],
        "line":       {"color": RED, "width": 2.25},
        "marker":     {"type": "circle", "size": 6,
                       "fill": {"color": RED}, "border": {"color": WHITE}},
        "y2_axis":    True,
    })
    bar.combine(line)

    bar.set_title({
        "name": "Revenue & Net Profit Margin",
        "name_font": {"name": "Calibri", "size": 12, "bold": True, "color": NAVY},
    })
    bar.set_x_axis({
        "name_font": {"name": "Calibri", "size": 9, "color": DGREY},
        "num_font":  {"name": "Calibri", "size": 9, "color": DGREY},
        "line":      {"color": LGREY},
        "major_gridlines": {"visible": False},
    })
    bar.set_y_axis({
        "name": "Revenue (USD mn)",
        "name_font": {"name": "Calibri", "size": 9, "color": DGREY},
        "num_font":  {"name": "Calibri", "size": 9, "color": DGREY},
        "line":      {"none": True},
        "major_gridlines": {
            "visible": True,
            "line": {"color": LGREY, "dash_type": "dash", "width": 0.75},
        },
    })
    bar.set_y2_axis({
        "name": "Net Margin (%)",
        "name_font": {"name": "Calibri", "size": 9, "color": RED},
        "num_font":  {"name": "Calibri", "size": 9, "color": DGREY},
        "num_format": "0%",
        "line": {"none": True},
    })
    bar.set_plotarea({"border": {"none": True}, "fill": {"color": WHITE}})
    bar.set_chartarea({"border": {"none": True}, "fill": {"color": WHITE}})
    bar.set_legend({
        "position": "bottom",
        "font": {"name": "Calibri", "size": 9, "color": DGREY},
    })
    bar.set_size({"width": 480, "height": 300})
    ws.insert_chart("A11", bar, {"x_offset": 5, "y_offset": 5})


def build_donut_chart(wb, fmts):
    """Sheet 6 – Donut Chart (Market Share)"""
    ws = wb.add_worksheet("6. Donut Chart")
    ws.set_column("A:A", 18)
    ws.set_column("B:C", 14)
    ws.hide_gridlines(2)

    ws.write("A1", "Global Market Share – Investment Banking Fees 2024E", fmts["title"])
    ws.write("A2", "Source: Dealogic | IB Chart Template", fmts["note"])

    players = ["Goldman Sachs", "JP Morgan", "Morgan Stanley",
               "Bank of America", "Citi", "Others"]
    shares  = [0.132, 0.128, 0.117, 0.108, 0.094, 0.421]
    colors  = [NAVY, BLUE1, BLUE2, BLUE3, ORANGE, LGREY]

    headers = ["Bank", "Market Share"]
    for c, h in enumerate(headers):
        ws.write(3, c, h, fmts["header"])
    for r, (p, s) in enumerate(zip(players, shares)):
        is_s = r % 2 == 1
        ws.write(4 + r, 0, p,  fmts["label_stripe"] if is_s else fmts["label"])
        ws.write(4 + r, 1, s,  fmts["data_pct"])

    chart = wb.add_chart({"type": "doughnut"})
    chart.add_series({
        "name":       "Market Share",
        "categories": ["6. Donut Chart", 4, 0, 4 + len(players) - 1, 0],
        "values":     ["6. Donut Chart", 4, 1, 4 + len(players) - 1, 1],
        "points": [{"fill": {"color": c}} for c in colors],
        "border": {"color": WHITE, "width": 1.5},
    })
    chart.set_title({
        "name": "IB Fee Market Share 2024E",
        "name_font": {"name": "Calibri", "size": 12, "bold": True, "color": NAVY},
    })
    chart.set_plotarea({"border": {"none": True}, "fill": {"color": WHITE}})
    chart.set_chartarea({"border": {"none": True}, "fill": {"color": WHITE}})
    chart.set_legend({
        "position": "right",
        "font": {"name": "Calibri", "size": 9, "color": DGREY},
    })
    chart.set_size({"width": 480, "height": 300})
    ws.insert_chart("D4", chart, {"x_offset": 5, "y_offset": 5})


def build_scatter_chart(wb, fmts):
    """Sheet 7 – Scatter / Bubble Chart (Valuation Comps)"""
    ws = wb.add_worksheet("7. Scatter Chart")
    ws.set_column("A:A", 18)
    ws.set_column("B:D", 12)
    ws.hide_gridlines(2)

    ws.write("A1", "Valuation Comps: EV/EBITDA vs. Revenue Growth (2024E)", fmts["title"])
    ws.write("A2", "Source: Bloomberg, FactSet | IB Chart Template", fmts["note"])

    comps = [
        ("Company A", 12.5, 0.08),
        ("Company B",  9.8, 0.05),
        ("Company C", 14.2, 0.12),
        ("Company D", 11.0, 0.07),
        ("Company E", 16.5, 0.15),
        ("Company F",  8.3, 0.03),
        ("Target Co", 13.0, 0.10),
    ]
    comp_colors = [BLUE2]*6 + [RED]  # Target highlighted

    headers = ["Company", "EV/EBITDA (x)", "Revenue Growth"]
    for c, h in enumerate(headers):
        ws.write(3, c, h, fmts["header"])
    for r, (name, ev, gr) in enumerate(comps):
        is_s = r % 2 == 1
        ws.write(4 + r, 0, name, fmts["label_stripe"] if is_s else fmts["label"])
        ws.write(4 + r, 1, ev,   fmts["data_dec"])
        ws.write(4 + r, 2, gr,   fmts["data_pct"])

    chart = wb.add_chart({"type": "scatter"})
    for i, (name, _, _) in enumerate(comps):
        chart.add_series({
            "name":       name,
            "categories": ["7. Scatter Chart", 4 + i, 2, 4 + i, 2],
            "values":     ["7. Scatter Chart", 4 + i, 1, 4 + i, 1],
            "marker": {
                "type": "circle", "size": 8 if name == "Target Co" else 6,
                "fill": {"color": comp_colors[i]},
                "border": {"color": WHITE},
            },
            "line": {"none": True},
        })
    style_chart(chart, "Valuation Comps: EV/EBITDA vs Rev. Growth",
                "Revenue Growth (%)", "EV/EBITDA (x)")
    chart.set_size({"width": 480, "height": 320})
    ws.insert_chart("A14", chart, {"x_offset": 5, "y_offset": 5})


def build_area_chart(wb, fmts):
    """Sheet 8 – Stacked Area Chart (AUM over time)"""
    ws = wb.add_worksheet("8. Area Chart")
    ws.set_column("A:A", 12)
    ws.set_column("B:F", 12)
    ws.hide_gridlines(2)

    ws.write("A1", "Assets Under Management by Asset Class (USD bn)", fmts["title"])
    ws.write("A2", "Source: Company Filings | IB Chart Template", fmts["note"])

    years   = ["2019", "2020", "2021", "2022", "2023", "2024E"]
    classes = ["Equities", "Fixed Income", "Alternatives", "Cash & Other"]
    data    = {
        "Equities":      [850, 780, 1020, 890,  980, 1100],
        "Fixed Income":  [620, 680,  710, 690,  730,  760],
        "Alternatives":  [280, 300,  340, 360,  400,  450],
        "Cash & Other":  [120, 140,  130, 150,  140,  150],
    }

    headers = ["Year"] + classes
    rows    = [[years[i]] + [data[c][i] for c in classes] for i in range(len(years))]
    write_table(ws, 3, 0, headers, rows, fmts)

    chart = wb.add_chart({"type": "area", "subtype": "stacked"})
    for i, cls in enumerate(classes):
        chart.add_series({
            "name":       cls,
            "categories": ["8. Area Chart", 4, 0, 4 + len(years) - 1, 0],
            "values":     ["8. Area Chart", 4, 1 + i, 4 + len(years) - 1, 1 + i],
            "fill":       {"color": SERIES_COLORS[i], "transparency": 20},
            "border":     {"none": True},
        })
    style_chart(chart, "AUM by Asset Class", "", "USD bn")
    ws.insert_chart("A12", chart, {"x_offset": 5, "y_offset": 5})


def build_cover(wb, fmts):
    """Cover sheet with palette reference."""
    ws = wb.add_worksheet("Cover")
    ws.set_column("A:A", 28)
    ws.set_column("B:H", 14)
    ws.hide_gridlines(2)
    ws.set_row(0, 40)

    ws.write("A1", "IB Chart Template — Professional Excel Charts", fmts["title"])
    ws.write("A2", "Inspired by Goldman Sachs / JP Morgan / Morgan Stanley charting standards", fmts["note"])

    ws.write("A4", "COLOUR PALETTE", fmts["section"])
    palette = [
        ("Primary Navy",  NAVY,  WHITE),
        ("Mid Blue",      BLUE1, WHITE),
        ("Blue 2",        BLUE2, WHITE),
        ("Blue 3",        BLUE3, DGREY),
        ("Blue 4",        BLUE4, DGREY),
        ("Dark Grey",     DGREY, WHITE),
        ("Mid Grey",      MGREY, WHITE),
        ("Light Grey",    LGREY, DGREY),
        ("Accent Red",    RED,   WHITE),
        ("Accent Green",  GREEN, WHITE),
        ("Accent Orange", ORANGE,WHITE),
    ]
    for r, (name, bg, fg) in enumerate(palette):
        fmt = wb.add_format({
            "font_name": "Calibri", "font_size": 10, "bold": True,
            "font_color": fg, "bg_color": bg,
            "align": "center", "valign": "vcenter",
            "border": 1, "border_color": WHITE,
        })
        ws.write(5 + r, 0, f"{name}  {bg}", fmt)
        ws.write(5 + r, 1, bg, fmt)

    ws.write("A18", "CHART INDEX", fmts["section"])
    index = [
        ("1. Column Chart",  "Clustered Column — Revenue by Business Segment"),
        ("2. Line Chart",    "Multi-line — Relative Stock Performance"),
        ("3. Stacked Bar",   "100% Stacked Bar — Revenue Mix by Geography"),
        ("4. Waterfall",     "Bridge / Waterfall — EBITDA Bridge"),
        ("5. Combo Chart",   "Column + Line — Revenue & Net Profit Margin"),
        ("6. Donut Chart",   "Doughnut — Market Share"),
        ("7. Scatter Chart", "Scatter — Valuation Comps (EV/EBITDA vs Growth)"),
        ("8. Area Chart",    "Stacked Area — AUM by Asset Class"),
    ]
    ws.write(18, 0, "Sheet", fmts["header"])
    ws.write(18, 1, "Chart Type & Description", fmts["header"])
    ws.set_column("B:B", 52)
    for r, (sheet, desc) in enumerate(index):
        is_s = r % 2 == 1
        ws.write(19 + r, 0, sheet, fmts["label_stripe"] if is_s else fmts["label"])
        ws.write(19 + r, 1, desc,  fmts["data_stripe"] if is_s else fmts["data"])


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main():
    wb = xlsxwriter.Workbook(OUTPUT_PATH, {"strings_to_numbers": False})
    fmts = add_formats(wb)

    build_cover(wb, fmts)
    build_column_chart(wb, fmts)
    build_line_chart(wb, fmts)
    build_stacked_bar(wb, fmts)
    build_waterfall(wb, fmts)
    build_combo_chart(wb, fmts)
    build_donut_chart(wb, fmts)
    build_scatter_chart(wb, fmts)
    build_area_chart(wb, fmts)

    wb.close()
    print(f"✅  Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
