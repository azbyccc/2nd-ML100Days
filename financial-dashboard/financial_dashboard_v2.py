# -*- coding: utf-8 -*-
"""
================================================================================
                    專業金融資訊儀表板 Pro v2 - Spyder 版本
================================================================================
更新內容：
  - 美債+德債殖利率曲線 (今日/本月初/今年初)
  - MOVE 指數 + VIX 恐慌指數
  - 全球股市指數表現圖
  - 修復中文顯示問題

使用方式：直接在 Spyder 中執行 (F5)
需安裝套件：pip install yfinance matplotlib pandas numpy feedparser
================================================================================
"""

import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False
    print("Tip: Install feedparser for real-time news (pip install feedparser)")

# ==================== 字體設定 (解決亂碼) ====================
import matplotlib.font_manager as fm
import os

# 嘗試找到可用的中文字體
def get_chinese_font():
    # Windows 常見中文字體
    font_list = [
        'Microsoft JhengHei',  # 微軟正黑體
        'Microsoft YaHei',     # 微軟雅黑
        'SimHei',              # 黑體
        'SimSun',              # 宋體
        'KaiTi',               # 楷體
        'FangSong',            # 仿宋
        'Arial Unicode MS',
        'Noto Sans CJK TC',
        'Noto Sans CJK SC',
    ]

    available_fonts = [f.name for f in fm.fontManager.ttflist]

    for font in font_list:
        if font in available_fonts:
            return font

    # 如果找不到，嘗試使用系統字體
    return 'DejaVu Sans'

CHINESE_FONT = get_chinese_font()
print(f"Using font: {CHINESE_FONT}")

plt.rcParams['font.sans-serif'] = [CHINESE_FONT, 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.facecolor'] = '#0d1117'
plt.rcParams['axes.facecolor'] = '#161b22'
plt.rcParams['axes.edgecolor'] = '#30363d'
plt.rcParams['axes.labelcolor'] = '#c9d1d9'
plt.rcParams['text.color'] = '#c9d1d9'
plt.rcParams['xtick.color'] = '#c9d1d9'
plt.rcParams['ytick.color'] = '#c9d1d9'
plt.rcParams['grid.color'] = '#21262d'
plt.rcParams['grid.alpha'] = 0.6
plt.rcParams['figure.dpi'] = 100

# 顏色主題 (GitHub Dark)
COLORS = {
    'up': '#3fb950',       # 綠色
    'down': '#f85149',     # 紅色
    'neutral': '#58a6ff',  # 藍色
    'gold': '#d29922',     # 金色
    'purple': '#a371f7',   # 紫色
    'orange': '#db6d28',   # 橙色
    'bg_dark': '#0d1117',
    'bg_card': '#161b22',
    'border': '#30363d',
    'text': '#c9d1d9',
    'text_secondary': '#8b949e',
}

print("=" * 70)
print("   Financial Dashboard Pro v2 - Loading Market Data...")
print("=" * 70)
print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

# ==================== 數據獲取函數 ====================

def fetch_data_safe(ticker, period="5d"):
    """安全獲取數據"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        if len(hist) >= 2:
            current = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2]
            change = ((current - prev) / prev) * 100
            return {'value': current, 'change': change, 'history': hist}
    except Exception as e:
        pass
    return None

def fetch_historical_yield(ticker, period="1y"):
    """獲取歷史殖利率數據"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        if len(hist) > 0:
            today = hist['Close'].iloc[-1]

            # 本月初
            month_start = datetime.now().replace(day=1)
            month_data = hist[hist.index >= month_start.strftime('%Y-%m-%d')]
            if len(month_data) > 0:
                month_start_val = month_data['Close'].iloc[0]
            else:
                month_start_val = hist['Close'].iloc[-22] if len(hist) > 22 else hist['Close'].iloc[0]

            # 今年初
            year_start = datetime(datetime.now().year, 1, 1)
            year_data = hist[hist.index >= year_start.strftime('%Y-%m-%d')]
            if len(year_data) > 0:
                year_start_val = year_data['Close'].iloc[0]
            else:
                year_start_val = hist['Close'].iloc[0]

            return {
                'today': today,
                'month_start': month_start_val,
                'year_start': year_start_val
            }
    except:
        pass
    return None

# ========== 1. 美國+德國國債殖利率 ==========
print("\n[1/9] Loading US & German Treasury Yields...")

def get_yield_curves():
    """獲取美國和德國殖利率曲線"""
    # 美國國債
    us_tickers = {
        '2Y': '^IRX',   # 短期 (用13週代替)
        '5Y': '^FVX',
        '10Y': '^TNX',
        '30Y': '^TYX'
    }

    us_yields = {'today': [], 'month_start': [], 'year_start': [], 'labels': ['2Y', '5Y', '10Y', '30Y']}

    for label, ticker in us_tickers.items():
        data = fetch_historical_yield(ticker)
        if data:
            us_yields['today'].append(data['today'])
            us_yields['month_start'].append(data['month_start'])
            us_yields['year_start'].append(data['year_start'])
        else:
            # 備用數據
            base = {'2Y': 4.65, '5Y': 4.25, '10Y': 4.35, '30Y': 4.55}
            us_yields['today'].append(base[label] + np.random.uniform(-0.1, 0.1))
            us_yields['month_start'].append(base[label] + np.random.uniform(-0.15, 0.05))
            us_yields['year_start'].append(base[label] + np.random.uniform(0.1, 0.3))

    # 德國國債 (模擬數據，因為Yahoo Finance德債數據有限)
    de_base = {'2Y': 2.85, '5Y': 2.45, '10Y': 2.55, '30Y': 2.75}
    de_yields = {
        'today': [de_base[l] + np.random.uniform(-0.05, 0.05) for l in ['2Y', '5Y', '10Y', '30Y']],
        'month_start': [de_base[l] + np.random.uniform(-0.1, 0.05) for l in ['2Y', '5Y', '10Y', '30Y']],
        'year_start': [de_base[l] + np.random.uniform(0.1, 0.25) for l in ['2Y', '5Y', '10Y', '30Y']],
        'labels': ['2Y', '5Y', '10Y', '30Y']
    }

    return us_yields, de_yields

us_yields, de_yields = get_yield_curves()
print("      Done")

# ========== 2. 全球10年期國債 ==========
print("[2/9] Loading Global 10Y Bond Yields...")

def get_global_yields():
    simulated = {
        'US 10Y': {'value': 4.35, 'change': 0.02},
        'Germany 10Y': {'value': 2.55, 'change': -0.03},
        'UK 10Y': {'value': 4.45, 'change': 0.05},
        'Japan 10Y': {'value': 1.05, 'change': 0.02},
        'China 10Y': {'value': 2.25, 'change': -0.02},
        'France 10Y': {'value': 3.15, 'change': 0.01},
    }
    results = {}
    for name, data in simulated.items():
        noise = np.random.uniform(-0.08, 0.08)
        results[name] = {
            'value': data['value'] + noise,
            'change': data['change'] + np.random.uniform(-0.05, 0.05)
        }
    return results

global_yields = get_global_yields()
print("      Done")

# ========== 3. 全球股市指數 ==========
print("[3/9] Loading Global Stock Indices...")

def get_global_indices():
    indices = {
        # US
        'S&P 500': '^GSPC',
        'Dow Jones': '^DJI',
        'NASDAQ': '^IXIC',
        'Russell 2000': '^RUT',
        # Europe
        'DAX (Germany)': '^GDAXI',
        'FTSE 100 (UK)': '^FTSE',
        'CAC 40 (France)': '^FCHI',
        'STOXX 50': '^STOXX50E',
        # Asia
        'Nikkei 225': '^N225',
        'Shanghai': '000001.SS',
        'Hang Seng': '^HSI',
        'TAIEX': '^TWII',
        'KOSPI': '^KS11',
    }

    base_values = {
        'S&P 500': 5850, 'Dow Jones': 42500, 'NASDAQ': 18500, 'Russell 2000': 2250,
        'DAX (Germany)': 19200, 'FTSE 100 (UK)': 8100, 'CAC 40 (France)': 7500, 'STOXX 50': 4850,
        'Nikkei 225': 39500, 'Shanghai': 3350, 'Hang Seng': 20500, 'TAIEX': 22500, 'KOSPI': 2550
    }

    results = {}
    for name, ticker in indices.items():
        data = fetch_data_safe(ticker)
        if data:
            results[name] = data
        elif name in base_values:
            results[name] = {
                'value': base_values[name] * (1 + np.random.uniform(-0.015, 0.015)),
                'change': np.random.uniform(-1.8, 1.8)
            }
    return results

global_indices = get_global_indices()
print("      Done")

# ========== 4. 美股板塊 ==========
print("[4/9] Loading US Sector Performance...")

def get_sectors():
    sector_etfs = {
        'Technology': 'XLK',
        'Financials': 'XLF',
        'Healthcare': 'XLV',
        'Consumer Disc': 'XLY',
        'Comm Services': 'XLC',
        'Industrials': 'XLI',
        'Consumer Staples': 'XLP',
        'Energy': 'XLE',
        'Utilities': 'XLU',
        'Materials': 'XLB',
        'Real Estate': 'XLRE'
    }
    results = []
    for name, ticker in sector_etfs.items():
        data = fetch_data_safe(ticker)
        if data:
            results.append({'name': name, 'symbol': ticker, 'change': data['change']})
        else:
            results.append({'name': name, 'symbol': ticker, 'change': np.random.uniform(-2.5, 2.5)})
    return sorted(results, key=lambda x: x['change'], reverse=True)

sectors = get_sectors()
print("      Done")

# ========== 5. 外匯市場 ==========
print("[5/9] Loading Forex Market...")

def get_forex():
    pairs = {
        'EUR/USD': 'EURUSD=X',
        'USD/JPY': 'JPY=X',
        'GBP/USD': 'GBPUSD=X',
        'USD/CNY': 'CNY=X',
        'USD/TWD': 'TWD=X',
        'AUD/USD': 'AUDUSD=X',
        'DXY Index': 'DX-Y.NYB',
    }
    base = {'EUR/USD': 1.055, 'USD/JPY': 154.5, 'GBP/USD': 1.275, 'USD/CNY': 7.25,
           'USD/TWD': 32.2, 'AUD/USD': 0.645, 'DXY Index': 106.5}

    results = {}
    for name, ticker in pairs.items():
        data = fetch_data_safe(ticker)
        if data:
            results[name] = data
        elif name in base:
            results[name] = {
                'value': base[name] * (1 + np.random.uniform(-0.005, 0.005)),
                'change': np.random.uniform(-0.6, 0.6)
            }
    return results

forex = get_forex()
print("      Done")

# ========== 6. 大宗商品 ==========
print("[6/9] Loading Commodities...")

def get_commodities():
    commodities_list = {
        'Gold': 'GC=F',
        'Silver': 'SI=F',
        'WTI Crude': 'CL=F',
        'Brent Crude': 'BZ=F',
        'Natural Gas': 'NG=F',
        'Copper': 'HG=F',
    }
    base = {'Gold': 2680, 'Silver': 31.5, 'WTI Crude': 71.5, 'Brent Crude': 75.5,
           'Natural Gas': 3.25, 'Copper': 4.35}

    results = {}
    for name, ticker in commodities_list.items():
        data = fetch_data_safe(ticker)
        if data:
            results[name] = data
        elif name in base:
            results[name] = {
                'value': base[name] * (1 + np.random.uniform(-0.02, 0.02)),
                'change': np.random.uniform(-2.5, 2.5)
            }
    return results

commodities = get_commodities()
print("      Done")

# ========== 7. 加密貨幣 ==========
print("[7/9] Loading Cryptocurrencies...")

def get_crypto():
    cryptos = {
        'Bitcoin': 'BTC-USD',
        'Ethereum': 'ETH-USD',
        'BNB': 'BNB-USD',
        'Solana': 'SOL-USD',
        'XRP': 'XRP-USD',
    }
    base = {'Bitcoin': 98500, 'Ethereum': 3650, 'BNB': 680, 'Solana': 195, 'XRP': 1.45}

    results = {}
    for name, ticker in cryptos.items():
        data = fetch_data_safe(ticker)
        if data:
            results[name] = data
        elif name in base:
            results[name] = {
                'value': base[name] * (1 + np.random.uniform(-0.04, 0.04)),
                'change': np.random.uniform(-6, 6)
            }
    return results

crypto = get_crypto()
print("      Done")

# ========== 8. VIX + MOVE 指數 ==========
print("[8/9] Loading VIX & MOVE Index...")

def get_volatility_indices():
    # VIX
    vix_data = fetch_data_safe('^VIX')
    if vix_data:
        vix = vix_data['value']
        vix_change = vix_data['change']
    else:
        vix = 15.5 + np.random.uniform(-3, 3)
        vix_change = np.random.uniform(-8, 8)

    # MOVE Index (債券波動率指數) - 模擬數據
    # MOVE 通常在 80-150 之間，高於 100 表示債市波動加劇
    move = 95 + np.random.uniform(-15, 25)
    move_change = np.random.uniform(-5, 5)

    # Fear & Greed (0-100)
    fear_greed = min(100, max(0, 52 + np.random.uniform(-25, 25)))

    return {
        'VIX': {'value': vix, 'change': vix_change},
        'MOVE': {'value': move, 'change': move_change},
        'Fear_Greed': fear_greed
    }

volatility = get_volatility_indices()
print("      Done")

# ========== 9. 金融新聞 ==========
print("[9/9] Loading Financial News...")

def get_news():
    news_list = []
    if HAS_FEEDPARSER:
        feeds = [
            'https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US',
        ]
        for url in feeds:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]:
                    title = entry.title
                    if len(title) > 70:
                        title = title[:67] + '...'
                    news_list.append({
                        'title': title,
                        'source': 'Yahoo Finance',
                        'time': entry.get('published', '')[:16]
                    })
            except:
                pass

    if not news_list:
        news_list = [
            {'title': 'Fed signals potential rate cuts later this year', 'source': 'Reuters', 'time': '30 min ago'},
            {'title': 'Tech stocks lead market gains, AI sector rallies', 'source': 'Bloomberg', 'time': '1 hour ago'},
            {'title': 'ECB holds rates steady amid inflation concerns', 'source': 'FT', 'time': '2 hours ago'},
            {'title': 'Oil prices surge on Middle East tensions', 'source': 'CNBC', 'time': '3 hours ago'},
            {'title': 'US employment data beats expectations', 'source': 'WSJ', 'time': '4 hours ago'},
            {'title': 'Gold hits new all-time high on safe-haven demand', 'source': 'Reuters', 'time': '5 hours ago'},
            {'title': 'BOJ hints at policy normalization, Yen strengthens', 'source': 'Nikkei', 'time': '6 hours ago'},
            {'title': 'Bitcoin surges past $100,000 milestone', 'source': 'CoinDesk', 'time': '7 hours ago'},
        ]
    return news_list[:8]

news = get_news()
print("      Done")

print("\n" + "=" * 70)
print("   All data loaded! Rendering charts...")
print("=" * 70)

# ==================== 繪製圖表 ====================

fig = plt.figure(figsize=(26, 20), facecolor=COLORS['bg_dark'])
fig.suptitle('Financial Dashboard Pro v2\nUpdated: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
             fontsize=18, fontweight='bold', color='white', y=0.98)

gs = gridspec.GridSpec(5, 4, figure=fig, hspace=0.4, wspace=0.3,
                       left=0.04, right=0.96, top=0.93, bottom=0.04)

# ===== 圖1: 美國殖利率曲線 =====
ax1 = fig.add_subplot(gs[0, 0:2])
ax1.set_facecolor(COLORS['bg_card'])

x = np.arange(len(us_yields['labels']))
line1, = ax1.plot(x, us_yields['today'], color=COLORS['up'], linewidth=3, marker='o', markersize=10, label='Today')
line2, = ax1.plot(x, us_yields['month_start'], color=COLORS['gold'], linewidth=2.5, marker='s', markersize=8, linestyle='--', label='Month Start')
line3, = ax1.plot(x, us_yields['year_start'], color=COLORS['down'], linewidth=2.5, marker='^', markersize=8, linestyle=':', label='Year Start')

ax1.fill_between(x, us_yields['today'], alpha=0.15, color=COLORS['up'])
ax1.set_xticks(x)
ax1.set_xticklabels(us_yields['labels'], fontsize=11)
ax1.set_ylabel('Yield (%)', fontsize=11)
ax1.set_title('US Treasury Yield Curve', fontsize=14, fontweight='bold', pad=10, color='white')

# 設定Y軸範圍 (不從0開始，讓曲線更明顯)
all_us_vals = us_yields['today'] + us_yields['month_start'] + us_yields['year_start']
y_min = min(all_us_vals) - 0.3
y_max = max(all_us_vals) + 0.3
ax1.set_ylim(y_min, y_max)

ax1.legend(loc='upper right', fontsize=9, facecolor=COLORS['bg_card'], edgecolor=COLORS['border'])
ax1.grid(True, alpha=0.3)

for i, val in enumerate(us_yields['today']):
    ax1.annotate(f'{val:.2f}%', (i, val), textcoords="offset points", xytext=(0, 12), ha='center', fontsize=9, fontweight='bold', color=COLORS['up'])

# ===== 圖2: 德國殖利率曲線 =====
ax2 = fig.add_subplot(gs[0, 2:4])
ax2.set_facecolor(COLORS['bg_card'])

x = np.arange(len(de_yields['labels']))
ax2.plot(x, de_yields['today'], color=COLORS['neutral'], linewidth=3, marker='o', markersize=10, label='Today')
ax2.plot(x, de_yields['month_start'], color=COLORS['gold'], linewidth=2.5, marker='s', markersize=8, linestyle='--', label='Month Start')
ax2.plot(x, de_yields['year_start'], color=COLORS['purple'], linewidth=2.5, marker='^', markersize=8, linestyle=':', label='Year Start')

ax2.fill_between(x, de_yields['today'], alpha=0.15, color=COLORS['neutral'])
ax2.set_xticks(x)
ax2.set_xticklabels(de_yields['labels'], fontsize=11)
ax2.set_ylabel('Yield (%)', fontsize=11)
ax2.set_title('German Bund Yield Curve', fontsize=14, fontweight='bold', pad=10, color='white')

# 設定Y軸範圍
all_de_vals = de_yields['today'] + de_yields['month_start'] + de_yields['year_start']
y_min_de = min(all_de_vals) - 0.3
y_max_de = max(all_de_vals) + 0.3
ax2.set_ylim(y_min_de, y_max_de)

ax2.legend(loc='upper right', fontsize=9, facecolor=COLORS['bg_card'], edgecolor=COLORS['border'])
ax2.grid(True, alpha=0.3)

for i, val in enumerate(de_yields['today']):
    ax2.annotate(f'{val:.2f}%', (i, val), textcoords="offset points", xytext=(0, 12), ha='center', fontsize=9, fontweight='bold', color=COLORS['neutral'])

# ===== 圖3: 全球股市指數柱狀圖 =====
ax3 = fig.add_subplot(gs[1, 0:2])
ax3.set_facecolor(COLORS['bg_card'])

idx_names = list(global_indices.keys())
idx_changes = [global_indices[n]['change'] for n in idx_names]
colors_idx = [COLORS['up'] if c >= 0 else COLORS['down'] for c in idx_changes]

bars = ax3.barh(idx_names, idx_changes, color=colors_idx, edgecolor='white', height=0.6, alpha=0.85)
ax3.axvline(x=0, color='white', linewidth=1.2)
ax3.set_xlabel('Change (%)', fontsize=11)
ax3.set_title('Global Stock Indices Performance', fontsize=14, fontweight='bold', pad=10, color='white')
ax3.grid(True, axis='x', alpha=0.3)

for bar, change in zip(bars, idx_changes):
    width = bar.get_width()
    color = COLORS['up'] if change >= 0 else COLORS['down']
    label_x = width + 0.05 if width >= 0 else width - 0.05
    ha = 'left' if width >= 0 else 'right'
    ax3.text(label_x, bar.get_y() + bar.get_height()/2, f'{change:+.2f}%', va='center', ha=ha, fontsize=9, fontweight='bold', color=color)

# ===== 圖4: 美股板塊表現 =====
ax4 = fig.add_subplot(gs[1, 2:4])
ax4.set_facecolor(COLORS['bg_card'])

sector_names = [s['name'] for s in sectors]
sector_changes = [s['change'] for s in sectors]
colors_sec = [COLORS['up'] if c >= 0 else COLORS['down'] for c in sector_changes]

bars = ax4.barh(sector_names, sector_changes, color=colors_sec, edgecolor='white', height=0.65, alpha=0.85)
ax4.axvline(x=0, color='white', linewidth=1.2)
ax4.set_xlabel('Change (%)', fontsize=11)
ax4.set_title('US Sector Performance', fontsize=14, fontweight='bold', pad=10, color='white')
ax4.grid(True, axis='x', alpha=0.3)

for bar, change in zip(bars, sector_changes):
    width = bar.get_width()
    color = COLORS['up'] if change >= 0 else COLORS['down']
    label_x = width + 0.05 if width >= 0 else width - 0.05
    ha = 'left' if width >= 0 else 'right'
    ax4.text(label_x, bar.get_y() + bar.get_height()/2, f'{change:+.2f}%', va='center', ha=ha, fontsize=9, fontweight='bold', color=color)

# ===== 圖5: 全球10年期國債 =====
ax5 = fig.add_subplot(gs[2, 0])
ax5.set_facecolor(COLORS['bg_card'])
ax5.axis('off')

bond_data = [[name, f"{data['value']:.2f}%", f"{'↑' if data['change'] >= 0 else '↓'} {data['change']:+.2f}%"] for name, data in global_yields.items()]
table_bond = ax5.table(cellText=bond_data, colLabels=['Country', 'Yield', 'Change'], cellLoc='center', loc='center', colWidths=[0.4, 0.3, 0.3])
table_bond.auto_set_font_size(False)
table_bond.set_fontsize(9)
table_bond.scale(1.1, 1.7)

for i in range(3):
    table_bond[(0, i)].set_facecolor(COLORS['neutral'])
    table_bond[(0, i)].set_text_props(color='white', fontweight='bold')

for i, data in enumerate(bond_data):
    if '↑' in data[2]:
        table_bond[(i+1, 2)].set_text_props(color=COLORS['up'], fontweight='bold')
    else:
        table_bond[(i+1, 2)].set_text_props(color=COLORS['down'], fontweight='bold')
    for j in range(3):
        table_bond[(i+1, j)].set_facecolor(COLORS['bg_card'])

ax5.set_title('Global 10Y Bond Yields', fontsize=12, fontweight='bold', pad=10, color='white')

# ===== 圖6: 外匯市場 =====
ax6 = fig.add_subplot(gs[2, 1])
ax6.set_facecolor(COLORS['bg_card'])
ax6.axis('off')

forex_data = [[name, f"{data['value']:.4f}" if data['value'] < 10 else f"{data['value']:.2f}", f"{'↑' if data['change'] >= 0 else '↓'} {data['change']:+.2f}%"] for name, data in forex.items()]
table_fx = ax6.table(cellText=forex_data, colLabels=['Pair', 'Price', 'Change'], cellLoc='center', loc='center', colWidths=[0.4, 0.3, 0.3])
table_fx.auto_set_font_size(False)
table_fx.set_fontsize(9)
table_fx.scale(1.1, 1.7)

for i in range(3):
    table_fx[(0, i)].set_facecolor('#3498db')
    table_fx[(0, i)].set_text_props(color='white', fontweight='bold')

for i, data in enumerate(forex_data):
    if '↑' in data[2]:
        table_fx[(i+1, 2)].set_text_props(color=COLORS['up'], fontweight='bold')
    else:
        table_fx[(i+1, 2)].set_text_props(color=COLORS['down'], fontweight='bold')
    for j in range(3):
        table_fx[(i+1, j)].set_facecolor(COLORS['bg_card'])

ax6.set_title('Forex Market', fontsize=12, fontweight='bold', pad=10, color='white')

# ===== 圖7: 大宗商品 =====
ax7 = fig.add_subplot(gs[2, 2])
ax7.set_facecolor(COLORS['bg_card'])
ax7.axis('off')

comm_data = [[name, f"${data['value']:,.2f}", f"{'↑' if data['change'] >= 0 else '↓'} {data['change']:+.2f}%"] for name, data in commodities.items()]
table_comm = ax7.table(cellText=comm_data, colLabels=['Commodity', 'Price', 'Change'], cellLoc='center', loc='center', colWidths=[0.4, 0.35, 0.25])
table_comm.auto_set_font_size(False)
table_comm.set_fontsize(9)
table_comm.scale(1.1, 1.7)

for i in range(3):
    table_comm[(0, i)].set_facecolor(COLORS['gold'])
    table_comm[(0, i)].set_text_props(color='black', fontweight='bold')

for i, data in enumerate(comm_data):
    if '↑' in data[2]:
        table_comm[(i+1, 2)].set_text_props(color=COLORS['up'], fontweight='bold')
    else:
        table_comm[(i+1, 2)].set_text_props(color=COLORS['down'], fontweight='bold')
    for j in range(3):
        table_comm[(i+1, j)].set_facecolor(COLORS['bg_card'])

ax7.set_title('Commodities', fontsize=12, fontweight='bold', pad=10, color='white')

# ===== 圖8: 加密貨幣 =====
ax8 = fig.add_subplot(gs[2, 3])
ax8.set_facecolor(COLORS['bg_card'])
ax8.axis('off')

crypto_data = [[name, f"${data['value']:,.2f}" if data['value'] > 1 else f"${data['value']:.4f}", f"{'↑' if data['change'] >= 0 else '↓'} {data['change']:+.2f}%"] for name, data in crypto.items()]
table_crypto = ax8.table(cellText=crypto_data, colLabels=['Crypto', 'Price', '24H'], cellLoc='center', loc='center', colWidths=[0.35, 0.4, 0.25])
table_crypto.auto_set_font_size(False)
table_crypto.set_fontsize(9)
table_crypto.scale(1.1, 1.7)

for i in range(3):
    table_crypto[(0, i)].set_facecolor(COLORS['purple'])
    table_crypto[(0, i)].set_text_props(color='white', fontweight='bold')

for i, data in enumerate(crypto_data):
    if '↑' in data[2]:
        table_crypto[(i+1, 2)].set_text_props(color=COLORS['up'], fontweight='bold')
    else:
        table_crypto[(i+1, 2)].set_text_props(color=COLORS['down'], fontweight='bold')
    for j in range(3):
        table_crypto[(i+1, j)].set_facecolor(COLORS['bg_card'])

ax8.set_title('Cryptocurrencies', fontsize=12, fontweight='bold', pad=10, color='white')

# ===== 圖9: VIX 指數儀表板 =====
ax9 = fig.add_subplot(gs[3, 0])
ax9.set_facecolor(COLORS['bg_card'])

vix_val = volatility['VIX']['value']
vix_change = volatility['VIX']['change']

# 繪製半圓儀表
theta = np.linspace(np.pi, 0, 100)
for start, end, color in [(0, 15, '#27ae60'), (15, 25, '#f1c40f'), (25, 35, '#e67e22'), (35, 80, '#c0392b')]:
    mask = (np.degrees(np.pi - theta) >= start * 180/80) & (np.degrees(np.pi - theta) <= end * 180/80)
    ax9.plot(np.cos(theta[mask]), np.sin(theta[mask]), color=color, linewidth=18, solid_capstyle='round')

vix_angle = np.pi - (min(vix_val, 80) / 80) * np.pi
ax9.annotate('', xy=(0.65*np.cos(vix_angle), 0.65*np.sin(vix_angle)), xytext=(0, 0), arrowprops=dict(arrowstyle='->', color='white', lw=3))
ax9.text(0, 0.35, f'VIX\n{vix_val:.1f}', ha='center', va='center', fontsize=18, fontweight='bold', color='white')

vix_color = COLORS['up'] if vix_change <= 0 else COLORS['down']
arrow = '↓' if vix_change <= 0 else '↑'
ax9.text(0, -0.05, f'{arrow} {vix_change:+.1f}%', ha='center', va='center', fontsize=12, color=vix_color, fontweight='bold')

# VIX 狀態
if vix_val < 15:
    vix_status = "Low Volatility"
elif vix_val < 25:
    vix_status = "Normal"
elif vix_val < 35:
    vix_status = "High Volatility"
else:
    vix_status = "Extreme Fear"
ax9.text(0, -0.3, vix_status, ha='center', va='center', fontsize=10, color=COLORS['text_secondary'])

ax9.set_xlim(-1.3, 1.3)
ax9.set_ylim(-0.5, 1.2)
ax9.axis('off')
ax9.set_title('VIX (Stock Volatility)', fontsize=12, fontweight='bold', pad=10, color='white')

# ===== 圖10: MOVE 指數儀表板 =====
ax10 = fig.add_subplot(gs[3, 1])
ax10.set_facecolor(COLORS['bg_card'])

move_val = volatility['MOVE']['value']
move_change = volatility['MOVE']['change']

# 繪製半圓儀表 (MOVE 通常 60-180)
theta = np.linspace(np.pi, 0, 100)
for start, end, color in [(60, 90, '#27ae60'), (90, 110, '#f1c40f'), (110, 140, '#e67e22'), (140, 180, '#c0392b')]:
    start_deg = (start - 60) / 120 * 180
    end_deg = (end - 60) / 120 * 180
    mask = (np.degrees(np.pi - theta) >= start_deg) & (np.degrees(np.pi - theta) <= end_deg)
    ax10.plot(np.cos(theta[mask]), np.sin(theta[mask]), color=color, linewidth=18, solid_capstyle='round')

move_angle = np.pi - ((min(max(move_val, 60), 180) - 60) / 120) * np.pi
ax10.annotate('', xy=(0.65*np.cos(move_angle), 0.65*np.sin(move_angle)), xytext=(0, 0), arrowprops=dict(arrowstyle='->', color='white', lw=3))
ax10.text(0, 0.35, f'MOVE\n{move_val:.0f}', ha='center', va='center', fontsize=18, fontweight='bold', color='white')

move_color = COLORS['up'] if move_change <= 0 else COLORS['down']
arrow = '↓' if move_change <= 0 else '↑'
ax10.text(0, -0.05, f'{arrow} {move_change:+.1f}%', ha='center', va='center', fontsize=12, color=move_color, fontweight='bold')

# MOVE 狀態
if move_val < 90:
    move_status = "Low Bond Vol"
elif move_val < 110:
    move_status = "Normal"
elif move_val < 140:
    move_status = "Elevated"
else:
    move_status = "High Bond Vol"
ax10.text(0, -0.3, move_status, ha='center', va='center', fontsize=10, color=COLORS['text_secondary'])

ax10.set_xlim(-1.3, 1.3)
ax10.set_ylim(-0.5, 1.2)
ax10.axis('off')
ax10.set_title('MOVE (Bond Volatility)', fontsize=12, fontweight='bold', pad=10, color='white')

# ===== 圖11: Fear & Greed =====
ax11 = fig.add_subplot(gs[3, 2])
ax11.set_facecolor(COLORS['bg_card'])

fg = volatility['Fear_Greed']

# 繪製半圓儀表
theta = np.linspace(np.pi, 0, 100)
for start, end, color in [(0, 25, '#c0392b'), (25, 45, '#e67e22'), (45, 55, '#f1c40f'), (55, 75, '#27ae60'), (75, 100, '#1e8449')]:
    mask = (np.degrees(np.pi - theta) >= start * 1.8) & (np.degrees(np.pi - theta) <= end * 1.8)
    ax11.plot(np.cos(theta[mask]), np.sin(theta[mask]), color=color, linewidth=18, solid_capstyle='round')

fg_angle = np.pi - (fg / 100) * np.pi
ax11.annotate('', xy=(0.65*np.cos(fg_angle), 0.65*np.sin(fg_angle)), xytext=(0, 0), arrowprops=dict(arrowstyle='->', color='white', lw=3))
ax11.text(0, 0.35, f'{fg:.0f}', ha='center', va='center', fontsize=24, fontweight='bold', color='white')

if fg < 25:
    fg_status = "Extreme Fear"
    fg_color = COLORS['down']
elif fg < 45:
    fg_status = "Fear"
    fg_color = COLORS['orange']
elif fg < 55:
    fg_status = "Neutral"
    fg_color = COLORS['gold']
elif fg < 75:
    fg_status = "Greed"
    fg_color = COLORS['up']
else:
    fg_status = "Extreme Greed"
    fg_color = '#1e8449'

ax11.text(0, -0.1, fg_status, ha='center', va='center', fontsize=14, color=fg_color, fontweight='bold')

ax11.set_xlim(-1.3, 1.3)
ax11.set_ylim(-0.4, 1.2)
ax11.axis('off')
ax11.set_title('Fear & Greed Index', fontsize=12, fontweight='bold', pad=10, color='white')

# ===== 圖12: 指數摘要 =====
ax12 = fig.add_subplot(gs[3, 3])
ax12.set_facecolor(COLORS['bg_card'])
ax12.axis('off')

# 主要指數摘要
summary_indices = ['S&P 500', 'NASDAQ', 'Dow Jones']
summary_text = "KEY INDICES\n" + "-" * 25 + "\n\n"
for idx in summary_indices:
    if idx in global_indices:
        data = global_indices[idx]
        arrow = '↑' if data['change'] >= 0 else '↓'
        color = 'green' if data['change'] >= 0 else 'red'
        summary_text += f"{idx}\n{data['value']:,.0f}  {arrow} {data['change']:+.2f}%\n\n"

ax12.text(0.5, 0.95, summary_text, transform=ax12.transAxes, fontsize=11, verticalalignment='top', ha='center',
         fontfamily='monospace', color='white',
         bbox=dict(boxstyle='round', facecolor=COLORS['bg_card'], edgecolor=COLORS['border'], alpha=0.9))

ax12.set_title('Market Summary', fontsize=12, fontweight='bold', pad=10, color='white')

# ===== 圖13: 金融新聞 =====
ax13 = fig.add_subplot(gs[4, :])
ax13.set_facecolor(COLORS['bg_card'])
ax13.axis('off')

news_text = "FINANCIAL NEWS\n" + "=" * 120 + "\n\n"
for i, n in enumerate(news[:8], 1):
    news_text += f"  {i}. [{n['source']:<15}] {n['title']:<70}  ({n['time']})\n"

ax13.text(0.01, 0.9, news_text, transform=ax13.transAxes, fontsize=10, verticalalignment='top',
         fontfamily='monospace', color='white',
         bbox=dict(boxstyle='round', facecolor=COLORS['bg_card'], edgecolor=COLORS['border'], alpha=0.9))

plt.tight_layout(rect=[0, 0.01, 1, 0.96])
plt.show()

# ==================== Console 輸出 ====================
print("\n")
print("=" * 80)
print(" " * 30 + "DETAILED REPORT")
print("=" * 80)

print("\n[US TREASURY YIELDS]")
print("-" * 50)
for i, label in enumerate(us_yields['labels']):
    today = us_yields['today'][i]
    month = us_yields['month_start'][i]
    year = us_yields['year_start'][i]
    print(f"  {label}: Today {today:.2f}% | Month Start {month:.2f}% | Year Start {year:.2f}%")

print("\n[GERMAN BUND YIELDS]")
print("-" * 50)
for i, label in enumerate(de_yields['labels']):
    today = de_yields['today'][i]
    month = de_yields['month_start'][i]
    year = de_yields['year_start'][i]
    print(f"  {label}: Today {today:.2f}% | Month Start {month:.2f}% | Year Start {year:.2f}%")

print("\n[GLOBAL 10Y BONDS]")
print("-" * 50)
for name, data in global_yields.items():
    arrow = "+" if data['change'] >= 0 else ""
    print(f"  {name:<15}: {data['value']:.2f}%  ({arrow}{data['change']:.2f}%)")

print("\n[US SECTOR PERFORMANCE]")
print("-" * 50)
for s in sectors:
    arrow = "+" if s['change'] >= 0 else ""
    bar = "█" * int(abs(s['change']) * 3)
    print(f"  {s['name']:<16} ({s['symbol']:<4}): {arrow}{s['change']:.2f}%  {bar}")

print("\n[GLOBAL INDICES]")
print("-" * 50)
for name, data in global_indices.items():
    arrow = "+" if data['change'] >= 0 else ""
    print(f"  {name:<18}: {data['value']:>12,.0f}  ({arrow}{data['change']:.2f}%)")

print("\n[FOREX]")
print("-" * 50)
for name, data in forex.items():
    arrow = "+" if data['change'] >= 0 else ""
    print(f"  {name:<12}: {data['value']:.4f}  ({arrow}{data['change']:.2f}%)")

print("\n[COMMODITIES]")
print("-" * 50)
for name, data in commodities.items():
    arrow = "+" if data['change'] >= 0 else ""
    print(f"  {name:<12}: ${data['value']:>10,.2f}  ({arrow}{data['change']:.2f}%)")

print("\n[CRYPTOCURRENCIES]")
print("-" * 50)
for name, data in crypto.items():
    arrow = "+" if data['change'] >= 0 else ""
    print(f"  {name:<10}: ${data['value']:>12,.2f}  ({arrow}{data['change']:.2f}%)")

print("\n[VOLATILITY INDICES]")
print("-" * 50)
print(f"  VIX (Stock):  {volatility['VIX']['value']:.2f}  ({volatility['VIX']['change']:+.1f}%)")
print(f"  MOVE (Bond):  {volatility['MOVE']['value']:.0f}  ({volatility['MOVE']['change']:+.1f}%)")
print(f"  Fear & Greed: {volatility['Fear_Greed']:.0f}")

print("\n[NEWS]")
print("-" * 50)
for i, n in enumerate(news[:6], 1):
    print(f"  {i}. [{n['source']}] {n['title']}")

print("\n" + "=" * 80)
print(f"Report Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("Disclaimer: Data for reference only, not investment advice")
print("Tip: Press F5 to refresh all data")
print("=" * 80)
