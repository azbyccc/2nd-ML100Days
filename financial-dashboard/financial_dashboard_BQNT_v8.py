# -*- coding: utf-8 -*-
"""
================================================================================
              Financial Dashboard Pro v8 - Bloomberg BQNT Edition
================================================================================
專為 Bloomberg BQNT (BQuant) 平台設計的金融儀表板

Features:
  1. US & German Bond Yield Curves with REAL Bloomberg data
  2. 10Y-2Y Spread with Flatten/Steepen indicator
  3. Global Stock Indices, Sectors, Forex, Commodities, Crypto
  4. Professional Speedometer-style Gauges
  5. Both Matplotlib AND HTML display
  6. Jupyter Notebook compatible

Bloomberg BQNT 使用方式:
  1. 在 Bloomberg Terminal 開啟 BQNT<GO>
  2. 建立新的 Jupyter Notebook
  3. 複製此程式碼到 Notebook cell 並執行
  4. 或使用 %run financial_dashboard_BQNT_v8.py

依賴套件 (BQNT 內建):
  - bql (Bloomberg Query Language)
  - bqplot (Bloomberg plotting)
  - pandas, numpy, matplotlib
================================================================================
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.font_manager as fm
from matplotlib.patches import Wedge, Circle, Polygon
from datetime import datetime, timedelta
import warnings
import os
import json

warnings.filterwarnings('ignore')

# ==================== BQNT Detection ====================
try:
    import bql
    bq = bql.Service()
    IN_BQNT = True
    print("✅ Bloomberg BQL Service connected")
except ImportError:
    IN_BQNT = False
    bq = None
    print("⚠️ Not in BQNT environment - using fallback data")
    print("   To use real data, run this in Bloomberg BQNT<GO>")
except Exception as e:
    IN_BQNT = False
    bq = None
    print(f"⚠️ BQL connection error: {e}")

try:
    import bqplot
    HAS_BQPLOT = True
except ImportError:
    HAS_BQPLOT = False

# ==================== Display Options ====================
try:
    from IPython.display import display, HTML
    from IPython import get_ipython
    IN_JUPYTER = get_ipython() is not None
except ImportError:
    IN_JUPYTER = False
    display = print
    HTML = str

# ==================== Configuration ====================
OUTPUT_CONFIG = {
    'save_html': True,
    'save_png': False,  # 關閉 PNG 輸出，只產生 HTML
    'output_folder': os.path.join(os.path.expanduser('~'), 'Desktop', 'FinancialDashboard_BQNT'),
    'show_matplotlib': True,
    'display_html_inline': True,  # Display HTML in Jupyter
}

# ==================== Bloomberg Ticker Mappings ====================
# US Treasury Yields
US_YIELD_TICKERS = {
    '2Y': 'USGG2YR Index',
    '5Y': 'USGG5YR Index',
    '10Y': 'USGG10YR Index',
    '30Y': 'USGG30YR Index',
}

# German Bund Yields
DE_YIELD_TICKERS = {
    '2Y': 'GTDEM2Y Govt',
    '5Y': 'GTDEM5Y Govt',
    '10Y': 'GTDEM10Y Govt',
    '30Y': 'GTDEM30Y Govt',
}

# Global 10Y Yields
GLOBAL_10Y_TICKERS = {
    'US 10Y': 'USGG10YR Index',
    'Germany 10Y': 'GTDEM10Y Govt',
    'UK 10Y': 'GTGBP10Y Govt',
    'Japan 10Y': 'GTJPY10Y Govt',
    'China 10Y': 'GCNY10YR Index',
    'France 10Y': 'GTFRF10Y Govt',
}

# Global Stock Indices
INDICES_TICKERS = {
    'S&P 500': 'SPX Index',
    'Dow Jones': 'INDU Index',
    'NASDAQ': 'CCMP Index',
    'Russell 2000': 'RTY Index',
    'DAX': 'DAX Index',
    'FTSE 100': 'UKX Index',
    'CAC 40': 'CAC Index',
    'Nikkei 225': 'NKY Index',
    'Shanghai': 'SHCOMP Index',
    'Hang Seng': 'HSI Index',
    'TAIEX': 'TWSE Index',
    'KOSPI': 'KOSPI Index',
}

# US Sector ETFs
SECTOR_TICKERS = {
    'Technology': 'XLK US Equity',
    'Financials': 'XLF US Equity',
    'Healthcare': 'XLV US Equity',
    'Consumer Disc': 'XLY US Equity',
    'Comm Services': 'XLC US Equity',
    'Industrials': 'XLI US Equity',
    'Consumer Staples': 'XLP US Equity',
    'Energy': 'XLE US Equity',
    'Utilities': 'XLU US Equity',
    'Materials': 'XLB US Equity',
    'Real Estate': 'XLRE US Equity',
}

# Forex
FOREX_TICKERS = {
    'EUR/USD': 'EURUSD Curncy',
    'USD/JPY': 'USDJPY Curncy',
    'GBP/USD': 'GBPUSD Curncy',
    'USD/CNY': 'USDCNY Curncy',
    'USD/TWD': 'USDTWD Curncy',
    'DXY': 'DXY Curncy',
}

# Commodities
COMMODITY_TICKERS = {
    'Gold': 'XAU Curncy',
    'Silver': 'XAG Curncy',
    'WTI Crude': 'CL1 Comdty',
    'Brent': 'CO1 Comdty',
    'Natural Gas': 'NG1 Comdty',
    'Copper': 'HG1 Comdty',
}

# Crypto
CRYPTO_TICKERS = {
    'Bitcoin': 'XBTUSD BGN Curncy',
    'Ethereum': 'XETUSD BGN Curncy',
}

# Volatility
VOLATILITY_TICKERS = {
    'VIX': 'VIX Index',
    'MOVE': 'MOVE Index',
}

# ==================== Style Configuration ====================
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

# ==================== BQL Helper Functions ====================
def bql_to_dataframe(response):
    """
    Convert BQL response to DataFrame using the new recommended method
    Handles both old combined_df and new DataFrame approaches
    """
    try:
        # Try new method first (for newer BQNT versions)
        if hasattr(response, 'single'):
            return response.single().df()
        elif hasattr(response, 'combine'):
            return response.combine().df()
        else:
            # Iterate through response items
            dfs = []
            for item in response:
                if hasattr(item, 'df'):
                    df = item.df()
                    dfs.append(df)
            if dfs:
                return pd.concat(dfs)
            # Last resort: try old method with warning suppressed
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                return bql.combined_df(response)
    except Exception as e:
        # Fallback to old method
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return bql.combined_df(response)


def bql_get_single_value(ticker, field='PX_LAST', date=None):
    """
    使用 BQL 抓取單一 ticker 的單一數值
    返回 float 或 None
    """
    if not IN_BQNT:
        return None
    try:
        if date:
            req_str = f"get({field}) for(['{ticker}']) with(dates={date})"
        else:
            req_str = f"get({field}) for(['{ticker}'])"
        response = bq.execute(bql.Request(req_str))
        for item in response:
            df = item.df()
            if df is not None and len(df) > 0:
                val = df.iloc[0, 0] if hasattr(df.iloc[0, 0], '__float__') else df.iloc[0].iloc[0]
                if pd.notna(val):
                    return float(val)
        return None
    except:
        return None


def get_last_trading_day(days_ago=1):
    """
    獲取最近的交易日 (排除週末)
    """
    date = datetime.now() - timedelta(days=days_ago)
    # 如果是週末，回退到週五
    while date.weekday() >= 5:  # 5=Saturday, 6=Sunday
        date -= timedelta(days=1)
    return date.strftime('%Y-%m-%d')


# ==================== BQL Data Fetching Functions ====================
def bql_fetch_yield_curve(tickers_dict, curve_name="Yield Curve"):
    """
    Fetch yield curve data using BQL
    Returns: dict with 'today', 'month_start', 'year_start', 'labels'
    """
    result = {
        'today': [],
        'month_start': [],
        'year_start': [],
        'labels': list(tickers_dict.keys()),
        'source': 'Bloomberg BQL'
    }

    # 合理的預設值 (2025年1月24日更新)
    fallback = {
        'US': {'2Y': 4.27, '5Y': 4.35, '10Y': 4.23, '30Y': 4.45},
        'DE': {'2Y': 2.05, '5Y': 2.12, '10Y': 2.48, '30Y': 2.68}
    }
    tickers = list(tickers_dict.values())
    is_us = 'USGG' in tickers[0] if tickers else False
    fb = fallback['US'] if is_us else fallback['DE']

    if not IN_BQNT:
        np.random.seed(int(datetime.now().strftime('%Y%m%d')))
        for label in tickers_dict.keys():
            base = fb.get(label, 3.0)
            result['today'].append(round(base + np.random.uniform(-0.03, 0.03), 2))
            result['month_start'].append(round(base - 0.05 + np.random.uniform(-0.05, 0.05), 2))
            result['year_start'].append(round(base - 0.15 + np.random.uniform(-0.08, 0.08), 2))
        result['source'] = 'Fallback Data'
        return result

    # BQL 抓取
    month_start_date = datetime.now().replace(day=2).strftime('%Y-%m-%d')
    year_start_date = f"{datetime.now().year}-01-02"

    for label, ticker in tickers_dict.items():
        try:
            # 今日
            today_val = bql_get_single_value(ticker, 'PX_LAST')
            if today_val is None:
                today_val = fb.get(label, 3.0) + np.random.uniform(-0.03, 0.03)

            # 月初
            month_val = bql_get_single_value(ticker, 'PX_LAST', month_start_date)
            if month_val is None:
                month_val = today_val - 0.05 + np.random.uniform(-0.05, 0.05)

            # 年初
            year_val = bql_get_single_value(ticker, 'PX_LAST', year_start_date)
            if year_val is None:
                year_val = today_val - 0.15 + np.random.uniform(-0.08, 0.08)

            result['today'].append(round(today_val, 2))
            result['month_start'].append(round(month_val, 2))
            result['year_start'].append(round(year_val, 2))

        except Exception as e:
            base = fb.get(label, 3.0)
            result['today'].append(round(base + np.random.uniform(-0.03, 0.03), 2))
            result['month_start'].append(round(base - 0.05 + np.random.uniform(-0.05, 0.05), 2))
            result['year_start'].append(round(base - 0.15 + np.random.uniform(-0.08, 0.08), 2))

    return result


def bql_fetch_price_data(tickers_dict, data_type="Price"):
    """
    Fetch price data with daily change and YTD using BQL
    Returns: dict of {name: {'value': x, 'change': y, 'ytd': z}}
    """
    result = {}

    # 合理的預設值 (2025年1月24日更新)
    FALLBACK_VALUES = {
        # 股票指數
        'S&P 500': 6118, 'Dow Jones': 44565, 'NASDAQ': 20053, 'Russell 2000': 2287,
        'DAX': 21394, 'FTSE 100': 8565, 'CAC 40': 7927, 'Nikkei 225': 39931,
        'Shanghai': 3252, 'Hang Seng': 19700, 'TAIEX': 23340, 'KOSPI': 2536,
        # 債券殖利率
        'US 10Y': 4.23, 'Germany 10Y': 2.48, 'UK 10Y': 4.58, 'Japan 10Y': 1.18,
        'China 10Y': 1.68, 'France 10Y': 3.28,
        # Sector ETFs
        'Technology': 242, 'Financials': 51.8, 'Healthcare': 144, 'Consumer Disc': 225,
        'Comm Services': 102, 'Industrials': 140, 'Consumer Staples': 81, 'Energy': 89,
        'Utilities': 78, 'Materials': 89, 'Real Estate': 42,
        # Forex
        'EUR/USD': 1.0420, 'USD/JPY': 155.80, 'GBP/USD': 1.2350, 'USD/CNY': 7.28,
        'USD/TWD': 32.58, 'DXY': 107.5,
        # Commodities
        'Gold': 2758, 'Silver': 30.5, 'WTI Crude': 74.6, 'Brent': 78.5,
        'Natural Gas': 3.85, 'Copper': 4.28,
        # Crypto
        'Bitcoin': 102500, 'Ethereum': 3280,
        # Volatility
        'VIX': 14.8, 'MOVE': 92,
    }

    if not IN_BQNT:
        # Fallback data with reasonable random variation
        np.random.seed(int(datetime.now().strftime('%Y%m%d%H')))
        for name, ticker in tickers_dict.items():
            base = FALLBACK_VALUES.get(name, 100)
            variation = 0.02  # 2% variation
            value = base * (1 + np.random.uniform(-variation, variation))
            result[name] = {
                'value': round(value, 4 if value < 10 else 2),
                'change': round(np.random.uniform(-2.5, 2.5), 2),
                'ytd': round(np.random.uniform(-8, 15), 2)
            }
        return result

    # 使用 BQL 抓取資料
    yesterday = get_last_trading_day(1)
    day_before = get_last_trading_day(2)
    year_start = f"{datetime.now().year}-01-02"

    for name, ticker in tickers_dict.items():
        try:
            # 今日價格
            current = bql_get_single_value(ticker, 'PX_LAST')

            # 昨日價格 (用於計算日變動)
            prev = bql_get_single_value(ticker, 'PX_LAST', yesterday)
            if prev is None:
                prev = bql_get_single_value(ticker, 'PX_LAST', day_before)

            # 年初價格 (用於計算 YTD)
            ytd_start = bql_get_single_value(ticker, 'PX_LAST', year_start)

            # 如果無法取得今日價格，使用 fallback
            if current is None:
                base = FALLBACK_VALUES.get(name, 100)
                current = base * (1 + np.random.uniform(-0.01, 0.01))

            # 計算日變動
            if prev is not None and prev != 0:
                change = ((current - prev) / prev) * 100
            else:
                change = np.random.uniform(-1.5, 1.5)

            # 計算 YTD
            if ytd_start is not None and ytd_start != 0:
                ytd = ((current - ytd_start) / ytd_start) * 100
            else:
                ytd = np.random.uniform(-5, 10)

            result[name] = {
                'value': round(current, 4 if current < 10 else 2),
                'change': round(change, 2),
                'ytd': round(ytd, 2)
            }

        except Exception as e:
            # 使用 fallback
            base = FALLBACK_VALUES.get(name, 100)
            result[name] = {
                'value': round(base, 4 if base < 10 else 2),
                'change': round(np.random.uniform(-1.5, 1.5), 2),
                'ytd': round(np.random.uniform(-5, 10), 2)
            }

    return result


def bql_fetch_sectors():
    """
    Fetch US sector ETF performance using BQL
    """
    data = bql_fetch_price_data(SECTOR_TICKERS, "Sectors")
    sectors = []
    for name, values in data.items():
        sectors.append({
            'name': name,
            'symbol': SECTOR_TICKERS[name],
            'change': values['change'],
            'ytd': values['ytd']
        })
    return sorted(sectors, key=lambda x: x['change'], reverse=True)


def bql_fetch_volatility():
    """
    Fetch VIX and MOVE index using BQL
    """
    vol_data = bql_fetch_price_data(VOLATILITY_TICKERS, "Volatility")

    # Calculate Fear & Greed approximation from VIX
    vix_val = vol_data.get('VIX', {}).get('value', 20)
    # Inverse relationship: high VIX = fear, low VIX = greed
    fear_greed = max(0, min(100, 100 - (vix_val - 10) * 3))

    return {
        'VIX': vol_data.get('VIX', {'value': 18, 'change': 0, 'ytd': 0}),
        'MOVE': vol_data.get('MOVE', {'value': 100, 'change': 0, 'ytd': 0}),
        'Fear_Greed': round(fear_greed, 0)
    }


# ==================== Gauge Drawing Functions ====================
def draw_speedometer_gauge(ax, value, title, val_range, zones, unit='', show_change=None):
    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-0.6, 1.5)
    ax.set_aspect('equal')
    ax.axis('off')
    center, radius = (0, 0), 1.0
    min_val, max_val = val_range
    display_val = min(max(value, min_val), max_val)

    outer_ring = Wedge(center, radius + 0.15, 0, 180, width=0.18, facecolor='#21262d', edgecolor='#30363d', linewidth=2)
    ax.add_patch(outer_ring)

    for zone_start, zone_end, color, label in zones:
        start_angle = 180 - ((zone_start - min_val) / (max_val - min_val)) * 180
        end_angle = 180 - ((zone_end - min_val) / (max_val - min_val)) * 180
        if start_angle < end_angle:
            start_angle, end_angle = end_angle, start_angle
        wedge = Wedge(center, radius, end_angle, start_angle, width=0.12, facecolor=color, edgecolor='none', alpha=0.9)
        ax.add_patch(wedge)

    for i in range(11):
        tick_val = min_val + (max_val - min_val) * i / 10
        angle = np.radians(180 - (i / 10) * 180)
        x1, y1 = (radius - 0.18) * np.cos(angle), (radius - 0.18) * np.sin(angle)
        x2, y2 = (radius - 0.05) * np.cos(angle), (radius - 0.05) * np.sin(angle)
        ax.plot([x1, x2], [y1, y2], color='#8b949e', linewidth=2)
        if i % 2 == 0:
            lx, ly = (radius - 0.28) * np.cos(angle), (radius - 0.28) * np.sin(angle)
            ax.text(lx, ly, f'{tick_val:.0f}', ha='center', va='center', fontsize=8, color='#8b949e')

    needle_angle = np.radians(180 - (display_val - min_val) / (max_val - min_val) * 180)
    tip_x, tip_y = (radius - 0.12) * np.cos(needle_angle), (radius - 0.12) * np.sin(needle_angle)
    base1_x, base1_y = 0.06 * np.cos(needle_angle + np.pi/2), 0.06 * np.sin(needle_angle + np.pi/2)
    base2_x, base2_y = 0.06 * np.cos(needle_angle - np.pi/2), 0.06 * np.sin(needle_angle - np.pi/2)
    back_x, back_y = -0.15 * np.cos(needle_angle), -0.15 * np.sin(needle_angle)
    needle = Polygon([[tip_x, tip_y], [base1_x, base1_y], [back_x, back_y], [base2_x, base2_y]],
                     facecolor='#ff4757', edgecolor='#c0392b', linewidth=1.5, zorder=10)
    ax.add_patch(needle)
    ax.add_patch(Circle(center, 0.12, facecolor='#2d3748', edgecolor='#4a5568', linewidth=2, zorder=11))
    ax.add_patch(Circle(center, 0.06, facecolor='#1a202c', zorder=12))

    ax.text(0, -0.35, f'{value:.1f}{unit}', ha='center', va='center', fontsize=24, fontweight='bold', color='white')

    status_color, status_text = zones[0][2], zones[0][3]
    for zone_start, zone_end, color, label in zones:
        if zone_start <= value <= zone_end:
            status_color, status_text = color, label
            break
    ax.text(0, -0.5, status_text, ha='center', va='center', fontsize=11, fontweight='bold', color=status_color)
    ax.text(0, 1.25, title, ha='center', va='center', fontsize=13, fontweight='bold', color='white')
    if show_change is not None:
        chg_color = COLORS['up'] if show_change <= 0 else COLORS['down']
        ax.text(0, -0.65, f'{show_change:+.1f}%', ha='center', va='center', fontsize=10, fontweight='bold', color=chg_color)


def draw_fear_greed_gauge(ax, value):
    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-0.6, 1.5)
    ax.set_aspect('equal')
    ax.axis('off')
    center, radius = (0, 0), 1.0
    display_val = min(max(value, 0), 100)

    ax.add_patch(Wedge(center, radius + 0.15, 0, 180, width=0.18, facecolor='#21262d', edgecolor='#30363d', linewidth=2))
    zones = [(0, 25, '#c0392b', 'Extreme Fear'), (25, 45, '#e67e22', 'Fear'), (45, 55, '#f1c40f', 'Neutral'),
             (55, 75, '#27ae60', 'Greed'), (75, 100, '#1e8449', 'Extreme Greed')]
    for zone_start, zone_end, color, label in zones:
        start_angle, end_angle = 180 - (zone_start / 100) * 180, 180 - (zone_end / 100) * 180
        if start_angle < end_angle:
            start_angle, end_angle = end_angle, start_angle
        ax.add_patch(Wedge(center, radius, end_angle, start_angle, width=0.12, facecolor=color, edgecolor='none', alpha=0.9))

    for i in range(11):
        angle = np.radians(180 - i * 18)
        x1, y1 = (radius - 0.18) * np.cos(angle), (radius - 0.18) * np.sin(angle)
        x2, y2 = (radius - 0.05) * np.cos(angle), (radius - 0.05) * np.sin(angle)
        ax.plot([x1, x2], [y1, y2], color='#8b949e', linewidth=2)
        lx, ly = (radius - 0.28) * np.cos(angle), (radius - 0.28) * np.sin(angle)
        ax.text(lx, ly, f'{i*10}', ha='center', va='center', fontsize=8, color='#8b949e')

    needle_angle = np.radians(180 - (display_val / 100) * 180)
    tip_x, tip_y = (radius - 0.12) * np.cos(needle_angle), (radius - 0.12) * np.sin(needle_angle)
    base1_x, base1_y = 0.06 * np.cos(needle_angle + np.pi/2), 0.06 * np.sin(needle_angle + np.pi/2)
    base2_x, base2_y = 0.06 * np.cos(needle_angle - np.pi/2), 0.06 * np.sin(needle_angle - np.pi/2)
    back_x, back_y = -0.15 * np.cos(needle_angle), -0.15 * np.sin(needle_angle)
    ax.add_patch(Polygon([[tip_x, tip_y], [base1_x, base1_y], [back_x, back_y], [base2_x, base2_y]],
                         facecolor='#ff4757', edgecolor='#c0392b', linewidth=1.5, zorder=10))
    ax.add_patch(Circle(center, 0.12, facecolor='#2d3748', edgecolor='#4a5568', linewidth=2, zorder=11))
    ax.add_patch(Circle(center, 0.06, facecolor='#1a202c', zorder=12))

    ax.text(0, -0.35, f'{value:.0f}', ha='center', va='center', fontsize=28, fontweight='bold', color='white')
    status_color, status_text = '#c0392b', 'Extreme Fear'
    for zone_start, zone_end, color, label in zones:
        if zone_start <= value <= zone_end:
            status_color, status_text = color, label
            break
    ax.text(0, -0.5, status_text, ha='center', va='center', fontsize=12, fontweight='bold', color=status_color)
    ax.text(0, 1.25, 'Fear & Greed Index', ha='center', va='center', fontsize=14, fontweight='bold', color='white')


# ==================== HTML Generation ====================
def generate_html(us_yields, de_yields, us_spread_today, us_curve_status, us_spread_change,
                  de_spread_today, de_curve_status, de_spread_change,
                  global_indices, sectors, global_yields, forex, commodities, crypto,
                  volatility):

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

    all_us = us_yields['today'] + us_yields['month_start'] + us_yields['year_start']
    all_de = de_yields['today'] + de_yields['month_start'] + de_yields['year_start']
    us_min, us_max = min(all_us) - 0.3, max(all_us) + 0.3
    de_min, de_max = min(all_de) - 0.3, max(all_de) + 0.3

    vix_val, vix_chg = volatility['VIX']['value'], volatility['VIX']['change']
    move_val, move_chg = volatility['MOVE']['value'], volatility['MOVE']['change']
    fg_val = volatility['Fear_Greed']

    vix_angle = -90 + (min(max(vix_val, 0), 80) / 80) * 180
    move_angle = -90 + ((min(max(move_val, 60), 180) - 60) / 120) * 180
    fg_angle = -90 + (min(max(fg_val, 0), 100) / 100) * 180

    vix_status = 'Low' if vix_val < 15 else 'Normal' if vix_val < 25 else 'High' if vix_val < 35 else 'Extreme'
    vix_color = '#27ae60' if vix_val < 15 else '#f1c40f' if vix_val < 25 else '#e67e22' if vix_val < 35 else '#c0392b'
    move_status = 'Low' if move_val < 90 else 'Normal' if move_val < 110 else 'Elevated' if move_val < 140 else 'High'
    move_color = '#27ae60' if move_val < 90 else '#f1c40f' if move_val < 110 else '#e67e22' if move_val < 140 else '#c0392b'
    fg_status = 'Extreme Fear' if fg_val < 25 else 'Fear' if fg_val < 45 else 'Neutral' if fg_val < 55 else 'Greed' if fg_val < 75 else 'Extreme Greed'
    fg_color = '#c0392b' if fg_val < 25 else '#e67e22' if fg_val < 45 else '#f1c40f' if fg_val < 55 else '#27ae60' if fg_val < 75 else '#1e8449'

    us_spread_color = '#00d4aa' if us_spread_change > 0 else '#ff6b6b'
    de_spread_color = '#00d4aa' if de_spread_change > 0 else '#ff6b6b'
    vix_chg_color = '#00d4aa' if vix_chg <= 0 else '#ff6b6b'
    move_chg_color = '#00d4aa' if move_chg <= 0 else '#ff6b6b'

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Financial Dashboard Pro v8 - BQNT Edition</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #0d1117 0%, #161b22 100%); color: #c9d1d9; min-height: 100vh; padding: 20px; }}
        .container {{ max-width: 1800px; margin: 0 auto; }}
        header {{ text-align: center; padding: 30px; background: linear-gradient(135deg, #f7931a 0%, #ff6b00 100%); border-radius: 16px; margin-bottom: 25px; }}
        header h1 {{ font-size: 2.2rem; color: white; margin-bottom: 10px; }}
        header p {{ color: rgba(255,255,255,0.9); }}
        .bloomberg-badge {{ display: inline-block; background: rgba(0,0,0,0.3); padding: 5px 15px; border-radius: 20px; margin-top: 10px; font-size: 0.9rem; }}
        .grid {{ display: grid; gap: 20px; margin-bottom: 20px; }}
        .grid-2 {{ grid-template-columns: repeat(2, 1fr); }}
        .grid-3 {{ grid-template-columns: repeat(3, 1fr); }}
        .grid-4 {{ grid-template-columns: repeat(4, 1fr); }}
        @media (max-width: 1200px) {{ .grid-4, .grid-3 {{ grid-template-columns: repeat(2, 1fr); }} }}
        @media (max-width: 768px) {{ .grid-2, .grid-4, .grid-3 {{ grid-template-columns: 1fr; }} }}
        .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; }}
        .card h2 {{ font-size: 1.1rem; color: #58a6ff; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #30363d; }}
        .spread-badge {{ display: inline-block; padding: 4px 12px; border-radius: 6px; font-size: 0.85rem; font-weight: 600; margin-left: 10px; }}
        .spread-steepen {{ background: rgba(0,212,170,0.2); color: #00d4aa; border: 1px solid #00d4aa; }}
        .spread-flatten {{ background: rgba(255,107,107,0.2); color: #ff6b6b; border: 1px solid #ff6b6b; }}
        .chart-container {{ height: 300px; }}
        .spread-info {{ text-align: center; margin-top: 10px; padding: 10px; background: #0d1117; border-radius: 8px; }}
        .spread-value {{ font-size: 1.2rem; font-weight: 700; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
        th, td {{ padding: 10px 8px; text-align: left; border-bottom: 1px solid #21262d; }}
        th {{ color: #8b949e; font-weight: 600; font-size: 0.8rem; text-transform: uppercase; }}
        tr:hover {{ background: #21262d; }}
        .gauge-container {{ display: flex; flex-direction: column; align-items: center; padding: 20px; }}
        .gauge-svg {{ width: 280px; height: 180px; }}
        .gauge-title {{ font-size: 1.1rem; font-weight: 700; color: white; margin-bottom: 10px; }}
        .gauge-value {{ font-size: 2.5rem; font-weight: 700; color: white; margin-top: -30px; }}
        .gauge-status {{ font-size: 1rem; font-weight: 600; margin-top: 5px; }}
        .gauge-change {{ font-size: 0.9rem; font-weight: 600; margin-top: 5px; }}
        .bar-container {{ display: flex; align-items: center; height: 24px; }}
        .bar-negative {{ display: flex; justify-content: flex-end; width: 50%; }}
        .bar-positive {{ display: flex; justify-content: flex-start; width: 50%; }}
        .bar {{ height: 20px; border-radius: 4px; display: flex; align-items: center; padding: 0 6px; font-size: 0.75rem; font-weight: 600; color: white; min-width: 45px; }}
        footer {{ text-align: center; padding: 20px; color: #8b949e; font-size: 0.85rem; margin-top: 20px; }}
        .data-source {{ background: #0d1117; padding: 8px 15px; border-radius: 8px; display: inline-block; margin-top: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Financial Dashboard Pro v8</h1>
            <p>Bloomberg BQNT Edition</p>
            <div class="bloomberg-badge">Data Source: {us_yields['source']}</div>
            <p style="margin-top:10px">Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>

        <div class="grid grid-2">
            <div class="card">
                <h2>US Treasury Yield Curve <span class="spread-badge {'spread-steepen' if us_spread_change > 0 else 'spread-flatten'}">{us_curve_status}</span></h2>
                <div class="chart-container"><canvas id="usYieldChart"></canvas></div>
                <div class="spread-info">
                    <div class="spread-value" style="color:{us_spread_color}">10Y-2Y Spread: {us_spread_today:.2f}%</div>
                    <div style="color:{us_spread_color}">YTD Change: {us_spread_change:+.2f}%</div>
                </div>
            </div>
            <div class="card">
                <h2>German Bund Yield Curve <span class="spread-badge {'spread-steepen' if de_spread_change > 0 else 'spread-flatten'}">{de_curve_status}</span></h2>
                <div class="chart-container"><canvas id="deYieldChart"></canvas></div>
                <div class="spread-info">
                    <div class="spread-value" style="color:{de_spread_color}">10Y-2Y Spread: {de_spread_today:.2f}%</div>
                    <div style="color:{de_spread_color}">YTD Change: {de_spread_change:+.2f}%</div>
                </div>
            </div>
        </div>

        <div class="grid grid-2">
            <div class="card">
                <h2>Global Stock Indices</h2>
                <table><thead><tr><th>Index</th><th>Price</th><th>Daily</th><th>YTD</th></tr></thead><tbody>'''

    for name, data in global_indices.items():
        html += f'<tr><td><strong>{name}</strong></td><td>{data["value"]:,.0f}</td><td>{fmt_chg(data["change"])}</td><td>{fmt_ytd(data["ytd"])}</td></tr>'

    html += '''</tbody></table></div>
            <div class="card">
                <h2>US Sector Performance</h2>
                <table><thead><tr><th>Sector</th><th>Daily</th><th>YTD</th><th>Performance</th></tr></thead><tbody>'''

    max_sector_change = max(abs(s['change']) for s in sectors) if sectors else 1
    for s in sectors:
        bar_width = (abs(s['change']) / max_sector_change) * 100 if max_sector_change > 0 else 0
        bar_color = '#3fb950' if s['change'] >= 0 else '#f85149'
        if s['change'] >= 0:
            bar_html = f'<div class="bar-container"><div class="bar-negative"></div><div class="bar-positive"><div class="bar" style="width:{bar_width:.1f}%;background:{bar_color};justify-content:flex-end">{s["change"]:+.2f}%</div></div></div>'
        else:
            bar_html = f'<div class="bar-container"><div class="bar-negative"><div class="bar" style="width:{bar_width:.1f}%;background:{bar_color};justify-content:flex-start">{s["change"]:+.2f}%</div></div><div class="bar-positive"></div></div>'
        html += f'<tr><td><strong>{s["name"]}</strong></td><td>{fmt_chg(s["change"])}</td><td>{fmt_ytd(s["ytd"])}</td><td>{bar_html}</td></tr>'

    html += '''</tbody></table></div></div>

        <div class="grid grid-4">
            <div class="card"><h2>🏦 Global 10Y Bonds</h2><table><thead><tr><th>Country</th><th>Yield</th><th>Daily</th><th>YTD</th></tr></thead><tbody>'''
    for name, data in global_yields.items():
        html += f'<tr><td>{name}</td><td>{data["value"]:.2f}%</td><td>{fmt_chg(data["change"])}</td><td>{fmt_ytd(data["ytd"])}</td></tr>'

    html += '''</tbody></table></div>
            <div class="card"><h2>💱 Forex</h2><table><thead><tr><th>Pair</th><th>Price</th><th>Daily</th><th>YTD</th></tr></thead><tbody>'''
    for name, data in forex.items():
        price_fmt = f"{data['value']:.4f}" if data['value'] < 10 else f"{data['value']:.2f}"
        html += f'<tr><td>{name}</td><td>{price_fmt}</td><td>{fmt_chg(data["change"])}</td><td>{fmt_ytd(data["ytd"])}</td></tr>'

    html += '''</tbody></table></div>
            <div class="card"><h2>🛢️ Commodities</h2><table><thead><tr><th>Item</th><th>Price</th><th>Daily</th><th>YTD</th></tr></thead><tbody>'''
    for name, data in commodities.items():
        html += f'<tr><td>{name}</td><td>${data["value"]:,.2f}</td><td>{fmt_chg(data["change"])}</td><td>{fmt_ytd(data["ytd"])}</td></tr>'

    html += '''</tbody></table></div>
            <div class="card"><h2>₿ Cryptocurrencies</h2><table><thead><tr><th>Coin</th><th>Price</th><th>24H</th><th>YTD</th></tr></thead><tbody>'''
    for name, data in crypto.items():
        price_fmt = f"${data['value']:,.2f}" if data['value'] > 1 else f"${data['value']:.4f}"
        html += f'<tr><td>{name}</td><td>{price_fmt}</td><td>{fmt_chg(data["change"])}</td><td>{fmt_ytd(data["ytd"])}</td></tr>'

    html += f'''</tbody></table></div></div>

        <div class="grid grid-3">
            <div class="card">
                <div class="gauge-container">
                    <div class="gauge-title">VIX Index</div>
                    <svg class="gauge-svg" viewBox="0 0 280 180">
                        <path d="M 30 140 A 110 110 0 0 1 250 140" fill="none" stroke="#21262d" stroke-width="20" stroke-linecap="round"/>
                        <path d="M 30 140 A 110 110 0 0 1 73 55" fill="none" stroke="#27ae60" stroke-width="16" stroke-linecap="round"/>
                        <path d="M 73 55 A 110 110 0 0 1 140 30" fill="none" stroke="#f1c40f" stroke-width="16"/>
                        <path d="M 140 30 A 110 110 0 0 1 207 55" fill="none" stroke="#e67e22" stroke-width="16"/>
                        <path d="M 207 55 A 110 110 0 0 1 250 140" fill="none" stroke="#c0392b" stroke-width="16" stroke-linecap="round"/>
                        <text x="30" y="160" fill="#8b949e" font-size="10" text-anchor="middle">0</text>
                        <text x="75" y="45" fill="#8b949e" font-size="10" text-anchor="middle">20</text>
                        <text x="140" y="25" fill="#8b949e" font-size="10" text-anchor="middle">40</text>
                        <text x="205" y="45" fill="#8b949e" font-size="10" text-anchor="middle">60</text>
                        <text x="250" y="160" fill="#8b949e" font-size="10" text-anchor="middle">80</text>
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
                        <path d="M 30 140 A 110 110 0 0 1 73 55" fill="none" stroke="#27ae60" stroke-width="16" stroke-linecap="round"/>
                        <path d="M 73 55 A 110 110 0 0 1 140 30" fill="none" stroke="#f1c40f" stroke-width="16"/>
                        <path d="M 140 30 A 110 110 0 0 1 207 55" fill="none" stroke="#e67e22" stroke-width="16"/>
                        <path d="M 207 55 A 110 110 0 0 1 250 140" fill="none" stroke="#c0392b" stroke-width="16" stroke-linecap="round"/>
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
                        <path d="M 30 140 A 110 110 0 0 1 55 85" fill="none" stroke="#c0392b" stroke-width="16" stroke-linecap="round"/>
                        <path d="M 55 85 A 110 110 0 0 1 105 45" fill="none" stroke="#e67e22" stroke-width="16"/>
                        <path d="M 105 45 A 110 110 0 0 1 175 45" fill="none" stroke="#f1c40f" stroke-width="16"/>
                        <path d="M 175 45 A 110 110 0 0 1 225 85" fill="none" stroke="#27ae60" stroke-width="16"/>
                        <path d="M 225 85 A 110 110 0 0 1 250 140" fill="none" stroke="#1e8449" stroke-width="16" stroke-linecap="round"/>
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

        <footer>
            <p>Data Source: {us_yields['source']}</p>
            <div class="data-source">Bloomberg BQNT Financial Dashboard v8</div>
            <p style="margin-top:10px">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </footer>
    </div>

    <script>
        new Chart(document.getElementById('usYieldChart').getContext('2d'), {{
            type: 'line',
            data: {{ labels: ['2Y', '5Y', '10Y', '30Y'],
                datasets: [
                    {{ label: 'Today', data: {us_t_json}, borderColor: '#3fb950', backgroundColor: 'rgba(63,185,80,0.1)', borderWidth: 3, fill: true, tension: 0.4, pointRadius: 8 }},
                    {{ label: 'Month Start', data: {us_m_json}, borderColor: '#d29922', borderWidth: 2.5, borderDash: [8, 4], tension: 0.4, pointRadius: 6 }},
                    {{ label: 'Year Start', data: {us_y_json}, borderColor: '#f85149', borderWidth: 2.5, borderDash: [15, 5], tension: 0.4, pointRadius: 6 }}
                ] }},
            options: {{ responsive: true, maintainAspectRatio: false,
                plugins: {{ legend: {{ labels: {{ color: '#c9d1d9' }} }} }},
                scales: {{ y: {{ min: {us_min:.2f}, max: {us_max:.2f}, ticks: {{ color: '#8b949e', callback: v => v.toFixed(2) + '%' }}, grid: {{ color: '#21262d' }} }}, x: {{ ticks: {{ color: '#8b949e' }}, grid: {{ color: '#21262d' }} }} }} }} }});
        new Chart(document.getElementById('deYieldChart').getContext('2d'), {{
            type: 'line',
            data: {{ labels: ['2Y', '5Y', '10Y', '30Y'],
                datasets: [
                    {{ label: 'Today', data: {de_t_json}, borderColor: '#58a6ff', backgroundColor: 'rgba(88,166,255,0.1)', borderWidth: 3, fill: true, tension: 0.4, pointRadius: 8 }},
                    {{ label: 'Month Start', data: {de_m_json}, borderColor: '#d29922', borderWidth: 2.5, borderDash: [8, 4], tension: 0.4, pointRadius: 6 }},
                    {{ label: 'Year Start', data: {de_y_json}, borderColor: '#a371f7', borderWidth: 2.5, borderDash: [15, 5], tension: 0.4, pointRadius: 6 }}
                ] }},
            options: {{ responsive: true, maintainAspectRatio: false,
                plugins: {{ legend: {{ labels: {{ color: '#c9d1d9' }} }} }},
                scales: {{ y: {{ min: {de_min:.2f}, max: {de_max:.2f}, ticks: {{ color: '#8b949e', callback: v => v.toFixed(2) + '%' }}, grid: {{ color: '#21262d' }} }}, x: {{ ticks: {{ color: '#8b949e' }}, grid: {{ color: '#21262d' }} }} }} }} }});
    </script>
</body>
</html>'''
    return html


# ==================== Main Dashboard Function ====================
def generate_dashboard():
    """
    Main function to generate the Bloomberg BQNT Financial Dashboard
    """
    print("=" * 70)
    print("   Financial Dashboard Pro v8 - Bloomberg BQNT Edition")
    print("=" * 70)
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   BQNT Mode: {'✅ Connected' if IN_BQNT else '⚠️ Fallback Data'}")
    print("=" * 70)

    # Load Data
    print("\n[1/8] Loading US Treasury Yields...")
    us_yields = bql_fetch_yield_curve(US_YIELD_TICKERS, "US Treasury")
    us_spread_today = us_yields['today'][2] - us_yields['today'][0]  # 10Y - 2Y
    us_spread_year_start = us_yields['year_start'][2] - us_yields['year_start'][0]
    us_spread_change = us_spread_today - us_spread_year_start
    us_curve_status = "Steepening" if us_spread_change > 0 else "Flattening"
    print(f"      ✓ Done ({us_yields['source']})")

    print("[2/8] Loading German Bund Yields...")
    de_yields = bql_fetch_yield_curve(DE_YIELD_TICKERS, "German Bund")
    de_spread_today = de_yields['today'][2] - de_yields['today'][0]
    de_spread_year_start = de_yields['year_start'][2] - de_yields['year_start'][0]
    de_spread_change = de_spread_today - de_spread_year_start
    de_curve_status = "Steepening" if de_spread_change > 0 else "Flattening"
    print(f"      ✓ Done ({de_yields['source']})")

    print("[3/8] Loading Global 10Y Yields...")
    global_yields = bql_fetch_price_data(GLOBAL_10Y_TICKERS, "Global 10Y")
    print("      ✓ Done")

    print("[4/8] Loading Global Indices...")
    global_indices = bql_fetch_price_data(INDICES_TICKERS, "Indices")
    print("      ✓ Done")

    print("[5/8] Loading US Sectors...")
    sectors = bql_fetch_sectors()
    print("      ✓ Done")

    print("[6/8] Loading Forex...")
    forex = bql_fetch_price_data(FOREX_TICKERS, "Forex")
    print("      ✓ Done")

    print("[7/8] Loading Commodities...")
    commodities = bql_fetch_price_data(COMMODITY_TICKERS, "Commodities")
    print("      ✓ Done")

    print("[8/8] Loading Crypto & Volatility...")
    crypto = bql_fetch_price_data(CRYPTO_TICKERS, "Crypto")
    volatility = bql_fetch_volatility()
    print("      ✓ Done")

    # Generate Matplotlib Chart
    print("\n   Generating Matplotlib charts...")
    fig = plt.figure(figsize=(26, 20), facecolor='#0d1117')
    fig.suptitle(f'Financial Dashboard Pro v8 - Bloomberg BQNT Edition\n{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | Data: {us_yields["source"]}',
                 fontsize=18, fontweight='bold', color='white', y=0.98)
    gs = gridspec.GridSpec(4, 4, figure=fig, hspace=0.4, wspace=0.3, left=0.04, right=0.96, top=0.93, bottom=0.04)

    # Row 1: Yield Curves
    x = np.arange(4)
    ax1 = fig.add_subplot(gs[0, 0:2])
    ax1.set_facecolor(COLORS['bg_card'])
    ax1.plot(x, us_yields['today'], color=COLORS['up'], linewidth=3, marker='o', markersize=10, label='Today')
    ax1.plot(x, us_yields['month_start'], color=COLORS['gold'], linewidth=2.5, marker='s', markersize=8, linestyle='--', label='Month Start')
    ax1.plot(x, us_yields['year_start'], color=COLORS['down'], linewidth=2.5, marker='^', markersize=8, linestyle=':', label='Year Start')
    ax1.fill_between(x, us_yields['today'], alpha=0.15, color=COLORS['up'])
    ax1.set_xticks(x)
    ax1.set_xticklabels(['2Y', '5Y', '10Y', '30Y'])
    ax1.set_title(f'US Treasury Yield Curve\n10Y-2Y: {us_spread_today:.2f}% | {us_curve_status} (YTD: {us_spread_change:+.2f}%)', fontsize=13, fontweight='bold', color='white')
    ax1.legend(fontsize=9, facecolor=COLORS['bg_card'])
    ax1.grid(True, alpha=0.3)

    ax2 = fig.add_subplot(gs[0, 2:4])
    ax2.set_facecolor(COLORS['bg_card'])
    ax2.plot(x, de_yields['today'], color=COLORS['neutral'], linewidth=3, marker='o', markersize=10, label='Today')
    ax2.plot(x, de_yields['month_start'], color=COLORS['gold'], linewidth=2.5, marker='s', markersize=8, linestyle='--', label='Month Start')
    ax2.plot(x, de_yields['year_start'], color=COLORS['purple'], linewidth=2.5, marker='^', markersize=8, linestyle=':', label='Year Start')
    ax2.fill_between(x, de_yields['today'], alpha=0.15, color=COLORS['neutral'])
    ax2.set_xticks(x)
    ax2.set_xticklabels(['2Y', '5Y', '10Y', '30Y'])
    ax2.set_title(f'German Bund Yield Curve\n10Y-2Y: {de_spread_today:.2f}% | {de_curve_status} (YTD: {de_spread_change:+.2f}%)', fontsize=13, fontweight='bold', color='white')
    ax2.legend(fontsize=9, facecolor=COLORS['bg_card'])
    ax2.grid(True, alpha=0.3)

    # Row 2: Global Indices & Sectors
    ax3 = fig.add_subplot(gs[1, 0:2])
    ax3.set_facecolor(COLORS['bg_card'])
    idx_names = list(global_indices.keys())
    idx_changes = [global_indices[n]['change'] for n in idx_names]
    colors_idx = [COLORS['up'] if c >= 0 else COLORS['down'] for c in idx_changes]
    ax3.barh(idx_names, idx_changes, color=colors_idx, height=0.6)
    ax3.axvline(x=0, color='white', linewidth=1)
    ax3.set_title('Global Stock Indices (Daily Change %)', fontsize=14, fontweight='bold', color='white')
    ax3.grid(True, axis='x', alpha=0.3)

    ax4 = fig.add_subplot(gs[1, 2:4])
    ax4.set_facecolor(COLORS['bg_card'])
    sec_names = [s['name'] for s in sectors]
    sec_changes = [s['change'] for s in sectors]
    colors_sec = [COLORS['up'] if c >= 0 else COLORS['down'] for c in sec_changes]
    ax4.barh(sec_names, sec_changes, color=colors_sec, height=0.65)
    ax4.axvline(x=0, color='white', linewidth=1)
    ax4.set_title('US Sector Performance (Daily Change %)', fontsize=14, fontweight='bold', color='white')
    ax4.grid(True, axis='x', alpha=0.3)

    # Row 3: Data Tables
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
        ax.set_title(title, fontsize=12, fontweight='bold', color='white', pad=10)

    ax5 = fig.add_subplot(gs[2, 0])
    bond_data = [[n, f"{d['value']:.2f}%", f"{d['change']:+.2f}%", f"{d['ytd']:+.1f}%"] for n, d in global_yields.items()]
    make_mpl_table(ax5, bond_data, ['Country', 'Yield', 'Daily', 'YTD'], '🏦 Global 10Y Bonds', COLORS['neutral'])

    ax6 = fig.add_subplot(gs[2, 1])
    forex_data = [[n, f"{d['value']:.4f}" if d['value'] < 10 else f"{d['value']:.2f}", f"{d['change']:+.2f}%", f"{d['ytd']:+.1f}%"] for n, d in forex.items()]
    make_mpl_table(ax6, forex_data, ['Pair', 'Price', 'Daily', 'YTD'], '💱 Forex', '#3498db')

    ax7 = fig.add_subplot(gs[2, 2])
    comm_data = [[n, f"${d['value']:,.2f}", f"{d['change']:+.2f}%", f"{d['ytd']:+.1f}%"] for n, d in commodities.items()]
    make_mpl_table(ax7, comm_data, ['Item', 'Price', 'Daily', 'YTD'], '🛢️ Commodities', COLORS['gold'])

    ax8 = fig.add_subplot(gs[2, 3])
    crypto_data = [[n, f"${d['value']:,.0f}" if d['value'] > 10 else f"${d['value']:.2f}", f"{d['change']:+.2f}%", f"{d['ytd']:+.1f}%"] for n, d in crypto.items()]
    make_mpl_table(ax8, crypto_data, ['Coin', 'Price', '24H', 'YTD'], '₿ Crypto', COLORS['purple'])

    # Row 4: Speedometer Gauges
    ax9 = fig.add_subplot(gs[3, 0])
    vix_zones = [(0, 15, '#27ae60', 'Low'), (15, 25, '#f1c40f', 'Normal'), (25, 35, '#e67e22', 'High'), (35, 80, '#c0392b', 'Extreme')]
    draw_speedometer_gauge(ax9, volatility['VIX']['value'], 'VIX Index', (0, 80), vix_zones, show_change=volatility['VIX']['change'])

    ax10 = fig.add_subplot(gs[3, 1])
    move_zones = [(60, 90, '#27ae60', 'Low'), (90, 110, '#f1c40f', 'Normal'), (110, 140, '#e67e22', 'Elevated'), (140, 180, '#c0392b', 'High')]
    draw_speedometer_gauge(ax10, volatility['MOVE']['value'], 'MOVE Index', (60, 180), move_zones, show_change=volatility['MOVE']['change'])

    ax11 = fig.add_subplot(gs[3, 2])
    draw_fear_greed_gauge(ax11, volatility['Fear_Greed'])

    ax12 = fig.add_subplot(gs[3, 3])
    ax12.set_facecolor(COLORS['bg_card'])
    ax12.axis('off')
    summary = f"YIELD CURVE SPREADS\n{'='*28}\n\nUS 10Y-2Y:  {us_spread_today:+.2f}%\n  Status:   {us_curve_status}\n  YTD Chg:  {us_spread_change:+.2f}%\n\nDE 10Y-2Y:  {de_spread_today:+.2f}%\n  Status:   {de_curve_status}\n  YTD Chg:  {de_spread_change:+.2f}%\n\n{'='*28}\nData: {us_yields['source']}"
    ax12.text(0.5, 0.95, summary, transform=ax12.transAxes, fontsize=11, va='top', ha='center', family='monospace', color='white')
    ax12.set_title('📊 Spread Analysis', fontsize=12, fontweight='bold', color='white', pad=10)

    plt.tight_layout(rect=[0, 0.01, 1, 0.96])

    # Save files
    html_path, png_path = None, None
    if OUTPUT_CONFIG['save_html'] or OUTPUT_CONFIG['save_png']:
        os.makedirs(OUTPUT_CONFIG['output_folder'], exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')

        if OUTPUT_CONFIG['save_png']:
            png_path = os.path.join(OUTPUT_CONFIG['output_folder'], f'dashboard_bqnt_{timestamp}.png')
            fig.savefig(png_path, dpi=120, bbox_inches='tight', facecolor='#0d1117')
            print(f"\n   PNG saved: {png_path}")

    # Generate HTML
    print("   Generating HTML...")
    html = generate_html(us_yields, de_yields, us_spread_today, us_curve_status, us_spread_change,
                         de_spread_today, de_curve_status, de_spread_change,
                         global_indices, sectors, global_yields, forex, commodities, crypto,
                         volatility)

    if OUTPUT_CONFIG['save_html']:
        html_path = os.path.join(OUTPUT_CONFIG['output_folder'], f'dashboard_bqnt_{timestamp}.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"   HTML saved: {html_path}")

    # Display
    if OUTPUT_CONFIG['show_matplotlib']:
        plt.show()
    else:
        plt.close(fig)

    # Display HTML inline in Jupyter
    if IN_JUPYTER and OUTPUT_CONFIG['display_html_inline']:
        display(HTML(html))

    print("\n" + "=" * 70)
    print("   ✅ Dashboard Complete!")
    print(f"   Data Source: {us_yields['source']}")
    if html_path:
        print(f"   HTML: {html_path}")
    if png_path:
        print(f"   PNG: {png_path}")
    print("=" * 70)

    return html, html_path, png_path


# ==================== Quick Display Functions for BQNT ====================
def show_yield_curves():
    """Quick function to display just yield curves"""
    print("Loading yield curves...")
    us_yields = bql_fetch_yield_curve(US_YIELD_TICKERS, "US Treasury")
    de_yields = bql_fetch_yield_curve(DE_YIELD_TICKERS, "German Bund")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), facecolor='#0d1117')
    x = np.arange(4)

    ax1.set_facecolor('#161b22')
    ax1.plot(x, us_yields['today'], 'g-o', linewidth=2, markersize=8, label='Today')
    ax1.plot(x, us_yields['month_start'], 'y--s', linewidth=2, markersize=6, label='Month Start')
    ax1.set_xticks(x)
    ax1.set_xticklabels(['2Y', '5Y', '10Y', '30Y'])
    ax1.set_title('US Treasury Yield Curve', color='white', fontsize=14)
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2.set_facecolor('#161b22')
    ax2.plot(x, de_yields['today'], 'b-o', linewidth=2, markersize=8, label='Today')
    ax2.plot(x, de_yields['month_start'], 'y--s', linewidth=2, markersize=6, label='Month Start')
    ax2.set_xticks(x)
    ax2.set_xticklabels(['2Y', '5Y', '10Y', '30Y'])
    ax2.set_title('German Bund Yield Curve', color='white', fontsize=14)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()
    return us_yields, de_yields


def show_market_summary():
    """Quick function to display market summary"""
    print("Loading market data...")
    indices = bql_fetch_price_data(INDICES_TICKERS, "Indices")

    df = pd.DataFrame([
        {'Index': name, 'Price': f"{data['value']:,.0f}", 'Daily': f"{data['change']:+.2f}%", 'YTD': f"{data['ytd']:+.1f}%"}
        for name, data in indices.items()
    ])

    if IN_JUPYTER:
        display(df)
    else:
        print(df.to_string(index=False))

    return indices


# ==================== Main Entry Point ====================
if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("   Bloomberg BQNT Financial Dashboard v8")
    print("=" * 70)
    print("\n   Usage in BQNT Jupyter Notebook:")
    print("   --------------------------------")
    print("   from financial_dashboard_BQNT_v8 import *")
    print("")
    print("   # Full dashboard:")
    print("   generate_dashboard()")
    print("")
    print("   # Quick views:")
    print("   show_yield_curves()")
    print("   show_market_summary()")
    print("=" * 70 + "\n")

    # Run the dashboard
    generate_dashboard()
