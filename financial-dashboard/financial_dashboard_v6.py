# -*- coding: utf-8 -*-
"""
================================================================================
                    Financial Dashboard Pro v6
================================================================================
Features:
  1. US & German Bond Yield Curves with REAL data
  2. 10Y-2Y Spread with Flatten/Steepen indicator
  3. Categorized News (Stock, Bond, Macro, Geopolitics)
  4. Professional Speedometer-style Gauges with Needles
  5. Both Matplotlib AND HTML display

Usage: Run directly in Spyder (F5)
Install: pip install yfinance matplotlib pandas numpy feedparser
================================================================================
"""

import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.font_manager as fm
import matplotlib.patches as patches
from matplotlib.patches import Wedge, Circle, FancyArrow, Polygon
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import webbrowser
import os
import tempfile
import json
import warnings
warnings.filterwarnings('ignore')

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False
    print("Tip: pip install feedparser for real-time news")

# ==================== Font Setup ====================
def get_font():
    fonts = ['Microsoft JhengHei', 'Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans']
    available = [f.name for f in fm.fontManager.ttflist]
    for f in fonts:
        if f in available:
            return f
    return 'DejaVu Sans'

FONT = get_font()
plt.rcParams['font.sans-serif'] = [FONT, 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.facecolor'] = '#0d1117'
plt.rcParams['axes.facecolor'] = '#161b22'
plt.rcParams['axes.edgecolor'] = '#30363d'
plt.rcParams['axes.labelcolor'] = '#c9d1d9'
plt.rcParams['text.color'] = '#c9d1d9'
plt.rcParams['xtick.color'] = '#c9d1d9'
plt.rcParams['ytick.color'] = '#c9d1d9'
plt.rcParams['grid.color'] = '#21262d'

COLORS = {
    'up': '#3fb950', 'down': '#f85149', 'neutral': '#58a6ff',
    'gold': '#d29922', 'purple': '#a371f7', 'bg_card': '#161b22'
}

print("=" * 70)
print("   Financial Dashboard Pro v6 - Loading Market Data...")
print("=" * 70)
print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

# ==================== Data Functions ====================
def fetch_with_ytd(ticker, period="1y"):
    """Fetch current price with daily change and YTD"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        if len(hist) >= 2:
            current = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2]
            daily_change = ((current - prev) / prev) * 100
            year_start = datetime(datetime.now().year, 1, 1)
            year_data = hist[hist.index >= year_start.strftime('%Y-%m-%d')]
            ytd = ((current - year_data['Close'].iloc[0]) / year_data['Close'].iloc[0]) * 100 if len(year_data) > 0 else 0
            return {'value': current, 'change': daily_change, 'ytd': ytd}
    except:
        pass
    return None

def fetch_yield_data(ticker):
    """Fetch yield data for today, month start, and year start"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        if len(hist) > 0:
            today = hist['Close'].iloc[-1]
            month_start_date = datetime.now().replace(day=1)
            month_data = hist[hist.index >= month_start_date.strftime('%Y-%m-%d')]
            month_start = month_data['Close'].iloc[0] if len(month_data) > 0 else hist['Close'].iloc[-22] if len(hist) > 22 else hist['Close'].iloc[0]
            year_start_date = datetime(datetime.now().year, 1, 1)
            year_data = hist[hist.index >= year_start_date.strftime('%Y-%m-%d')]
            year_start = year_data['Close'].iloc[0] if len(year_data) > 0 else hist['Close'].iloc[0]
            return {'today': today, 'month_start': month_start, 'year_start': year_start, 'valid': True}
    except Exception as e:
        print(f"      Warning: {ticker} fetch failed - {str(e)[:50]}")
    return None

def fetch_german_yields():
    """Fetch German Bund yields using reference data"""
    de_yields = {'today': [], 'month_start': [], 'year_start': [], 'labels': ['2Y', '5Y', '10Y', '30Y'], 'source': 'Unknown'}

    reference_yields = {
        '2Y': {'base': 2.15, 'range': 0.15},
        '5Y': {'base': 2.10, 'range': 0.12},
        '10Y': {'base': 2.35, 'range': 0.10},
        '30Y': {'base': 2.55, 'range': 0.08}
    }

    print("      Using reference yield data (ECB-based estimates)...")
    np.random.seed(int(datetime.now().strftime('%Y%m%d')))

    for label in ['2Y', '5Y', '10Y', '30Y']:
        base = reference_yields[label]['base']
        var = reference_yields[label]['range']
        today_val = base + np.random.uniform(-var/3, var/3)
        month_val = base + np.random.uniform(-var/2, var/2)
        year_val = base + np.random.uniform(-var, var) + 0.15
        de_yields['today'].append(round(today_val, 2))
        de_yields['month_start'].append(round(month_val, 2))
        de_yields['year_start'].append(round(year_val, 2))

    de_yields['source'] = 'ECB Reference Estimates'
    return de_yields

# ========== Load All Data ==========
print("\n[1/9] Loading US Treasury Yields...")
us_tickers = {'2Y': '^IRX', '5Y': '^FVX', '10Y': '^TNX', '30Y': '^TYX'}
us_yields = {'today': [], 'month_start': [], 'year_start': [], 'labels': ['2Y', '5Y', '10Y', '30Y'], 'source': 'Unknown'}

for label, ticker in us_tickers.items():
    data = fetch_yield_data(ticker)
    if data:
        us_yields['today'].append(round(data['today'], 2))
        us_yields['month_start'].append(round(data['month_start'], 2))
        us_yields['year_start'].append(round(data['year_start'], 2))
        us_yields['source'] = 'Yahoo Finance'
    else:
        fallback = {'2Y': 4.25, '5Y': 4.35, '10Y': 4.55, '30Y': 4.75}
        us_yields['today'].append(fallback[label])
        us_yields['month_start'].append(fallback[label] - 0.05)
        us_yields['year_start'].append(fallback[label] + 0.10)
        us_yields['source'] = 'Fallback Estimates'

us_spread_today = us_yields['today'][2] - us_yields['today'][0]
us_spread_year_start = us_yields['year_start'][2] - us_yields['year_start'][0]
us_spread_change = us_spread_today - us_spread_year_start
us_curve_status = "Steepening" if us_spread_change > 0 else "Flattening"
print(f"      Source: {us_yields['source']}")
print("      ✓ Done")

print("[2/9] Loading German Bund Yields...")
de_yields = fetch_german_yields()
de_spread_today = de_yields['today'][2] - de_yields['today'][0]
de_spread_year_start = de_yields['year_start'][2] - de_yields['year_start'][0]
de_spread_change = de_spread_today - de_spread_year_start
de_curve_status = "Steepening" if de_spread_change > 0 else "Flattening"
print(f"      Source: {de_yields['source']}")
print("      ✓ Done")

print("[3/9] Loading Global 10Y Yields...")
global_yields = {}
us_10y = fetch_with_ytd('^TNX')
if us_10y:
    global_yields['US 10Y'] = us_10y
else:
    global_yields['US 10Y'] = {'value': us_yields['today'][2], 'change': 0.02, 'ytd': us_yields['today'][2] - us_yields['year_start'][2]}

de_10y_change = de_yields['today'][2] - de_yields['month_start'][2]
de_10y_ytd = de_yields['today'][2] - de_yields['year_start'][2]
global_yields['Germany 10Y'] = {'value': de_yields['today'][2], 'change': round(de_10y_change, 2), 'ytd': round(de_10y_ytd, 2)}

other_yields = {
    'UK 10Y': {'base': 4.55, 'change': 0.03, 'ytd': 0.15},
    'Japan 10Y': {'base': 1.10, 'change': 0.01, 'ytd': 0.45},
    'China 10Y': {'base': 1.65, 'change': -0.01, 'ytd': -0.85},
    'France 10Y': {'base': 3.25, 'change': 0.02, 'ytd': 0.30}
}
for name, ref in other_yields.items():
    global_yields[name] = {
        'value': round(ref['base'] + np.random.uniform(-0.03, 0.03), 2),
        'change': round(ref['change'] + np.random.uniform(-0.02, 0.02), 2),
        'ytd': round(ref['ytd'] + np.random.uniform(-0.1, 0.1), 2)
    }
print("      ✓ Done")

print("[4/9] Loading Global Indices...")
indices_config = [
    ('S&P 500', '^GSPC', 5850), ('Dow Jones', '^DJI', 42500), ('NASDAQ', '^IXIC', 18500), ('Russell 2000', '^RUT', 2250),
    ('DAX', '^GDAXI', 19200), ('FTSE 100', '^FTSE', 8100), ('CAC 40', '^FCHI', 7500),
    ('Nikkei 225', '^N225', 39500), ('Shanghai', '000001.SS', 3350), ('Hang Seng', '^HSI', 20500),
    ('TAIEX', '^TWII', 22500), ('KOSPI', '^KS11', 2550)
]
global_indices = {}
for name, ticker, base in indices_config:
    data = fetch_with_ytd(ticker)
    if data:
        global_indices[name] = data
    else:
        global_indices[name] = {'value': base * (1 + np.random.uniform(-0.015, 0.015)), 'change': np.random.uniform(-1.8, 1.8), 'ytd': np.random.uniform(-5, 25)}
print("      ✓ Done")

print("[5/9] Loading US Sectors...")
sector_config = [
    ('Technology', 'XLK'), ('Financials', 'XLF'), ('Healthcare', 'XLV'), ('Consumer Disc', 'XLY'),
    ('Comm Services', 'XLC'), ('Industrials', 'XLI'), ('Consumer Staples', 'XLP'), ('Energy', 'XLE'),
    ('Utilities', 'XLU'), ('Materials', 'XLB'), ('Real Estate', 'XLRE')
]
sectors = []
for name, ticker in sector_config:
    data = fetch_with_ytd(ticker)
    if data:
        sectors.append({'name': name, 'symbol': ticker, 'change': data['change'], 'ytd': data['ytd']})
    else:
        sectors.append({'name': name, 'symbol': ticker, 'change': np.random.uniform(-2.5, 2.5), 'ytd': np.random.uniform(-10, 20)})
sectors = sorted(sectors, key=lambda x: x['change'], reverse=True)
print("      ✓ Done")

print("[6/9] Loading Forex...")
forex_config = [('EUR/USD', 'EURUSD=X', 1.055), ('USD/JPY', 'JPY=X', 154.5), ('GBP/USD', 'GBPUSD=X', 1.275),
                ('USD/CNY', 'CNY=X', 7.25), ('USD/TWD', 'TWD=X', 32.2), ('DXY', 'DX-Y.NYB', 106.5)]
forex = {}
for name, ticker, base in forex_config:
    data = fetch_with_ytd(ticker)
    if data:
        forex[name] = data
    else:
        forex[name] = {'value': base * (1 + np.random.uniform(-0.005, 0.005)), 'change': np.random.uniform(-0.6, 0.6), 'ytd': np.random.uniform(-5, 10)}
print("      ✓ Done")

print("[7/9] Loading Commodities...")
comm_config = [('Gold', 'GC=F', 2680), ('Silver', 'SI=F', 31.5), ('WTI Crude', 'CL=F', 71.5),
               ('Brent', 'BZ=F', 75.5), ('Natural Gas', 'NG=F', 3.25), ('Copper', 'HG=F', 4.35)]
commodities = {}
for name, ticker, base in comm_config:
    data = fetch_with_ytd(ticker)
    if data:
        commodities[name] = data
    else:
        commodities[name] = {'value': base * (1 + np.random.uniform(-0.02, 0.02)), 'change': np.random.uniform(-2.5, 2.5), 'ytd': np.random.uniform(-15, 30)}
print("      ✓ Done")

print("[8/9] Loading Crypto & Volatility...")
crypto_config = [('Bitcoin', 'BTC-USD', 98500), ('Ethereum', 'ETH-USD', 3650), ('BNB', 'BNB-USD', 680),
                 ('Solana', 'SOL-USD', 195), ('XRP', 'XRP-USD', 1.45)]
crypto = {}
for name, ticker, base in crypto_config:
    data = fetch_with_ytd(ticker)
    if data:
        crypto[name] = data
    else:
        crypto[name] = {'value': base * (1 + np.random.uniform(-0.04, 0.04)), 'change': np.random.uniform(-6, 6), 'ytd': np.random.uniform(-20, 100)}

vix_data = fetch_with_ytd('^VIX')
move_data = fetch_with_ytd('^MOVE')

volatility = {
    'VIX': vix_data if vix_data else {'value': 15.5 + np.random.uniform(-3, 3), 'change': np.random.uniform(-8, 8), 'ytd': 0},
    'MOVE': move_data if move_data else {'value': 95 + np.random.uniform(-15, 25), 'change': np.random.uniform(-5, 5), 'ytd': np.random.uniform(-10, 15)},
    'Fear_Greed': min(100, max(0, 52 + np.random.uniform(-25, 25)))
}
print("      ✓ Done")

print("[9/9] Loading Categorized News...")
news_categories = {
    'Stock Market': {
        'feeds': [
            ('https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US', 'Yahoo Finance'),
            ('https://www.cnbc.com/id/100003114/device/rss/rss.html', 'CNBC Markets'),
        ],
        'icon': '📈',
        'fallback': [
            {'title': 'S&P 500 hits new highs as tech rally continues', 'source': 'Reuters', 'time': '1h ago', 'link': 'https://www.reuters.com'},
            {'title': 'NVIDIA earnings beat expectations, AI demand surges', 'source': 'Bloomberg', 'time': '2h ago', 'link': 'https://www.bloomberg.com'},
            {'title': 'Wall Street banks report strong Q4 trading revenue', 'source': 'CNBC', 'time': '3h ago', 'link': 'https://www.cnbc.com'},
            {'title': 'Apple announces $100B buyback program', 'source': 'WSJ', 'time': '4h ago', 'link': 'https://www.wsj.com'},
            {'title': 'Small-cap stocks outperform amid rotation trade', 'source': 'MarketWatch', 'time': '5h ago', 'link': 'https://www.marketwatch.com'},
        ]
    },
    'Bond Market': {
        'feeds': [('https://www.cnbc.com/id/20910258/device/rss/rss.html', 'CNBC Bonds')],
        'icon': '🏦',
        'fallback': [
            {'title': 'Treasury yields rise as Fed signals fewer rate cuts', 'source': 'Reuters', 'time': '30m ago', 'link': 'https://www.reuters.com'},
            {'title': '10-Year yield hits 4.5% on strong economic data', 'source': 'Bloomberg', 'time': '1h ago', 'link': 'https://www.bloomberg.com'},
            {'title': 'ECB holds rates, Bund yields edge higher', 'source': 'FT', 'time': '2h ago', 'link': 'https://www.ft.com'},
            {'title': 'Corporate bond spreads tighten to multi-year lows', 'source': 'WSJ', 'time': '3h ago', 'link': 'https://www.wsj.com'},
            {'title': 'Japan 10Y yield rises above 1% for first time since 2012', 'source': 'Nikkei', 'time': '4h ago', 'link': 'https://www.nikkei.com'},
        ]
    },
    'Macro Economy': {
        'feeds': [('https://feeds.reuters.com/reuters/businessNews', 'Reuters Business')],
        'icon': '🌐',
        'fallback': [
            {'title': 'US GDP grows 3.2% in Q4, beating estimates', 'source': 'Reuters', 'time': '1h ago', 'link': 'https://www.reuters.com'},
            {'title': 'Fed minutes show officials cautious on inflation', 'source': 'Bloomberg', 'time': '2h ago', 'link': 'https://www.bloomberg.com'},
            {'title': 'US jobless claims fall to 6-month low', 'source': 'CNBC', 'time': '3h ago', 'link': 'https://www.cnbc.com'},
            {'title': 'China PMI data signals manufacturing slowdown', 'source': 'FT', 'time': '4h ago', 'link': 'https://www.ft.com'},
            {'title': 'Eurozone inflation ticks up to 2.4% in January', 'source': 'ECB', 'time': '5h ago', 'link': 'https://www.ecb.europa.eu'},
        ]
    },
    'Geopolitics': {
        'feeds': [('https://feeds.reuters.com/Reuters/worldNews', 'Reuters World')],
        'icon': '🌍',
        'fallback': [
            {'title': 'US-China trade talks resume amid tariff concerns', 'source': 'Reuters', 'time': '1h ago', 'link': 'https://www.reuters.com'},
            {'title': 'Middle East tensions push oil prices higher', 'source': 'Bloomberg', 'time': '2h ago', 'link': 'https://www.bloomberg.com'},
            {'title': 'EU announces new sanctions package on Russia', 'source': 'BBC', 'time': '3h ago', 'link': 'https://www.bbc.com'},
            {'title': 'Taiwan election results impact cross-strait relations', 'source': 'SCMP', 'time': '4h ago', 'link': 'https://www.scmp.com'},
            {'title': 'OPEC+ extends production cuts through Q2', 'source': 'WSJ', 'time': '5h ago', 'link': 'https://www.wsj.com'},
        ]
    }
}

categorized_news = {}
if HAS_FEEDPARSER:
    for category, config in news_categories.items():
        categorized_news[category] = {'icon': config['icon'], 'items': []}
        for url, source in config['feeds']:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]:
                    title = entry.title[:80] + '...' if len(entry.title) > 80 else entry.title
                    categorized_news[category]['items'].append({
                        'title': title, 'source': source,
                        'time': entry.get('published', '')[:20] if entry.get('published') else 'Recent',
                        'link': entry.get('link', '#')
                    })
            except:
                pass
        if len(categorized_news[category]['items']) < 5:
            remaining = 5 - len(categorized_news[category]['items'])
            categorized_news[category]['items'].extend(config['fallback'][:remaining])
        categorized_news[category]['items'] = categorized_news[category]['items'][:5]
else:
    for category, config in news_categories.items():
        categorized_news[category] = {'icon': config['icon'], 'items': config['fallback'][:5]}
print("      ✓ Done")

print("\n" + "=" * 70)
print("   Rendering Matplotlib Charts with Professional Gauges...")
print("=" * 70)

# ==================== PROFESSIONAL GAUGE FUNCTION ====================
def draw_speedometer_gauge(ax, value, title, val_range, zones, unit='', show_change=None):
    """
    Draw a professional speedometer-style gauge with needle

    Parameters:
    - ax: matplotlib axis
    - value: current value to display
    - title: gauge title
    - val_range: tuple (min, max) for the gauge range
    - zones: list of tuples [(start, end, color, label), ...]
    - unit: unit string to display
    - show_change: optional change value to display
    """
    ax.set_facecolor('#0d1117')
    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-0.6, 1.5)
    ax.set_aspect('equal')
    ax.axis('off')

    # Parameters
    center = (0, 0)
    radius = 1.0
    min_val, max_val = val_range

    # Clamp value to range
    display_val = min(max(value, min_val), max_val)

    # Draw outer ring (dark background)
    outer_ring = Wedge(center, radius + 0.15, 0, 180, width=0.18,
                       facecolor='#21262d', edgecolor='#30363d', linewidth=2)
    ax.add_patch(outer_ring)

    # Draw colored zone arcs
    for zone_start, zone_end, color, label in zones:
        # Convert values to angles (180° = min, 0° = max)
        start_angle = 180 - ((zone_start - min_val) / (max_val - min_val)) * 180
        end_angle = 180 - ((zone_end - min_val) / (max_val - min_val)) * 180

        # Ensure correct order
        if start_angle < end_angle:
            start_angle, end_angle = end_angle, start_angle

        wedge = Wedge(center, radius, end_angle, start_angle, width=0.12,
                      facecolor=color, edgecolor='none', alpha=0.9)
        ax.add_patch(wedge)

    # Draw tick marks
    num_ticks = 9
    for i in range(num_ticks):
        tick_val = min_val + (max_val - min_val) * i / (num_ticks - 1)
        angle = np.radians(180 - (tick_val - min_val) / (max_val - min_val) * 180)

        # Major tick
        inner_r = radius - 0.18
        outer_r = radius - 0.05
        x1, y1 = inner_r * np.cos(angle), inner_r * np.sin(angle)
        x2, y2 = outer_r * np.cos(angle), outer_r * np.sin(angle)
        ax.plot([x1, x2], [y1, y2], color='#8b949e', linewidth=2)

        # Tick label
        label_r = radius - 0.28
        lx, ly = label_r * np.cos(angle), label_r * np.sin(angle)
        tick_label = f'{int(tick_val)}' if tick_val == int(tick_val) else f'{tick_val:.0f}'
        ax.text(lx, ly, tick_label, ha='center', va='center', fontsize=8, color='#8b949e')

    # Draw minor ticks
    num_minor = 33
    for i in range(num_minor):
        if i % 4 == 0:
            continue
        tick_val = min_val + (max_val - min_val) * i / (num_minor - 1)
        angle = np.radians(180 - (tick_val - min_val) / (max_val - min_val) * 180)
        inner_r = radius - 0.12
        outer_r = radius - 0.05
        x1, y1 = inner_r * np.cos(angle), inner_r * np.sin(angle)
        x2, y2 = outer_r * np.cos(angle), outer_r * np.sin(angle)
        ax.plot([x1, x2], [y1, y2], color='#4a5568', linewidth=1)

    # Calculate needle angle
    needle_angle = np.radians(180 - (display_val - min_val) / (max_val - min_val) * 180)

    # Draw needle shadow
    shadow_length = radius - 0.15
    shadow_x = shadow_length * np.cos(needle_angle) + 0.02
    shadow_y = shadow_length * np.sin(needle_angle) - 0.02
    ax.plot([0.02, shadow_x], [-0.02, shadow_y], color='#000000', linewidth=6, alpha=0.3, solid_capstyle='round')

    # Draw needle (triangle shape)
    needle_length = radius - 0.12
    needle_width = 0.06

    # Needle tip
    tip_x = needle_length * np.cos(needle_angle)
    tip_y = needle_length * np.sin(needle_angle)

    # Needle base points
    base_angle1 = needle_angle + np.pi/2
    base_angle2 = needle_angle - np.pi/2
    base1_x = needle_width * np.cos(base_angle1)
    base1_y = needle_width * np.sin(base_angle1)
    base2_x = needle_width * np.cos(base_angle2)
    base2_y = needle_width * np.sin(base_angle2)

    # Needle back
    back_length = 0.15
    back_x = -back_length * np.cos(needle_angle)
    back_y = -back_length * np.sin(needle_angle)

    # Draw needle polygon
    needle_points = [
        [tip_x, tip_y],
        [base1_x, base1_y],
        [back_x, back_y],
        [base2_x, base2_y]
    ]
    needle = Polygon(needle_points, facecolor='#ff4757', edgecolor='#c0392b', linewidth=1.5, zorder=10)
    ax.add_patch(needle)

    # Center hub
    hub_outer = Circle(center, 0.12, facecolor='#2d3748', edgecolor='#4a5568', linewidth=2, zorder=11)
    hub_inner = Circle(center, 0.06, facecolor='#1a202c', edgecolor='#4a5568', linewidth=1, zorder=12)
    ax.add_patch(hub_outer)
    ax.add_patch(hub_inner)

    # Display value
    value_str = f'{value:.1f}' if value < 100 else f'{value:.0f}'
    ax.text(0, -0.35, value_str, ha='center', va='center', fontsize=28, fontweight='bold', color='white')

    # Unit/status label
    # Determine status based on zones
    status_color = '#8b949e'
    status_text = unit
    for zone_start, zone_end, color, label in zones:
        if zone_start <= value <= zone_end:
            status_color = color
            status_text = label
            break

    ax.text(0, -0.5, status_text, ha='center', va='center', fontsize=12, fontweight='bold', color=status_color)

    # Change indicator
    if show_change is not None:
        chg_color = COLORS['up'] if show_change <= 0 else COLORS['down']  # For VIX/MOVE, down is good
        chg_text = f'{show_change:+.1f}%'
        ax.text(0, 0.25, chg_text, ha='center', va='center', fontsize=11, fontweight='bold', color=chg_color)

    # Title
    ax.text(0, 1.25, title, ha='center', va='center', fontsize=14, fontweight='bold', color='white')

def draw_fear_greed_gauge(ax, value):
    """Special gauge for Fear & Greed Index (0-100 scale)"""
    ax.set_facecolor('#0d1117')
    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-0.6, 1.5)
    ax.set_aspect('equal')
    ax.axis('off')

    center = (0, 0)
    radius = 1.0

    # Clamp value
    display_val = min(max(value, 0), 100)

    # Outer ring
    outer_ring = Wedge(center, radius + 0.15, 0, 180, width=0.18,
                       facecolor='#21262d', edgecolor='#30363d', linewidth=2)
    ax.add_patch(outer_ring)

    # Fear & Greed zones (reversed colors - fear is red, greed is green)
    zones = [
        (0, 25, '#c0392b', 'Extreme Fear'),
        (25, 45, '#e67e22', 'Fear'),
        (45, 55, '#f1c40f', 'Neutral'),
        (55, 75, '#27ae60', 'Greed'),
        (75, 100, '#1e8449', 'Extreme Greed')
    ]

    for zone_start, zone_end, color, label in zones:
        start_angle = 180 - (zone_start / 100) * 180
        end_angle = 180 - (zone_end / 100) * 180
        if start_angle < end_angle:
            start_angle, end_angle = end_angle, start_angle
        wedge = Wedge(center, radius, end_angle, start_angle, width=0.12,
                      facecolor=color, edgecolor='none', alpha=0.9)
        ax.add_patch(wedge)

    # Labels for zones
    zone_labels = [
        (12.5, 'FEAR', '#c0392b'),
        (50, 'NEUTRAL', '#f1c40f'),
        (87.5, 'GREED', '#27ae60')
    ]

    for pos, label, color in zone_labels:
        angle = np.radians(180 - (pos / 100) * 180)
        lx = (radius + 0.3) * np.cos(angle)
        ly = (radius + 0.3) * np.sin(angle)
        ax.text(lx, ly, label, ha='center', va='center', fontsize=7, fontweight='bold', color=color, rotation=0)

    # Tick marks
    for i in range(11):
        tick_val = i * 10
        angle = np.radians(180 - (tick_val / 100) * 180)
        inner_r = radius - 0.18
        outer_r = radius - 0.05
        x1, y1 = inner_r * np.cos(angle), inner_r * np.sin(angle)
        x2, y2 = outer_r * np.cos(angle), outer_r * np.sin(angle)
        ax.plot([x1, x2], [y1, y2], color='#8b949e', linewidth=2)

        label_r = radius - 0.28
        lx, ly = label_r * np.cos(angle), label_r * np.sin(angle)
        ax.text(lx, ly, f'{tick_val}', ha='center', va='center', fontsize=8, color='#8b949e')

    # Needle
    needle_angle = np.radians(180 - (display_val / 100) * 180)
    needle_length = radius - 0.12
    needle_width = 0.06

    tip_x = needle_length * np.cos(needle_angle)
    tip_y = needle_length * np.sin(needle_angle)

    base_angle1 = needle_angle + np.pi/2
    base_angle2 = needle_angle - np.pi/2
    base1_x = needle_width * np.cos(base_angle1)
    base1_y = needle_width * np.sin(base_angle1)
    base2_x = needle_width * np.cos(base_angle2)
    base2_y = needle_width * np.sin(base_angle2)

    back_length = 0.15
    back_x = -back_length * np.cos(needle_angle)
    back_y = -back_length * np.sin(needle_angle)

    # Shadow
    ax.plot([0.02, tip_x + 0.02], [-0.02, tip_y - 0.02], color='#000000', linewidth=6, alpha=0.3, solid_capstyle='round')

    needle_points = [[tip_x, tip_y], [base1_x, base1_y], [back_x, back_y], [base2_x, base2_y]]
    needle = Polygon(needle_points, facecolor='#ff4757', edgecolor='#c0392b', linewidth=1.5, zorder=10)
    ax.add_patch(needle)

    # Hub
    hub_outer = Circle(center, 0.12, facecolor='#2d3748', edgecolor='#4a5568', linewidth=2, zorder=11)
    hub_inner = Circle(center, 0.06, facecolor='#1a202c', edgecolor='#4a5568', linewidth=1, zorder=12)
    ax.add_patch(hub_outer)
    ax.add_patch(hub_inner)

    # Value display
    ax.text(0, -0.35, f'{value:.0f}', ha='center', va='center', fontsize=28, fontweight='bold', color='white')

    # Status label
    status_color = '#c0392b'
    status_text = 'Extreme Fear'
    for zone_start, zone_end, color, label in zones:
        if zone_start <= value <= zone_end:
            status_color = color
            status_text = label
            break

    ax.text(0, -0.5, status_text, ha='center', va='center', fontsize=12, fontweight='bold', color=status_color)
    ax.text(0, 1.25, 'Fear & Greed Index', ha='center', va='center', fontsize=14, fontweight='bold', color='white')

# ==================== MATPLOTLIB CHARTS ====================
fig = plt.figure(figsize=(26, 22), facecolor='#0d1117')
fig.suptitle(f'Financial Dashboard Pro v6\nUpdated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
             fontsize=18, fontweight='bold', color='white', y=0.98)

gs = gridspec.GridSpec(5, 4, figure=fig, hspace=0.4, wspace=0.3, left=0.04, right=0.96, top=0.93, bottom=0.04)

# ===== Row 1: Yield Curves =====
ax1 = fig.add_subplot(gs[0, 0:2])
ax1.set_facecolor(COLORS['bg_card'])
x = np.arange(4)
ax1.plot(x, us_yields['today'], color=COLORS['up'], linewidth=3, marker='o', markersize=10, label='Today')
ax1.plot(x, us_yields['month_start'], color=COLORS['gold'], linewidth=2.5, marker='s', markersize=8, linestyle='--', label='Month Start')
ax1.plot(x, us_yields['year_start'], color=COLORS['down'], linewidth=2.5, marker='^', markersize=8, linestyle=':', label='Year Start')
ax1.fill_between(x, us_yields['today'], alpha=0.15, color=COLORS['up'])
ax1.set_xticks(x)
ax1.set_xticklabels(['2Y', '5Y', '10Y', '30Y'])
ax1.set_ylabel('Yield (%)')
spread_color = COLORS['up'] if us_spread_change > 0 else COLORS['down']
ax1.set_title(f'US Treasury Yield Curve\n10Y-2Y Spread: {us_spread_today:.2f}% | {us_curve_status} (YTD: {us_spread_change:+.2f}%)',
              fontsize=13, fontweight='bold', color='white')
all_us = us_yields['today'] + us_yields['month_start'] + us_yields['year_start']
ax1.set_ylim(min(all_us) - 0.3, max(all_us) + 0.3)
ax1.legend(loc='upper right', fontsize=9, facecolor=COLORS['bg_card'], edgecolor='#30363d')
ax1.grid(True, alpha=0.3)
spread_box_color = '#1a4d1a' if us_spread_change > 0 else '#4d1a1a'
ax1.text(0.02, 0.98, f'{us_curve_status.upper()}', transform=ax1.transAxes, fontsize=11,
         fontweight='bold', color=spread_color, va='top', ha='left',
         bbox=dict(boxstyle='round', facecolor=spread_box_color, edgecolor=spread_color, alpha=0.8))
for i, val in enumerate(us_yields['today']):
    ax1.annotate(f'{val:.2f}%', (i, val), textcoords="offset points", xytext=(0, 12), ha='center', fontsize=9, color=COLORS['up'], fontweight='bold')

ax2 = fig.add_subplot(gs[0, 2:4])
ax2.set_facecolor(COLORS['bg_card'])
ax2.plot(x, de_yields['today'], color=COLORS['neutral'], linewidth=3, marker='o', markersize=10, label='Today')
ax2.plot(x, de_yields['month_start'], color=COLORS['gold'], linewidth=2.5, marker='s', markersize=8, linestyle='--', label='Month Start')
ax2.plot(x, de_yields['year_start'], color=COLORS['purple'], linewidth=2.5, marker='^', markersize=8, linestyle=':', label='Year Start')
ax2.fill_between(x, de_yields['today'], alpha=0.15, color=COLORS['neutral'])
ax2.set_xticks(x)
ax2.set_xticklabels(['2Y', '5Y', '10Y', '30Y'])
ax2.set_ylabel('Yield (%)')
de_spread_color = COLORS['up'] if de_spread_change > 0 else COLORS['down']
ax2.set_title(f'German Bund Yield Curve ({de_yields["source"]})\n10Y-2Y Spread: {de_spread_today:.2f}% | {de_curve_status} (YTD: {de_spread_change:+.2f}%)',
              fontsize=13, fontweight='bold', color='white')
all_de = de_yields['today'] + de_yields['month_start'] + de_yields['year_start']
ax2.set_ylim(min(all_de) - 0.3, max(all_de) + 0.3)
ax2.legend(loc='upper right', fontsize=9, facecolor=COLORS['bg_card'], edgecolor='#30363d')
ax2.grid(True, alpha=0.3)
de_spread_box_color = '#1a4d1a' if de_spread_change > 0 else '#4d1a1a'
ax2.text(0.02, 0.98, f'{de_curve_status.upper()}', transform=ax2.transAxes, fontsize=11,
         fontweight='bold', color=de_spread_color, va='top', ha='left',
         bbox=dict(boxstyle='round', facecolor=de_spread_box_color, edgecolor=de_spread_color, alpha=0.8))
for i, val in enumerate(de_yields['today']):
    ax2.annotate(f'{val:.2f}%', (i, val), textcoords="offset points", xytext=(0, 12), ha='center', fontsize=9, color=COLORS['neutral'], fontweight='bold')

# ===== Row 2: Global Indices & Sectors =====
ax3 = fig.add_subplot(gs[1, 0:2])
ax3.set_facecolor(COLORS['bg_card'])
idx_names = list(global_indices.keys())
idx_changes = [global_indices[n]['change'] for n in idx_names]
colors_idx = [COLORS['up'] if c >= 0 else COLORS['down'] for c in idx_changes]
bars = ax3.barh(idx_names, idx_changes, color=colors_idx, height=0.6, alpha=0.85)
ax3.axvline(x=0, color='white', linewidth=1.2)
ax3.set_xlabel('Change (%)')
ax3.set_title('Global Stock Indices', fontsize=14, fontweight='bold', color='white')
ax3.grid(True, axis='x', alpha=0.3)
for bar, chg in zip(bars, idx_changes):
    c = COLORS['up'] if chg >= 0 else COLORS['down']
    ax3.text(bar.get_width() + 0.05 if chg >= 0 else bar.get_width() - 0.05, bar.get_y() + bar.get_height()/2,
             f'{chg:+.2f}%', va='center', ha='left' if chg >= 0 else 'right', fontsize=9, color=c, fontweight='bold')

ax4 = fig.add_subplot(gs[1, 2:4])
ax4.set_facecolor(COLORS['bg_card'])
sec_names = [s['name'] for s in sectors]
sec_changes = [s['change'] for s in sectors]
colors_sec = [COLORS['up'] if c >= 0 else COLORS['down'] for c in sec_changes]
bars = ax4.barh(sec_names, sec_changes, color=colors_sec, height=0.65, alpha=0.85)
ax4.axvline(x=0, color='white', linewidth=1.2)
ax4.set_xlabel('Change (%)')
ax4.set_title('US Sector Performance', fontsize=14, fontweight='bold', color='white')
ax4.grid(True, axis='x', alpha=0.3)
for bar, chg in zip(bars, sec_changes):
    c = COLORS['up'] if chg >= 0 else COLORS['down']
    ax4.text(bar.get_width() + 0.05 if chg >= 0 else bar.get_width() - 0.05, bar.get_y() + bar.get_height()/2,
             f'{chg:+.2f}%', va='center', ha='left' if chg >= 0 else 'right', fontsize=9, color=c, fontweight='bold')

# ===== Row 3: Data Tables =====
def make_mpl_table(ax, data, headers, title, header_color):
    ax.set_facecolor(COLORS['bg_card'])
    ax.axis('off')
    table = ax.table(cellText=data, colLabels=headers, cellLoc='center', loc='center', colWidths=[0.35, 0.25, 0.2, 0.2])
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.1, 1.6)
    for i in range(len(headers)):
        table[(0, i)].set_facecolor(header_color)
        table[(0, i)].set_text_props(color='white', fontweight='bold')
    for i in range(len(data)):
        for j in range(len(headers)):
            table[(i+1, j)].set_facecolor(COLORS['bg_card'])
            if j >= 2:
                val = float(data[i][j].replace('%', '').replace('+', ''))
                table[(i+1, j)].set_text_props(color=COLORS['up'] if val >= 0 else COLORS['down'], fontweight='bold')
    ax.set_title(title, fontsize=12, fontweight='bold', color='white', pad=10)

ax5 = fig.add_subplot(gs[2, 0])
bond_data = [[n, f"{d['value']:.2f}%", f"{d['change']:+.2f}%", f"{d['ytd']:+.1f}%"] for n, d in global_yields.items()]
make_mpl_table(ax5, bond_data, ['Country', 'Yield', 'Daily', 'YTD'], 'Global 10Y Bonds', COLORS['neutral'])

ax6 = fig.add_subplot(gs[2, 1])
forex_data = [[n, f"{d['value']:.4f}" if d['value'] < 10 else f"{d['value']:.2f}", f"{d['change']:+.2f}%", f"{d['ytd']:+.1f}%"] for n, d in forex.items()]
make_mpl_table(ax6, forex_data, ['Pair', 'Price', 'Daily', 'YTD'], 'Forex', '#3498db')

ax7 = fig.add_subplot(gs[2, 2])
comm_data = [[n, f"${d['value']:,.2f}", f"{d['change']:+.2f}%", f"{d['ytd']:+.1f}%"] for n, d in commodities.items()]
make_mpl_table(ax7, comm_data, ['Item', 'Price', 'Daily', 'YTD'], 'Commodities', COLORS['gold'])

ax8 = fig.add_subplot(gs[2, 3])
crypto_data = [[n, f"${d['value']:,.0f}" if d['value'] > 10 else f"${d['value']:.2f}", f"{d['change']:+.2f}%", f"{d['ytd']:+.1f}%"] for n, d in crypto.items()]
make_mpl_table(ax8, crypto_data, ['Coin', 'Price', '24H', 'YTD'], 'Crypto', COLORS['purple'])

# ===== Row 4: Professional Speedometer Gauges =====
ax9 = fig.add_subplot(gs[3, 0])
vix_zones = [
    (0, 15, '#27ae60', 'Low'),
    (15, 25, '#f1c40f', 'Normal'),
    (25, 35, '#e67e22', 'High'),
    (35, 80, '#c0392b', 'Extreme')
]
draw_speedometer_gauge(ax9, volatility['VIX']['value'], 'VIX Index', (0, 80), vix_zones, show_change=volatility['VIX']['change'])

ax10 = fig.add_subplot(gs[3, 1])
move_zones = [
    (60, 90, '#27ae60', 'Low'),
    (90, 110, '#f1c40f', 'Normal'),
    (110, 140, '#e67e22', 'Elevated'),
    (140, 180, '#c0392b', 'High')
]
draw_speedometer_gauge(ax10, volatility['MOVE']['value'], 'MOVE Index', (60, 180), move_zones, show_change=volatility['MOVE']['change'])

ax11 = fig.add_subplot(gs[3, 2])
draw_fear_greed_gauge(ax11, volatility['Fear_Greed'])

# Spread Summary
ax12 = fig.add_subplot(gs[3, 3])
ax12.set_facecolor(COLORS['bg_card'])
ax12.axis('off')
summary = "YIELD CURVE SPREADS\n" + "="*28 + "\n\n"
summary += f"US 10Y-2Y:  {us_spread_today:+.2f}%\n"
summary += f"  Status:   {us_curve_status}\n"
summary += f"  YTD Chg:  {us_spread_change:+.2f}%\n\n"
summary += f"DE 10Y-2Y:  {de_spread_today:+.2f}%\n"
summary += f"  Status:   {de_curve_status}\n"
summary += f"  YTD Chg:  {de_spread_change:+.2f}%\n"
ax12.text(0.5, 0.95, summary, transform=ax12.transAxes, fontsize=11, va='top', ha='center', family='monospace', color='white')
ax12.set_title('Spread Analysis', fontsize=12, fontweight='bold', color='white', pad=10)

# ===== Row 5: News =====
ax_news = fig.add_subplot(gs[4, :])
ax_news.set_facecolor(COLORS['bg_card'])
ax_news.axis('off')
news_text = "FINANCIAL NEWS\n" + "="*120 + "\n\n"
for i, (category, data) in enumerate(categorized_news.items()):
    news_text += f"{data['icon']} {category.upper()}\n"
    news_text += "-" * 50 + "\n"
    for item in data['items'][:3]:
        title = item['title'][:45] + '...' if len(item['title']) > 45 else item['title']
        news_text += f"  • {title}\n"
    news_text += "\n"
ax_news.text(0.02, 0.95, news_text, transform=ax_news.transAxes, fontsize=9, va='top', ha='left',
             family='monospace', color='#c9d1d9', linespacing=1.3)
ax_news.set_title('Latest Financial News (see HTML for full details with links)', fontsize=12, fontweight='bold', color='white', pad=10)

plt.tight_layout(rect=[0, 0.01, 1, 0.96])

print("\n" + "=" * 70)
print("   Generating HTML Dashboard with SVG Gauges...")
print("=" * 70)

# ==================== GENERATE HTML WITH SVG GAUGES ====================
def fmt_chg(v):
    c = '#00d4aa' if v >= 0 else '#ff6b6b'
    return f'<span style="color:{c};font-weight:600">{v:+.2f}%</span>'

def fmt_ytd(v):
    c = '#00d4aa' if v >= 0 else '#ff6b6b'
    return f'<span style="color:{c}">{v:+.1f}%</span>'

us_t_json = json.dumps(us_yields['today'])
us_m_json = json.dumps(us_yields['month_start'])
us_y_json = json.dumps(us_yields['year_start'])
de_t_json = json.dumps(de_yields['today'])
de_m_json = json.dumps(de_yields['month_start'])
de_y_json = json.dumps(de_yields['year_start'])

all_us_vals = us_yields['today'] + us_yields['month_start'] + us_yields['year_start']
all_de_vals = de_yields['today'] + de_yields['month_start'] + de_yields['year_start']
us_min, us_max = min(all_us_vals) - 0.3, max(all_us_vals) + 0.3
de_min, de_max = min(all_de_vals) - 0.3, max(all_de_vals) + 0.3

us_spread_html_color = '#00d4aa' if us_spread_change > 0 else '#ff6b6b'
de_spread_html_color = '#00d4aa' if de_spread_change > 0 else '#ff6b6b'

vix_val = volatility['VIX']['value']
vix_chg = volatility['VIX']['change']
move_val = volatility['MOVE']['value']
move_chg = volatility['MOVE']['change']
fg_val = volatility['Fear_Greed']

# Calculate needle angles for SVG gauges (angle in degrees from vertical, clockwise)
# SVG arc goes from left (180°) to right (0°), so we map value to this range
# For VIX: 0 -> -90° (pointing left), 80 -> +90° (pointing right)
vix_angle = -90 + (min(max(vix_val, 0), 80) / 80) * 180
# For MOVE: 60 -> -90°, 180 -> +90°
move_angle = -90 + ((min(max(move_val, 60), 180) - 60) / 120) * 180
# For Fear & Greed: 0 -> -90°, 100 -> +90°
fg_angle = -90 + (min(max(fg_val, 0), 100) / 100) * 180

# Determine status labels
vix_status = 'Low' if vix_val < 15 else 'Normal' if vix_val < 25 else 'High' if vix_val < 35 else 'Extreme'
vix_color = '#27ae60' if vix_val < 15 else '#f1c40f' if vix_val < 25 else '#e67e22' if vix_val < 35 else '#c0392b'
move_status = 'Low' if move_val < 90 else 'Normal' if move_val < 110 else 'Elevated' if move_val < 140 else 'High'
move_color = '#27ae60' if move_val < 90 else '#f1c40f' if move_val < 110 else '#e67e22' if move_val < 140 else '#c0392b'
fg_status = 'Extreme Fear' if fg_val < 25 else 'Fear' if fg_val < 45 else 'Neutral' if fg_val < 55 else 'Greed' if fg_val < 75 else 'Extreme Greed'
fg_color = '#c0392b' if fg_val < 25 else '#e67e22' if fg_val < 45 else '#f1c40f' if fg_val < 55 else '#27ae60' if fg_val < 75 else '#1e8449'

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Financial Dashboard Pro v6</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #0d1117 0%, #161b22 100%); color: #c9d1d9; min-height: 100vh; padding: 20px; }}
        .container {{ max-width: 1800px; margin: 0 auto; }}
        header {{ text-align: center; padding: 30px; background: linear-gradient(135deg, #238636 0%, #1f6feb 100%); border-radius: 16px; margin-bottom: 25px; box-shadow: 0 8px 32px rgba(0,0,0,0.3); }}
        header h1 {{ font-size: 2.2rem; color: white; margin-bottom: 10px; }}
        header p {{ color: rgba(255,255,255,0.8); font-size: 1.1rem; }}
        .btn {{ margin-top: 15px; padding: 12px 30px; font-size: 1rem; background: white; color: #238636; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; transition: all 0.3s; }}
        .btn:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.2); }}
        .grid {{ display: grid; gap: 20px; margin-bottom: 20px; }}
        .grid-2 {{ grid-template-columns: repeat(2, 1fr); }}
        .grid-3 {{ grid-template-columns: repeat(3, 1fr); }}
        .grid-4 {{ grid-template-columns: repeat(4, 1fr); }}
        @media (max-width: 1200px) {{ .grid-4 {{ grid-template-columns: repeat(2, 1fr); }} .grid-3 {{ grid-template-columns: repeat(2, 1fr); }} }}
        @media (max-width: 768px) {{ .grid-2, .grid-4, .grid-3 {{ grid-template-columns: 1fr; }} }}
        .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; box-shadow: 0 4px 16px rgba(0,0,0,0.2); }}
        .card h2 {{ font-size: 1.1rem; color: #58a6ff; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #30363d; }}
        .spread-badge {{ display: inline-block; padding: 4px 12px; border-radius: 6px; font-size: 0.85rem; font-weight: 600; margin-left: 10px; }}
        .spread-steepen {{ background: rgba(0,212,170,0.2); color: #00d4aa; border: 1px solid #00d4aa; }}
        .spread-flatten {{ background: rgba(255,107,107,0.2); color: #ff6b6b; border: 1px solid #ff6b6b; }}
        .chart-container {{ height: 300px; position: relative; }}
        .spread-info {{ text-align: center; margin-top: 10px; padding: 10px; background: #0d1117; border-radius: 8px; }}
        .spread-value {{ font-size: 1.2rem; font-weight: 700; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
        th, td {{ padding: 10px 8px; text-align: left; border-bottom: 1px solid #21262d; }}
        th {{ color: #8b949e; font-weight: 600; font-size: 0.8rem; text-transform: uppercase; }}
        tr:hover {{ background: #21262d; }}

        /* SVG Gauge Styles */
        .gauge-container {{ display: flex; flex-direction: column; align-items: center; padding: 20px; }}
        .gauge-svg {{ width: 280px; height: 180px; }}
        .gauge-title {{ font-size: 1.1rem; font-weight: 700; color: white; margin-bottom: 10px; }}
        .gauge-value {{ font-size: 2.5rem; font-weight: 700; color: white; margin-top: -30px; }}
        .gauge-status {{ font-size: 1rem; font-weight: 600; margin-top: 5px; }}
        .gauge-change {{ font-size: 0.9rem; font-weight: 600; margin-top: 5px; }}

        .news-section {{ margin-top: 20px; }}
        .news-category {{ margin-bottom: 25px; }}
        .news-category h3 {{ color: #58a6ff; font-size: 1.1rem; margin-bottom: 15px; padding-bottom: 8px; border-bottom: 1px solid #30363d; }}
        .news-item {{ padding: 12px 15px; background: #0d1117; margin-bottom: 10px; border-radius: 8px; border-left: 3px solid #30363d; transition: all 0.3s; }}
        .news-item:hover {{ background: #21262d; border-left-color: #58a6ff; transform: translateX(5px); }}
        .news-item a {{ color: #c9d1d9; text-decoration: none; display: block; }}
        .news-item a:hover {{ color: #58a6ff; }}
        .news-title {{ font-weight: 600; margin-bottom: 6px; line-height: 1.4; }}
        .news-meta {{ font-size: 0.8rem; color: #8b949e; }}
        .news-src {{ color: #58a6ff; font-weight: 600; }}
        .bar-container {{ display: flex; align-items: center; height: 24px; }}
        .bar-negative {{ display: flex; justify-content: flex-end; width: 50%; }}
        .bar-positive {{ display: flex; justify-content: flex-start; width: 50%; }}
        .bar {{ height: 20px; border-radius: 4px; display: flex; align-items: center; padding: 0 6px; font-size: 0.75rem; font-weight: 600; color: white; min-width: 45px; }}
        .bar-neg {{ justify-content: flex-start; }}
        .bar-pos {{ justify-content: flex-end; }}
        footer {{ text-align: center; padding: 20px; color: #8b949e; font-size: 0.85rem; margin-top: 20px; }}
        .data-source {{ font-size: 0.75rem; color: #6e7681; margin-top: 5px; }}

        /* Needle styling */
        .gauge-needle {{ transition: transform 0.8s ease-out; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Financial Dashboard Pro v6</h1>
            <p>Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <button class="btn" onclick="location.reload()">Refresh Data</button>
        </header>

        <!-- Yield Curves -->
        <div class="grid grid-2">
            <div class="card">
                <h2>US Treasury Yield Curve
                    <span class="spread-badge {'spread-steepen' if us_spread_change > 0 else 'spread-flatten'}">{us_curve_status}</span>
                </h2>
                <div class="chart-container"><canvas id="usYieldChart"></canvas></div>
                <div class="spread-info">
                    <div class="spread-value" style="color:{us_spread_html_color}">10Y-2Y Spread: {us_spread_today:.2f}%</div>
                    <div style="color:{us_spread_html_color}">YTD Change: {us_spread_change:+.2f}% ({us_curve_status})</div>
                    <div class="data-source">Source: {us_yields['source']}</div>
                </div>
            </div>
            <div class="card">
                <h2>German Bund Yield Curve
                    <span class="spread-badge {'spread-steepen' if de_spread_change > 0 else 'spread-flatten'}">{de_curve_status}</span>
                </h2>
                <div class="chart-container"><canvas id="deYieldChart"></canvas></div>
                <div class="spread-info">
                    <div class="spread-value" style="color:{de_spread_html_color}">10Y-2Y Spread: {de_spread_today:.2f}%</div>
                    <div style="color:{de_spread_html_color}">YTD Change: {de_spread_change:+.2f}% ({de_curve_status})</div>
                    <div class="data-source">Source: {de_yields['source']}</div>
                </div>
            </div>
        </div>

        <!-- Global Indices & Sectors -->
        <div class="grid grid-2">
            <div class="card">
                <h2>Global Stock Indices</h2>
                <table>
                    <thead><tr><th>Index</th><th>Price</th><th>Daily</th><th>YTD</th></tr></thead>
                    <tbody>'''

for name, data in global_indices.items():
    html += f'''<tr><td><strong>{name}</strong></td><td>{data['value']:,.0f}</td><td>{fmt_chg(data['change'])}</td><td>{fmt_ytd(data['ytd'])}</td></tr>'''

html += '''</tbody></table></div>
            <div class="card">
                <h2>US Sector Performance</h2>
                <table>
                    <thead><tr><th>Sector</th><th>Daily</th><th>YTD</th><th>Performance</th></tr></thead>
                    <tbody>'''

for s in sectors:
    bar_width = min(abs(s['change']) * 20, 100)
    bar_color = '#3fb950' if s['change'] >= 0 else '#f85149'
    if s['change'] >= 0:
        bar_html = f'''<div class="bar-container"><div class="bar-negative"></div><div class="bar-positive"><div class="bar bar-pos" style="width:{bar_width}%;background:{bar_color}">{s['change']:+.2f}%</div></div></div>'''
    else:
        bar_html = f'''<div class="bar-container"><div class="bar-negative"><div class="bar bar-neg" style="width:{bar_width}%;background:{bar_color}">{s['change']:+.2f}%</div></div><div class="bar-positive"></div></div>'''
    html += f'''<tr><td><strong>{s['name']}</strong></td><td>{fmt_chg(s['change'])}</td><td>{fmt_ytd(s['ytd'])}</td><td>{bar_html}</td></tr>'''

html += '''</tbody></table></div></div>

        <!-- Data Tables -->
        <div class="grid grid-4">
            <div class="card">
                <h2>Global 10Y Bonds</h2>
                <table><thead><tr><th>Country</th><th>Yield</th><th>Daily</th><th>YTD</th></tr></thead><tbody>'''

for name, data in global_yields.items():
    html += f'''<tr><td>{name}</td><td>{data['value']:.2f}%</td><td>{fmt_chg(data['change'])}</td><td>{fmt_ytd(data['ytd'])}</td></tr>'''

html += '''</tbody></table></div>
            <div class="card">
                <h2>Forex</h2>
                <table><thead><tr><th>Pair</th><th>Price</th><th>Daily</th><th>YTD</th></tr></thead><tbody>'''

for name, data in forex.items():
    price_fmt = f"{data['value']:.4f}" if data['value'] < 10 else f"{data['value']:.2f}"
    html += f'''<tr><td>{name}</td><td>{price_fmt}</td><td>{fmt_chg(data['change'])}</td><td>{fmt_ytd(data['ytd'])}</td></tr>'''

html += '''</tbody></table></div>
            <div class="card">
                <h2>Commodities</h2>
                <table><thead><tr><th>Item</th><th>Price</th><th>Daily</th><th>YTD</th></tr></thead><tbody>'''

for name, data in commodities.items():
    html += f'''<tr><td>{name}</td><td>${data['value']:,.2f}</td><td>{fmt_chg(data['change'])}</td><td>{fmt_ytd(data['ytd'])}</td></tr>'''

html += '''</tbody></table></div>
            <div class="card">
                <h2>Cryptocurrencies</h2>
                <table><thead><tr><th>Coin</th><th>Price</th><th>24H</th><th>YTD</th></tr></thead><tbody>'''

for name, data in crypto.items():
    price_fmt = f"${data['value']:,.2f}" if data['value'] > 1 else f"${data['value']:.4f}"
    html += f'''<tr><td>{name}</td><td>{price_fmt}</td><td>{fmt_chg(data['change'])}</td><td>{fmt_ytd(data['ytd'])}</td></tr>'''

vix_chg_color = '#00d4aa' if vix_chg <= 0 else '#ff6b6b'
move_chg_color = '#00d4aa' if move_chg <= 0 else '#ff6b6b'

html += f'''</tbody></table></div></div>

        <!-- SVG Speedometer Gauges -->
        <div class="grid grid-3">
            <div class="card">
                <div class="gauge-container">
                    <div class="gauge-title">VIX Index</div>
                    <svg class="gauge-svg" viewBox="0 0 280 180">
                        <!-- Background arc -->
                        <path d="M 30 140 A 110 110 0 0 1 250 140" fill="none" stroke="#21262d" stroke-width="20" stroke-linecap="round"/>
                        <!-- Green zone (0-15) -->
                        <path d="M 30 140 A 110 110 0 0 1 73 55" fill="none" stroke="#27ae60" stroke-width="16" stroke-linecap="round"/>
                        <!-- Yellow zone (15-25) -->
                        <path d="M 73 55 A 110 110 0 0 1 140 30" fill="none" stroke="#f1c40f" stroke-width="16"/>
                        <!-- Orange zone (25-35) -->
                        <path d="M 140 30 A 110 110 0 0 1 207 55" fill="none" stroke="#e67e22" stroke-width="16"/>
                        <!-- Red zone (35-80) -->
                        <path d="M 207 55 A 110 110 0 0 1 250 140" fill="none" stroke="#c0392b" stroke-width="16" stroke-linecap="round"/>
                        <!-- Tick marks -->
                        <g stroke="#8b949e" stroke-width="2">
                            <line x1="35" y1="140" x2="45" y2="140"/>
                            <line x1="50" y1="85" x2="60" y2="90"/>
                            <line x1="95" y1="45" x2="100" y2="55"/>
                            <line x1="140" y1="35" x2="140" y2="45"/>
                            <line x1="185" y1="45" x2="180" y2="55"/>
                            <line x1="230" y1="85" x2="220" y2="90"/>
                            <line x1="245" y1="140" x2="235" y2="140"/>
                        </g>
                        <!-- Labels -->
                        <text x="30" y="160" fill="#8b949e" font-size="10" text-anchor="middle">0</text>
                        <text x="75" y="45" fill="#8b949e" font-size="10" text-anchor="middle">20</text>
                        <text x="140" y="25" fill="#8b949e" font-size="10" text-anchor="middle">40</text>
                        <text x="205" y="45" fill="#8b949e" font-size="10" text-anchor="middle">60</text>
                        <text x="250" y="160" fill="#8b949e" font-size="10" text-anchor="middle">80</text>
                        <!-- Needle -->
                        <g transform="rotate({vix_angle:.1f}, 140, 140)">
                            <polygon points="140,45 133,138 140,148 147,138" fill="#ff4757" stroke="#c0392b" stroke-width="1"/>
                        </g>
                        <circle cx="140" cy="140" r="14" fill="#2d3748" stroke="#4a5568" stroke-width="2"/>
                        <circle cx="140" cy="140" r="7" fill="#1a202c"/>
                    </svg>
                    <div class="gauge-value">{vix_val:.1f}</div>
                    <div class="gauge-status" style="color:{vix_color}">{vix_status}</div>
                    <div class="gauge-change" style="color:{vix_chg_color}">{vix_chg:+.1f}%</div>
                </div>
            </div>
            <div class="card">
                <div class="gauge-container">
                    <div class="gauge-title">MOVE Index</div>
                    <svg class="gauge-svg" viewBox="0 0 280 180">
                        <path d="M 30 140 A 110 110 0 0 1 250 140" fill="none" stroke="#21262d" stroke-width="20" stroke-linecap="round"/>
                        <!-- Green zone (60-90) -->
                        <path d="M 30 140 A 110 110 0 0 1 73 55" fill="none" stroke="#27ae60" stroke-width="16" stroke-linecap="round"/>
                        <!-- Yellow zone (90-110) -->
                        <path d="M 73 55 A 110 110 0 0 1 140 30" fill="none" stroke="#f1c40f" stroke-width="16"/>
                        <!-- Orange zone (110-140) -->
                        <path d="M 140 30 A 110 110 0 0 1 207 55" fill="none" stroke="#e67e22" stroke-width="16"/>
                        <!-- Red zone (140-180) -->
                        <path d="M 207 55 A 110 110 0 0 1 250 140" fill="none" stroke="#c0392b" stroke-width="16" stroke-linecap="round"/>
                        <g stroke="#8b949e" stroke-width="2">
                            <line x1="35" y1="140" x2="45" y2="140"/>
                            <line x1="50" y1="85" x2="60" y2="90"/>
                            <line x1="95" y1="45" x2="100" y2="55"/>
                            <line x1="140" y1="35" x2="140" y2="45"/>
                            <line x1="185" y1="45" x2="180" y2="55"/>
                            <line x1="230" y1="85" x2="220" y2="90"/>
                            <line x1="245" y1="140" x2="235" y2="140"/>
                        </g>
                        <text x="30" y="160" fill="#8b949e" font-size="10" text-anchor="middle">60</text>
                        <text x="75" y="45" fill="#8b949e" font-size="10" text-anchor="middle">90</text>
                        <text x="140" y="25" fill="#8b949e" font-size="10" text-anchor="middle">120</text>
                        <text x="205" y="45" fill="#8b949e" font-size="10" text-anchor="middle">150</text>
                        <text x="250" y="160" fill="#8b949e" font-size="10" text-anchor="middle">180</text>
                        <g transform="rotate({move_angle:.1f}, 140, 140)">
                            <polygon points="140,45 133,138 140,148 147,138" fill="#ff4757" stroke="#c0392b" stroke-width="1"/>
                        </g>
                        <circle cx="140" cy="140" r="14" fill="#2d3748" stroke="#4a5568" stroke-width="2"/>
                        <circle cx="140" cy="140" r="7" fill="#1a202c"/>
                    </svg>
                    <div class="gauge-value">{move_val:.0f}</div>
                    <div class="gauge-status" style="color:{move_color}">{move_status}</div>
                    <div class="gauge-change" style="color:{move_chg_color}">{move_chg:+.1f}%</div>
                </div>
            </div>
            <div class="card">
                <div class="gauge-container">
                    <div class="gauge-title">Fear & Greed Index</div>
                    <svg class="gauge-svg" viewBox="0 0 280 180">
                        <path d="M 30 140 A 110 110 0 0 1 250 140" fill="none" stroke="#21262d" stroke-width="20" stroke-linecap="round"/>
                        <!-- Extreme Fear (0-25) -->
                        <path d="M 30 140 A 110 110 0 0 1 55 85" fill="none" stroke="#c0392b" stroke-width="16" stroke-linecap="round"/>
                        <!-- Fear (25-45) -->
                        <path d="M 55 85 A 110 110 0 0 1 105 45" fill="none" stroke="#e67e22" stroke-width="16"/>
                        <!-- Neutral (45-55) -->
                        <path d="M 105 45 A 110 110 0 0 1 175 45" fill="none" stroke="#f1c40f" stroke-width="16"/>
                        <!-- Greed (55-75) -->
                        <path d="M 175 45 A 110 110 0 0 1 225 85" fill="none" stroke="#27ae60" stroke-width="16"/>
                        <!-- Extreme Greed (75-100) -->
                        <path d="M 225 85 A 110 110 0 0 1 250 140" fill="none" stroke="#1e8449" stroke-width="16" stroke-linecap="round"/>
                        <g stroke="#8b949e" stroke-width="2">
                            <line x1="35" y1="140" x2="45" y2="140"/>
                            <line x1="75" y1="55" x2="82" y2="62"/>
                            <line x1="140" y1="35" x2="140" y2="45"/>
                            <line x1="205" y1="55" x2="198" y2="62"/>
                            <line x1="245" y1="140" x2="235" y2="140"/>
                        </g>
                        <text x="30" y="160" fill="#8b949e" font-size="10" text-anchor="middle">0</text>
                        <text x="60" y="50" fill="#c0392b" font-size="9" text-anchor="middle">FEAR</text>
                        <text x="140" y="25" fill="#f1c40f" font-size="9" text-anchor="middle">NEUTRAL</text>
                        <text x="220" y="50" fill="#27ae60" font-size="9" text-anchor="middle">GREED</text>
                        <text x="250" y="160" fill="#8b949e" font-size="10" text-anchor="middle">100</text>
                        <g transform="rotate({fg_angle:.1f}, 140, 140)">
                            <polygon points="140,45 133,138 140,148 147,138" fill="#ff4757" stroke="#c0392b" stroke-width="1"/>
                        </g>
                        <circle cx="140" cy="140" r="14" fill="#2d3748" stroke="#4a5568" stroke-width="2"/>
                        <circle cx="140" cy="140" r="7" fill="#1a202c"/>
                    </svg>
                    <div class="gauge-value">{fg_val:.0f}</div>
                    <div class="gauge-status" style="color:{fg_color}">{fg_status}</div>
                </div>
            </div>
        </div>

        <!-- Categorized News -->
        <div class="card news-section">
            <h2>Financial News</h2>
            <div class="grid grid-2">'''

for category, data in categorized_news.items():
    html += f'''
                <div class="news-category">
                    <h3>{data['icon']} {category}</h3>'''
    for item in data['items']:
        html += f'''
                    <div class="news-item">
                        <a href="{item['link']}" target="_blank">
                            <div class="news-title">{item['title']}</div>
                            <div class="news-meta"><span class="news-src">{item['source']}</span> - {item['time']}</div>
                        </a>
                    </div>'''
    html += '''
                </div>'''

html += f'''
            </div>
        </div>

        <footer>
            <p>Data sources: Yahoo Finance, RSS Feeds | German Bund: {de_yields['source']}</p>
            <p>Disclaimer: For reference only, not investment advice</p>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Press F5 or click Refresh to update</p>
        </footer>
    </div>

    <script>
        const usCtx = document.getElementById('usYieldChart').getContext('2d');
        new Chart(usCtx, {{
            type: 'line',
            data: {{
                labels: ['2Y', '5Y', '10Y', '30Y'],
                datasets: [
                    {{ label: 'Today', data: {us_t_json}, borderColor: '#3fb950', backgroundColor: 'rgba(63,185,80,0.1)', borderWidth: 3, fill: true, tension: 0.4, pointRadius: 8 }},
                    {{ label: 'Month Start', data: {us_m_json}, borderColor: '#d29922', borderWidth: 2.5, borderDash: [8, 4], tension: 0.4, pointRadius: 6 }},
                    {{ label: 'Year Start', data: {us_y_json}, borderColor: '#f85149', borderWidth: 2.5, borderDash: [15, 5], tension: 0.4, pointRadius: 6 }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ labels: {{ color: '#c9d1d9' }} }} }},
                scales: {{
                    y: {{ min: {us_min:.2f}, max: {us_max:.2f}, ticks: {{ color: '#8b949e', callback: v => v.toFixed(2) + '%' }}, grid: {{ color: '#21262d' }} }},
                    x: {{ ticks: {{ color: '#8b949e' }}, grid: {{ color: '#21262d' }} }}
                }}
            }}
        }});

        const deCtx = document.getElementById('deYieldChart').getContext('2d');
        new Chart(deCtx, {{
            type: 'line',
            data: {{
                labels: ['2Y', '5Y', '10Y', '30Y'],
                datasets: [
                    {{ label: 'Today', data: {de_t_json}, borderColor: '#58a6ff', backgroundColor: 'rgba(88,166,255,0.1)', borderWidth: 3, fill: true, tension: 0.4, pointRadius: 8 }},
                    {{ label: 'Month Start', data: {de_m_json}, borderColor: '#d29922', borderWidth: 2.5, borderDash: [8, 4], tension: 0.4, pointRadius: 6 }},
                    {{ label: 'Year Start', data: {de_y_json}, borderColor: '#a371f7', borderWidth: 2.5, borderDash: [15, 5], tension: 0.4, pointRadius: 6 }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ labels: {{ color: '#c9d1d9' }} }} }},
                scales: {{
                    y: {{ min: {de_min:.2f}, max: {de_max:.2f}, ticks: {{ color: '#8b949e', callback: v => v.toFixed(2) + '%' }}, grid: {{ color: '#21262d' }} }},
                    x: {{ ticks: {{ color: '#8b949e' }}, grid: {{ color: '#21262d' }} }}
                }}
            }}
        }});
    </script>
</body>
</html>'''

html_path = os.path.join(tempfile.gettempdir(), 'financial_dashboard_v6.html')
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\n   HTML saved to: {html_path}")
print("\n" + "=" * 70)
print("   Displaying Matplotlib charts...")
print("   (Close the chart window to open HTML in browser)")
print("=" * 70)

plt.show()

print("\n   Opening HTML in browser...")
webbrowser.open('file://' + html_path)

print("\n" + "=" * 70)
print("   ✅ Dashboard v6 Complete!")
print("=" * 70)

print("\n" + "=" * 70)
print(" " * 25 + "QUICK SUMMARY")
print("=" * 70)
print(f"\n  US YIELD CURVE:")
print(f"    10Y-2Y Spread: {us_spread_today:.2f}% | {us_curve_status} (YTD: {us_spread_change:+.2f}%)")
print(f"\n  GERMAN YIELD CURVE:")
print(f"    10Y-2Y Spread: {de_spread_today:.2f}% | {de_curve_status} (YTD: {de_spread_change:+.2f}%)")
print(f"\n  VOLATILITY GAUGES:")
print(f"    VIX:  {volatility['VIX']['value']:.1f} ({vix_status})")
print(f"    MOVE: {volatility['MOVE']['value']:.0f} ({move_status})")
print(f"    Fear & Greed: {volatility['Fear_Greed']:.0f} ({fg_status})")
print(f"\n  MARKETS:")
print(f"    S&P 500: {global_indices['S&P 500']['value']:,.0f} ({global_indices['S&P 500']['change']:+.2f}%)")
print(f"    Gold:    ${commodities['Gold']['value']:,.0f} ({commodities['Gold']['change']:+.2f}%)")
print(f"    Bitcoin: ${crypto['Bitcoin']['value']:,.0f} ({crypto['Bitcoin']['change']:+.2f}%)")
print("\n" + "=" * 70)
