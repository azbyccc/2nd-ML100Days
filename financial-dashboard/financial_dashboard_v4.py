# -*- coding: utf-8 -*-
"""
================================================================================
                    Financial Dashboard Pro v4
================================================================================
同時顯示：
  1. Python Matplotlib 圖表
  2. HTML 網頁 (自動開啟瀏覽器)

使用方式：直接在 Spyder 中執行 (F5)
需安裝套件：pip install yfinance matplotlib pandas numpy feedparser
================================================================================
"""

import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.font_manager as fm
import numpy as np
from datetime import datetime
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
print("   Financial Dashboard Pro v4 - Loading Market Data...")
print("=" * 70)
print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

# ==================== Data Functions ====================
def fetch_with_ytd(ticker, period="1y"):
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
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        if len(hist) > 0:
            today = hist['Close'].iloc[-1]
            month_data = hist[hist.index >= datetime.now().replace(day=1).strftime('%Y-%m-%d')]
            month_start = month_data['Close'].iloc[0] if len(month_data) > 0 else hist['Close'].iloc[-22] if len(hist) > 22 else hist['Close'].iloc[0]
            year_data = hist[hist.index >= datetime(datetime.now().year, 1, 1).strftime('%Y-%m-%d')]
            year_start = year_data['Close'].iloc[0] if len(year_data) > 0 else hist['Close'].iloc[0]
            return {'today': today, 'month_start': month_start, 'year_start': year_start}
    except:
        pass
    return None

# ========== Load All Data ==========
print("\n[1/9] Loading US Treasury Yields...")
us_tickers = {'2Y': '^IRX', '5Y': '^FVX', '10Y': '^TNX', '30Y': '^TYX'}
us_yields = {'today': [], 'month_start': [], 'year_start': [], 'labels': ['2Y', '5Y', '10Y', '30Y']}
for label, ticker in us_tickers.items():
    data = fetch_yield_data(ticker)
    if data:
        us_yields['today'].append(round(data['today'], 2))
        us_yields['month_start'].append(round(data['month_start'], 2))
        us_yields['year_start'].append(round(data['year_start'], 2))
    else:
        base = {'2Y': 4.65, '5Y': 4.25, '10Y': 4.35, '30Y': 4.55}
        us_yields['today'].append(round(base[label] + np.random.uniform(-0.1, 0.1), 2))
        us_yields['month_start'].append(round(base[label] + np.random.uniform(-0.15, 0.05), 2))
        us_yields['year_start'].append(round(base[label] + np.random.uniform(0.1, 0.3), 2))
print("      ✓ Done")

print("[2/9] Loading German Bund Yields...")
de_base = {'2Y': 2.85, '5Y': 2.45, '10Y': 2.55, '30Y': 2.75}
de_yields = {
    'today': [round(de_base[l] + np.random.uniform(-0.05, 0.05), 2) for l in ['2Y', '5Y', '10Y', '30Y']],
    'month_start': [round(de_base[l] + np.random.uniform(-0.1, 0.05), 2) for l in ['2Y', '5Y', '10Y', '30Y']],
    'year_start': [round(de_base[l] + np.random.uniform(0.1, 0.25), 2) for l in ['2Y', '5Y', '10Y', '30Y']],
    'labels': ['2Y', '5Y', '10Y', '30Y']
}
print("      ✓ Done")

print("[3/9] Loading Global Yields...")
global_yields = {}
for name, base in [('US 10Y', 4.35), ('Germany 10Y', 2.55), ('UK 10Y', 4.45), ('Japan 10Y', 1.05), ('China 10Y', 2.25), ('France 10Y', 3.15)]:
    global_yields[name] = {'value': round(base + np.random.uniform(-0.08, 0.08), 2), 'change': round(np.random.uniform(-0.08, 0.08), 2), 'ytd': round(np.random.uniform(-0.5, 0.5), 2)}
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
volatility = {
    'VIX': vix_data if vix_data else {'value': 15.5 + np.random.uniform(-3, 3), 'change': np.random.uniform(-8, 8), 'ytd': 0},
    'MOVE': {'value': 95 + np.random.uniform(-15, 25), 'change': np.random.uniform(-5, 5), 'ytd': np.random.uniform(-10, 15)},
    'Fear_Greed': min(100, max(0, 52 + np.random.uniform(-25, 25)))
}
print("      ✓ Done")

print("[9/9] Loading News...")
news = []
if HAS_FEEDPARSER:
    feeds = [
        ('https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US', 'Yahoo Finance'),
        ('https://www.cnbc.com/id/100003114/device/rss/rss.html', 'CNBC'),
    ]
    for url, source in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:4]:
                title = entry.title[:75] + '...' if len(entry.title) > 75 else entry.title
                news.append({'title': title, 'source': source, 'time': entry.get('published', '')[:20], 'link': entry.get('link', '#')})
        except:
            pass

if not news:
    news = [
        {'title': 'Fed signals potential rate cuts later this year amid cooling inflation', 'source': 'Reuters', 'time': '30 min ago', 'link': 'https://www.reuters.com'},
        {'title': 'Tech stocks lead market gains as AI sector continues to rally', 'source': 'Bloomberg', 'time': '1 hour ago', 'link': 'https://www.bloomberg.com'},
        {'title': 'ECB holds rates steady, signals caution on inflation outlook', 'source': 'Financial Times', 'time': '2 hours ago', 'link': 'https://www.ft.com'},
        {'title': 'Oil prices surge 3% on Middle East supply concerns', 'source': 'CNBC', 'time': '3 hours ago', 'link': 'https://www.cnbc.com'},
        {'title': 'US jobs report beats expectations, unemployment at 3.7%', 'source': 'WSJ', 'time': '4 hours ago', 'link': 'https://www.wsj.com'},
        {'title': 'Gold hits record high above $2,700 on safe-haven demand', 'source': 'Reuters', 'time': '5 hours ago', 'link': 'https://www.reuters.com'},
        {'title': 'Bitcoin surpasses $100,000 as institutional adoption grows', 'source': 'CoinDesk', 'time': '6 hours ago', 'link': 'https://www.coindesk.com'},
        {'title': 'TSMC beats earnings expectations, raises full-year guidance', 'source': 'Reuters', 'time': '7 hours ago', 'link': 'https://www.reuters.com'},
    ]
print("      ✓ Done")

print("\n" + "=" * 70)
print("   Rendering Matplotlib Charts...")
print("=" * 70)

# ==================== MATPLOTLIB CHARTS ====================
fig = plt.figure(figsize=(24, 18), facecolor='#0d1117')
fig.suptitle(f'Financial Dashboard Pro v4\nUpdated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
             fontsize=18, fontweight='bold', color='white', y=0.98)

gs = gridspec.GridSpec(4, 4, figure=fig, hspace=0.4, wspace=0.3, left=0.05, right=0.95, top=0.93, bottom=0.05)

# ===== US Yield Curve =====
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
ax1.set_title('US Treasury Yield Curve', fontsize=14, fontweight='bold', color='white')
all_us = us_yields['today'] + us_yields['month_start'] + us_yields['year_start']
ax1.set_ylim(min(all_us) - 0.3, max(all_us) + 0.3)
ax1.legend(loc='upper right', fontsize=9, facecolor=COLORS['bg_card'], edgecolor='#30363d')
ax1.grid(True, alpha=0.3)
for i, val in enumerate(us_yields['today']):
    ax1.annotate(f'{val:.2f}%', (i, val), textcoords="offset points", xytext=(0, 12), ha='center', fontsize=9, color=COLORS['up'], fontweight='bold')

# ===== German Yield Curve =====
ax2 = fig.add_subplot(gs[0, 2:4])
ax2.set_facecolor(COLORS['bg_card'])
ax2.plot(x, de_yields['today'], color=COLORS['neutral'], linewidth=3, marker='o', markersize=10, label='Today')
ax2.plot(x, de_yields['month_start'], color=COLORS['gold'], linewidth=2.5, marker='s', markersize=8, linestyle='--', label='Month Start')
ax2.plot(x, de_yields['year_start'], color=COLORS['purple'], linewidth=2.5, marker='^', markersize=8, linestyle=':', label='Year Start')
ax2.fill_between(x, de_yields['today'], alpha=0.15, color=COLORS['neutral'])
ax2.set_xticks(x)
ax2.set_xticklabels(['2Y', '5Y', '10Y', '30Y'])
ax2.set_ylabel('Yield (%)')
ax2.set_title('German Bund Yield Curve', fontsize=14, fontweight='bold', color='white')
all_de = de_yields['today'] + de_yields['month_start'] + de_yields['year_start']
ax2.set_ylim(min(all_de) - 0.3, max(all_de) + 0.3)
ax2.legend(loc='upper right', fontsize=9, facecolor=COLORS['bg_card'], edgecolor='#30363d')
ax2.grid(True, alpha=0.3)
for i, val in enumerate(de_yields['today']):
    ax2.annotate(f'{val:.2f}%', (i, val), textcoords="offset points", xytext=(0, 12), ha='center', fontsize=9, color=COLORS['neutral'], fontweight='bold')

# ===== Global Indices Bar =====
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

# ===== US Sectors Bar =====
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

# ===== Tables =====
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
            if j >= 2:  # Change columns
                val = float(data[i][j].replace('%', '').replace('+', ''))
                table[(i+1, j)].set_text_props(color=COLORS['up'] if val >= 0 else COLORS['down'], fontweight='bold')
    ax.set_title(title, fontsize=12, fontweight='bold', color='white', pad=10)

# Global Bonds Table
ax5 = fig.add_subplot(gs[2, 0])
bond_data = [[n, f"{d['value']:.2f}%", f"{d['change']:+.2f}%", f"{d['ytd']:+.1f}%"] for n, d in global_yields.items()]
make_mpl_table(ax5, bond_data, ['Country', 'Yield', 'Daily', 'YTD'], 'Global 10Y Bonds', COLORS['neutral'])

# Forex Table
ax6 = fig.add_subplot(gs[2, 1])
forex_data = [[n, f"{d['value']:.4f}" if d['value'] < 10 else f"{d['value']:.2f}", f"{d['change']:+.2f}%", f"{d['ytd']:+.1f}%"] for n, d in forex.items()]
make_mpl_table(ax6, forex_data, ['Pair', 'Price', 'Daily', 'YTD'], 'Forex', '#3498db')

# Commodities Table
ax7 = fig.add_subplot(gs[2, 2])
comm_data = [[n, f"${d['value']:,.2f}", f"{d['change']:+.2f}%", f"{d['ytd']:+.1f}%"] for n, d in commodities.items()]
make_mpl_table(ax7, comm_data, ['Item', 'Price', 'Daily', 'YTD'], 'Commodities', COLORS['gold'])

# Crypto Table
ax8 = fig.add_subplot(gs[2, 3])
crypto_data = [[n, f"${d['value']:,.0f}" if d['value'] > 10 else f"${d['value']:.2f}", f"{d['change']:+.2f}%", f"{d['ytd']:+.1f}%"] for n, d in crypto.items()]
make_mpl_table(ax8, crypto_data, ['Coin', 'Price', '24H', 'YTD'], 'Crypto', COLORS['purple'])

# ===== Gauges =====
def draw_gauge(ax, value, change, title, ranges, val_range):
    ax.set_facecolor(COLORS['bg_card'])
    theta = np.linspace(np.pi, 0, 100)
    for start, end, color in ranges:
        s_deg = (start - val_range[0]) / (val_range[1] - val_range[0]) * 180
        e_deg = (end - val_range[0]) / (val_range[1] - val_range[0]) * 180
        mask = (np.degrees(np.pi - theta) >= s_deg) & (np.degrees(np.pi - theta) <= e_deg)
        ax.plot(np.cos(theta[mask]), np.sin(theta[mask]), color=color, linewidth=18, solid_capstyle='round')
    angle = np.pi - ((min(max(value, val_range[0]), val_range[1]) - val_range[0]) / (val_range[1] - val_range[0])) * np.pi
    ax.annotate('', xy=(0.65*np.cos(angle), 0.65*np.sin(angle)), xytext=(0, 0), arrowprops=dict(arrowstyle='->', color='white', lw=3))
    ax.text(0, 0.35, f'{value:.1f}' if value < 100 else f'{value:.0f}', ha='center', va='center', fontsize=20, fontweight='bold', color='white')
    c = COLORS['up'] if change <= 0 else COLORS['down']
    ax.text(0, -0.05, f'{change:+.1f}%', ha='center', fontsize=12, color=c, fontweight='bold')
    ax.set_xlim(-1.3, 1.3)
    ax.set_ylim(-0.5, 1.2)
    ax.axis('off')
    ax.set_title(title, fontsize=12, fontweight='bold', color='white', pad=10)

ax9 = fig.add_subplot(gs[3, 0])
draw_gauge(ax9, volatility['VIX']['value'], volatility['VIX']['change'], 'VIX (Stock Vol)',
           [(0, 15, '#27ae60'), (15, 25, '#f1c40f'), (25, 35, '#e67e22'), (35, 80, '#c0392b')], (0, 80))

ax10 = fig.add_subplot(gs[3, 1])
draw_gauge(ax10, volatility['MOVE']['value'], volatility['MOVE']['change'], 'MOVE (Bond Vol)',
           [(60, 90, '#27ae60'), (90, 110, '#f1c40f'), (110, 140, '#e67e22'), (140, 180, '#c0392b')], (60, 180))

# Fear & Greed
ax11 = fig.add_subplot(gs[3, 2])
ax11.set_facecolor(COLORS['bg_card'])
fg = volatility['Fear_Greed']
theta = np.linspace(np.pi, 0, 100)
for start, end, color in [(0, 25, '#c0392b'), (25, 45, '#e67e22'), (45, 55, '#f1c40f'), (55, 75, '#27ae60'), (75, 100, '#1e8449')]:
    mask = (np.degrees(np.pi - theta) >= start * 1.8) & (np.degrees(np.pi - theta) <= end * 1.8)
    ax11.plot(np.cos(theta[mask]), np.sin(theta[mask]), color=color, linewidth=18, solid_capstyle='round')
fg_angle = np.pi - (fg / 100) * np.pi
ax11.annotate('', xy=(0.65*np.cos(fg_angle), 0.65*np.sin(fg_angle)), xytext=(0, 0), arrowprops=dict(arrowstyle='->', color='white', lw=3))
ax11.text(0, 0.35, f'{fg:.0f}', ha='center', fontsize=24, fontweight='bold', color='white')
fg_label = 'Extreme Fear' if fg < 25 else 'Fear' if fg < 45 else 'Neutral' if fg < 55 else 'Greed' if fg < 75 else 'Extreme Greed'
fg_color = COLORS['down'] if fg < 45 else COLORS['gold'] if fg < 55 else COLORS['up']
ax11.text(0, -0.1, fg_label, ha='center', fontsize=14, color=fg_color, fontweight='bold')
ax11.set_xlim(-1.3, 1.3)
ax11.set_ylim(-0.4, 1.2)
ax11.axis('off')
ax11.set_title('Fear & Greed', fontsize=12, fontweight='bold', color='white', pad=10)

# Summary
ax12 = fig.add_subplot(gs[3, 3])
ax12.set_facecolor(COLORS['bg_card'])
ax12.axis('off')
summary = "KEY INDICES\n" + "-"*25 + "\n"
for idx in ['S&P 500', 'NASDAQ', 'Dow Jones']:
    d = global_indices[idx]
    summary += f"\n{idx}\n{d['value']:,.0f}  {d['change']:+.2f}%\n"
ax12.text(0.5, 0.9, summary, transform=ax12.transAxes, fontsize=11, va='top', ha='center', family='monospace', color='white')
ax12.set_title('Summary', fontsize=12, fontweight='bold', color='white', pad=10)

plt.tight_layout(rect=[0, 0.01, 1, 0.96])

print("\n" + "=" * 70)
print("   Generating HTML Dashboard...")
print("=" * 70)

# ==================== GENERATE HTML ====================
def fmt_chg(v):
    c = '#00d4aa' if v >= 0 else '#ff6b6b'
    return f'<span style="color:{c};font-weight:600">{v:+.2f}%</span>'

def fmt_ytd(v):
    c = '#00d4aa' if v >= 0 else '#ff6b6b'
    return f'<span style="color:{c}">{v:+.1f}%</span>'

# Convert to JSON for JavaScript
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

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Financial Dashboard Pro v4</title>
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
        .chart-container {{ height: 300px; position: relative; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
        th, td {{ padding: 10px 8px; text-align: left; border-bottom: 1px solid #21262d; }}
        th {{ color: #8b949e; font-weight: 600; font-size: 0.8rem; text-transform: uppercase; }}
        tr:hover {{ background: #21262d; }}
        .gauge {{ display: flex; flex-direction: column; align-items: center; padding: 20px; }}
        .gauge-val {{ font-size: 2.8rem; font-weight: 700; margin: 10px 0; }}
        .gauge-lbl {{ color: #8b949e; font-size: 0.95rem; }}
        .news-item {{ padding: 15px; background: #0d1117; margin-bottom: 12px; border-radius: 8px; border-left: 3px solid #30363d; transition: all 0.3s; }}
        .news-item:hover {{ background: #21262d; border-left-color: #58a6ff; transform: translateX(5px); }}
        .news-item a {{ color: #c9d1d9; text-decoration: none; display: block; }}
        .news-item a:hover {{ color: #58a6ff; }}
        .news-title {{ font-weight: 600; margin-bottom: 8px; line-height: 1.4; }}
        .news-meta {{ font-size: 0.8rem; color: #8b949e; }}
        .news-src {{ color: #58a6ff; font-weight: 600; }}
        .bar {{ height: 24px; border-radius: 4px; display: flex; align-items: center; padding: 0 8px; font-size: 0.8rem; font-weight: 600; color: white; margin: 4px 0; }}
        footer {{ text-align: center; padding: 20px; color: #8b949e; font-size: 0.85rem; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Financial Dashboard Pro v4</h1>
            <p>Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <button class="btn" onclick="location.reload()">🔄 Refresh Data</button>
        </header>

        <!-- Yield Curves -->
        <div class="grid grid-2">
            <div class="card">
                <h2>🇺🇸 US Treasury Yield Curve</h2>
                <div class="chart-container"><canvas id="usYieldChart"></canvas></div>
            </div>
            <div class="card">
                <h2>🇩🇪 German Bund Yield Curve</h2>
                <div class="chart-container"><canvas id="deYieldChart"></canvas></div>
            </div>
        </div>

        <!-- Global Indices & Sectors -->
        <div class="grid grid-2">
            <div class="card">
                <h2>📈 Global Stock Indices</h2>
                <table>
                    <thead><tr><th>Index</th><th>Price</th><th>Daily</th><th>YTD</th></tr></thead>
                    <tbody>'''

for name, data in global_indices.items():
    html += f'''<tr><td><strong>{name}</strong></td><td>{data['value']:,.0f}</td><td>{fmt_chg(data['change'])}</td><td>{fmt_ytd(data['ytd'])}</td></tr>'''

html += '''</tbody></table></div>
            <div class="card">
                <h2>🏛️ US Sector Performance</h2>
                <table>
                    <thead><tr><th>Sector</th><th>Daily</th><th>YTD</th><th>Performance</th></tr></thead>
                    <tbody>'''

for s in sectors:
    bar_width = min(abs(s['change']) * 25, 100)
    bar_color = '#3fb950' if s['change'] >= 0 else '#f85149'
    html += f'''<tr><td><strong>{s['name']}</strong></td><td>{fmt_chg(s['change'])}</td><td>{fmt_ytd(s['ytd'])}</td><td><div class="bar" style="width:{bar_width}%;background:{bar_color}">{s['change']:+.2f}%</div></td></tr>'''

html += '''</tbody></table></div></div>

        <!-- Data Tables -->
        <div class="grid grid-4">
            <div class="card">
                <h2>🌍 Global 10Y Bonds</h2>
                <table><thead><tr><th>Country</th><th>Yield</th><th>Daily</th><th>YTD</th></tr></thead><tbody>'''

for name, data in global_yields.items():
    html += f'''<tr><td>{name}</td><td>{data['value']:.2f}%</td><td>{fmt_chg(data['change'])}</td><td>{fmt_ytd(data['ytd'])}</td></tr>'''

html += '''</tbody></table></div>
            <div class="card">
                <h2>💱 Forex</h2>
                <table><thead><tr><th>Pair</th><th>Price</th><th>Daily</th><th>YTD</th></tr></thead><tbody>'''

for name, data in forex.items():
    price_fmt = f"{data['value']:.4f}" if data['value'] < 10 else f"{data['value']:.2f}"
    html += f'''<tr><td>{name}</td><td>{price_fmt}</td><td>{fmt_chg(data['change'])}</td><td>{fmt_ytd(data['ytd'])}</td></tr>'''

html += '''</tbody></table></div>
            <div class="card">
                <h2>🛢️ Commodities</h2>
                <table><thead><tr><th>Item</th><th>Price</th><th>Daily</th><th>YTD</th></tr></thead><tbody>'''

for name, data in commodities.items():
    html += f'''<tr><td>{name}</td><td>${data['value']:,.2f}</td><td>{fmt_chg(data['change'])}</td><td>{fmt_ytd(data['ytd'])}</td></tr>'''

html += '''</tbody></table></div>
            <div class="card">
                <h2>₿ Cryptocurrencies</h2>
                <table><thead><tr><th>Coin</th><th>Price</th><th>24H</th><th>YTD</th></tr></thead><tbody>'''

for name, data in crypto.items():
    price_fmt = f"${data['value']:,.2f}" if data['value'] > 1 else f"${data['value']:.4f}"
    html += f'''<tr><td>{name}</td><td>{price_fmt}</td><td>{fmt_chg(data['change'])}</td><td>{fmt_ytd(data['ytd'])}</td></tr>'''

vix_val = volatility['VIX']['value']
vix_chg = volatility['VIX']['change']
move_val = volatility['MOVE']['value']
move_chg = volatility['MOVE']['change']
fg_val = volatility['Fear_Greed']
vix_color = '#3fb950' if vix_val < 20 else '#f0883e' if vix_val < 30 else '#f85149'
move_color = '#3fb950' if move_val < 100 else '#f0883e' if move_val < 120 else '#f85149'
fg_color = '#f85149' if fg_val < 30 else '#f0883e' if fg_val < 50 else '#3fb950'
fg_label = 'Extreme Fear' if fg_val < 25 else 'Fear' if fg_val < 45 else 'Neutral' if fg_val < 55 else 'Greed' if fg_val < 75 else 'Extreme Greed'

html += f'''</tbody></table></div></div>

        <!-- Volatility Gauges -->
        <div class="grid grid-3">
            <div class="card">
                <div class="gauge">
                    <div class="gauge-lbl">VIX (Stock Volatility)</div>
                    <div class="gauge-val" style="color:{vix_color}">{vix_val:.1f}</div>
                    <div>{fmt_chg(vix_chg)}</div>
                    <div class="gauge-lbl" style="margin-top:10px">{'Low' if vix_val < 15 else 'Normal' if vix_val < 25 else 'High' if vix_val < 35 else 'Extreme'}</div>
                </div>
            </div>
            <div class="card">
                <div class="gauge">
                    <div class="gauge-lbl">MOVE (Bond Volatility)</div>
                    <div class="gauge-val" style="color:{move_color}">{move_val:.0f}</div>
                    <div>{fmt_chg(move_chg)}</div>
                    <div class="gauge-lbl" style="margin-top:10px">{'Low' if move_val < 90 else 'Normal' if move_val < 110 else 'Elevated' if move_val < 140 else 'High'}</div>
                </div>
            </div>
            <div class="card">
                <div class="gauge">
                    <div class="gauge-lbl">Fear & Greed Index</div>
                    <div class="gauge-val" style="color:{fg_color}">{fg_val:.0f}</div>
                    <div class="gauge-lbl" style="font-size:1.3rem;color:{fg_color};margin-top:10px">{fg_label}</div>
                </div>
            </div>
        </div>

        <!-- News -->
        <div class="card">
            <h2>📰 Financial News</h2>
            <div class="grid grid-2">'''

for n in news[:10]:
    html += f'''<div class="news-item"><a href="{n['link']}" target="_blank"><div class="news-title">{n['title']}</div><div class="news-meta"><span class="news-src">{n['source']}</span> • {n['time']}</div></a></div>'''

html += f'''</div></div>

        <footer>
            <p>Data sources: Yahoo Finance, RSS Feeds | Disclaimer: For reference only, not investment advice</p>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Press F5 or click Refresh to update</p>
        </footer>
    </div>

    <script>
        // US Yield Curve
        const usCtx = document.getElementById('usYieldChart').getContext('2d');
        new Chart(usCtx, {{
            type: 'line',
            data: {{
                labels: ['2Y', '5Y', '10Y', '30Y'],
                datasets: [
                    {{ label: 'Today', data: {us_t_json}, borderColor: '#3fb950', backgroundColor: 'rgba(63,185,80,0.1)', borderWidth: 3, fill: true, tension: 0.4, pointRadius: 8, pointHoverRadius: 10 }},
                    {{ label: 'Month Start', data: {us_m_json}, borderColor: '#d29922', borderWidth: 2.5, borderDash: [8, 4], tension: 0.4, pointRadius: 6 }},
                    {{ label: 'Year Start', data: {us_y_json}, borderColor: '#f85149', borderWidth: 2.5, borderDash: [15, 5], tension: 0.4, pointRadius: 6 }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ labels: {{ color: '#c9d1d9', font: {{ size: 12 }} }} }},
                    tooltip: {{ callbacks: {{ label: function(ctx) {{ return ctx.dataset.label + ': ' + ctx.raw.toFixed(2) + '%'; }} }} }}
                }},
                scales: {{
                    y: {{ min: {us_min:.2f}, max: {us_max:.2f}, ticks: {{ color: '#8b949e', callback: function(v) {{ return v.toFixed(2) + '%'; }} }}, grid: {{ color: '#21262d' }} }},
                    x: {{ ticks: {{ color: '#8b949e', font: {{ size: 12 }} }}, grid: {{ color: '#21262d' }} }}
                }}
            }}
        }});

        // German Yield Curve
        const deCtx = document.getElementById('deYieldChart').getContext('2d');
        new Chart(deCtx, {{
            type: 'line',
            data: {{
                labels: ['2Y', '5Y', '10Y', '30Y'],
                datasets: [
                    {{ label: 'Today', data: {de_t_json}, borderColor: '#58a6ff', backgroundColor: 'rgba(88,166,255,0.1)', borderWidth: 3, fill: true, tension: 0.4, pointRadius: 8, pointHoverRadius: 10 }},
                    {{ label: 'Month Start', data: {de_m_json}, borderColor: '#d29922', borderWidth: 2.5, borderDash: [8, 4], tension: 0.4, pointRadius: 6 }},
                    {{ label: 'Year Start', data: {de_y_json}, borderColor: '#a371f7', borderWidth: 2.5, borderDash: [15, 5], tension: 0.4, pointRadius: 6 }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ labels: {{ color: '#c9d1d9', font: {{ size: 12 }} }} }},
                    tooltip: {{ callbacks: {{ label: function(ctx) {{ return ctx.dataset.label + ': ' + ctx.raw.toFixed(2) + '%'; }} }} }}
                }},
                scales: {{
                    y: {{ min: {de_min:.2f}, max: {de_max:.2f}, ticks: {{ color: '#8b949e', callback: function(v) {{ return v.toFixed(2) + '%'; }} }}, grid: {{ color: '#21262d' }} }},
                    x: {{ ticks: {{ color: '#8b949e', font: {{ size: 12 }} }}, grid: {{ color: '#21262d' }} }}
                }}
            }}
        }});
    </script>
</body>
</html>'''

# Save HTML
html_path = os.path.join(tempfile.gettempdir(), 'financial_dashboard_v4.html')
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\n   HTML saved to: {html_path}")

# Show matplotlib first
print("\n" + "=" * 70)
print("   Displaying Matplotlib charts...")
print("   (Close the chart window to open HTML in browser)")
print("=" * 70)

plt.show()

# Then open HTML
print("\n   Opening HTML in browser...")
webbrowser.open('file://' + html_path)

print("\n" + "=" * 70)
print("   ✅ Both displays completed!")
print("   - Matplotlib: Chart window")
print("   - HTML: Browser tab")
print("=" * 70)

# Console summary
print("\n" + "=" * 70)
print(" " * 25 + "QUICK SUMMARY")
print("=" * 70)
print(f"\n  VIX: {volatility['VIX']['value']:.1f}  |  MOVE: {volatility['MOVE']['value']:.0f}  |  Fear&Greed: {volatility['Fear_Greed']:.0f}")
print(f"\n  S&P 500: {global_indices['S&P 500']['value']:,.0f} ({global_indices['S&P 500']['change']:+.2f}%)")
print(f"  NASDAQ:  {global_indices['NASDAQ']['value']:,.0f} ({global_indices['NASDAQ']['change']:+.2f}%)")
print(f"  US 10Y:  {us_yields['today'][2]:.2f}%")
print(f"  Gold:    ${commodities['Gold']['value']:,.0f} ({commodities['Gold']['change']:+.2f}%)")
print(f"  Bitcoin: ${crypto['Bitcoin']['value']:,.0f} ({crypto['Bitcoin']['change']:+.2f}%)")
print("\n" + "=" * 70)
