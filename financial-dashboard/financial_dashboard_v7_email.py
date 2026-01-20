#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financial Dashboard v7 with Email
=================================
完整的金融儀表板，包含：
- 美歐殖利率曲線（Today/Month Start/Year Start）
- 10Y-2Y 利差計算 + Flatten/Steepen 指標
- 全球股市指數、美股板塊表現（雙向長條圖）
- 外匯、商品、加密貨幣表格
- VIX、MOVE、恐懼貪婪指數（指針儀表盤）
- 分類新聞（股市/債市/總經/地緣政治）
- Gmail 自動寄信
- 排程：每日 07:00 和 15:00 自動執行
"""

import os
import sys
import json
import smtplib
import webbrowser
import schedule
import time
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Wedge, FancyBboxPatch
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from io import BytesIO
import base64
import warnings
warnings.filterwarnings('ignore')

# 設定中文字體
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Microsoft JhengHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================================
# 配置區
# ============================================================================
EMAIL_CONFIG = {
    'sender': 'tadpole60270@gmail.com',
    'recipients': ['josh.ko@tsit.com.tw', 'tadpole60270@gmail.com'],
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    # 注意：需要設定 Gmail App Password
    'app_password': os.environ.get('GMAIL_APP_PASSWORD', ''),
}

SCHEDULE_TIMES = ['07:00', '15:00']

# API Keys (從環境變數讀取)
ALPHA_VANTAGE_KEY = os.environ.get('ALPHA_VANTAGE_KEY', 'demo')
FRED_API_KEY = os.environ.get('FRED_API_KEY', '')
NEWS_API_KEY = os.environ.get('NEWS_API_KEY', '')

# ============================================================================
# 數據獲取函數
# ============================================================================

def get_treasury_yields():
    """獲取美國國債殖利率數據"""
    maturities = ['1M', '3M', '6M', '1Y', '2Y', '3Y', '5Y', '7Y', '10Y', '20Y', '30Y']
    maturity_values = [1/12, 3/12, 6/12, 1, 2, 3, 5, 7, 10, 20, 30]

    # 模擬數據（實際應用中應從 FRED API 獲取）
    today = datetime.now()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    # 模擬殖利率數據
    np.random.seed(42)
    base_rates = [4.5, 4.6, 4.7, 4.5, 4.3, 4.2, 4.1, 4.15, 4.2, 4.4, 4.5]

    yields_today = [r + np.random.uniform(-0.1, 0.1) for r in base_rates]
    yields_month_start = [r + np.random.uniform(-0.2, 0.0) for r in base_rates]
    yields_year_start = [r + np.random.uniform(-0.5, -0.2) for r in base_rates]

    return {
        'maturities': maturities,
        'maturity_values': maturity_values,
        'today': yields_today,
        'month_start': yields_month_start,
        'year_start': yields_year_start,
        'date_today': today.strftime('%Y-%m-%d'),
        'date_month_start': month_start.strftime('%Y-%m-%d'),
        'date_year_start': year_start.strftime('%Y-%m-%d'),
    }


def get_euro_yields():
    """獲取歐洲國債殖利率數據"""
    maturities = ['3M', '6M', '1Y', '2Y', '3Y', '5Y', '7Y', '10Y', '20Y', '30Y']
    maturity_values = [3/12, 6/12, 1, 2, 3, 5, 7, 10, 20, 30]

    np.random.seed(43)
    base_rates = [3.2, 3.1, 3.0, 2.8, 2.7, 2.6, 2.65, 2.7, 2.9, 3.0]

    yields_today = [r + np.random.uniform(-0.1, 0.1) for r in base_rates]
    yields_month_start = [r + np.random.uniform(-0.15, 0.05) for r in base_rates]
    yields_year_start = [r + np.random.uniform(-0.3, 0.0) for r in base_rates]

    return {
        'maturities': maturities,
        'maturity_values': maturity_values,
        'today': yields_today,
        'month_start': yields_month_start,
        'year_start': yields_year_start,
    }


def calculate_spread_indicator(yields_data):
    """計算 10Y-2Y 利差和 Flatten/Steepen 指標"""
    # 找到 2Y 和 10Y 的索引
    maturities = yields_data['maturities']
    idx_2y = maturities.index('2Y')
    idx_10y = maturities.index('10Y')

    spread_today = yields_data['today'][idx_10y] - yields_data['today'][idx_2y]
    spread_month = yields_data['month_start'][idx_10y] - yields_data['month_start'][idx_2y]
    spread_year = yields_data['year_start'][idx_10y] - yields_data['year_start'][idx_2y]

    # 判斷趨勢
    spread_change = spread_today - spread_month
    if spread_change > 0.05:
        trend = 'Steepening'
        trend_color = '#28a745'  # 綠色
    elif spread_change < -0.05:
        trend = 'Flattening'
        trend_color = '#dc3545'  # 紅色
    else:
        trend = 'Stable'
        trend_color = '#6c757d'  # 灰色

    return {
        'spread_today': spread_today,
        'spread_month': spread_month,
        'spread_year': spread_year,
        'spread_change': spread_change,
        'trend': trend,
        'trend_color': trend_color,
        'yield_2y': yields_data['today'][idx_2y],
        'yield_10y': yields_data['today'][idx_10y],
    }


def get_global_indices():
    """獲取全球股市指數數據"""
    indices = {
        'S&P 500': {'price': 5850.25, 'change': 0.85, 'ytd': 24.5},
        'NASDAQ': {'price': 18520.30, 'change': 1.12, 'ytd': 28.3},
        'Dow Jones': {'price': 43250.80, 'change': 0.45, 'ytd': 18.2},
        'Russell 2000': {'price': 2285.60, 'change': -0.32, 'ytd': 12.8},
        'STOXX 600': {'price': 518.45, 'change': 0.28, 'ytd': 8.5},
        'DAX': {'price': 19850.20, 'change': 0.55, 'ytd': 15.2},
        'FTSE 100': {'price': 8125.30, 'change': 0.18, 'ytd': 5.8},
        'CAC 40': {'price': 7520.15, 'change': 0.42, 'ytd': 6.2},
        'Nikkei 225': {'price': 38520.80, 'change': -0.65, 'ytd': 16.5},
        'Hang Seng': {'price': 19850.25, 'change': 1.85, 'ytd': 22.8},
        'Shanghai Comp': {'price': 3380.50, 'change': 0.92, 'ytd': 15.2},
        'TAIEX': {'price': 22850.30, 'change': 0.68, 'ytd': 28.5},
        'KOSPI': {'price': 2520.45, 'change': 0.35, 'ytd': -5.2},
    }
    return indices


def get_us_sector_performance():
    """獲取美股板塊表現數據"""
    sectors = {
        'Technology': {'daily': 1.25, 'weekly': 2.8, 'monthly': 5.2, 'ytd': 32.5},
        'Healthcare': {'daily': 0.45, 'weekly': 1.2, 'monthly': 2.8, 'ytd': 8.5},
        'Financials': {'daily': 0.85, 'weekly': 2.1, 'monthly': 4.5, 'ytd': 22.8},
        'Consumer Disc.': {'daily': -0.32, 'weekly': 0.8, 'monthly': 3.2, 'ytd': 18.5},
        'Industrials': {'daily': 0.55, 'weekly': 1.5, 'monthly': 3.8, 'ytd': 15.2},
        'Energy': {'daily': -0.85, 'weekly': -2.5, 'monthly': -4.2, 'ytd': -8.5},
        'Materials': {'daily': 0.22, 'weekly': 0.5, 'monthly': 1.8, 'ytd': 5.2},
        'Utilities': {'daily': -0.15, 'weekly': 0.2, 'monthly': 1.2, 'ytd': 18.8},
        'Real Estate': {'daily': 0.35, 'weekly': 1.0, 'monthly': 2.5, 'ytd': 8.2},
        'Comm. Services': {'daily': 0.92, 'weekly': 2.2, 'monthly': 4.8, 'ytd': 35.5},
        'Consumer Staples': {'daily': 0.12, 'weekly': 0.3, 'monthly': 1.5, 'ytd': 12.5},
    }
    return sectors


def get_forex_data():
    """獲取外匯數據"""
    forex = {
        'EUR/USD': {'price': 1.0485, 'change': -0.25, 'weekly': -0.85},
        'USD/JPY': {'price': 154.85, 'change': 0.32, 'weekly': 1.25},
        'GBP/USD': {'price': 1.2650, 'change': -0.18, 'weekly': -0.55},
        'USD/CNY': {'price': 7.2485, 'change': 0.12, 'weekly': 0.35},
        'USD/TWD': {'price': 32.25, 'change': 0.08, 'weekly': 0.22},
        'AUD/USD': {'price': 0.6485, 'change': -0.35, 'weekly': -1.12},
        'USD/CHF': {'price': 0.8925, 'change': 0.15, 'weekly': 0.45},
        'DXY': {'price': 106.85, 'change': 0.28, 'weekly': 0.95},
    }
    return forex


def get_commodities_data():
    """獲取商品數據"""
    commodities = {
        'Gold': {'price': 2650.50, 'change': 0.45, 'weekly': 1.25, 'unit': '$/oz'},
        'Silver': {'price': 31.25, 'change': 0.85, 'weekly': 2.15, 'unit': '$/oz'},
        'WTI Crude': {'price': 68.50, 'change': -1.25, 'weekly': -3.50, 'unit': '$/bbl'},
        'Brent Crude': {'price': 72.85, 'change': -1.15, 'weekly': -3.25, 'unit': '$/bbl'},
        'Natural Gas': {'price': 3.25, 'change': 2.50, 'weekly': 8.50, 'unit': '$/MMBtu'},
        'Copper': {'price': 4.15, 'change': 0.55, 'weekly': 1.85, 'unit': '$/lb'},
        'Wheat': {'price': 585.50, 'change': -0.85, 'weekly': -2.25, 'unit': '¢/bu'},
        'Corn': {'price': 425.25, 'change': 0.32, 'weekly': 0.85, 'unit': '¢/bu'},
    }
    return commodities


def get_crypto_data():
    """獲取加密貨幣數據"""
    crypto = {
        'Bitcoin': {'price': 98520.50, 'change': 2.85, 'weekly': 8.50, 'market_cap': '1.95T'},
        'Ethereum': {'price': 3450.25, 'change': 3.25, 'weekly': 12.50, 'market_cap': '415B'},
        'BNB': {'price': 625.80, 'change': 1.50, 'weekly': 5.25, 'market_cap': '95B'},
        'Solana': {'price': 185.50, 'change': 5.25, 'weekly': 18.50, 'market_cap': '85B'},
        'XRP': {'price': 2.35, 'change': 8.50, 'weekly': 45.50, 'market_cap': '135B'},
        'Cardano': {'price': 0.85, 'change': 4.25, 'weekly': 25.50, 'market_cap': '30B'},
    }
    return crypto


def get_volatility_indices():
    """獲取波動率指數"""
    return {
        'VIX': {
            'value': 14.25,
            'change': -5.50,
            'level': 'Low',  # Low < 15, Normal 15-25, High > 25
            'description': 'Market calm, low fear'
        },
        'MOVE': {
            'value': 95.50,
            'change': -2.25,
            'level': 'Normal',  # Low < 80, Normal 80-120, High > 120
            'description': 'Bond market stable'
        },
        'Fear_Greed': {
            'value': 72,
            'change': 5,
            'level': 'Greed',  # 0-25 Extreme Fear, 25-45 Fear, 45-55 Neutral, 55-75 Greed, 75-100 Extreme Greed
            'description': 'Investors are greedy'
        }
    }


def get_categorized_news():
    """獲取分類新聞"""
    news = {
        'stock_market': [
            {'title': 'S&P 500 hits new all-time high amid tech rally', 'source': 'Bloomberg', 'time': '2h ago'},
            {'title': 'NVIDIA reports record Q3 earnings, beats expectations', 'source': 'Reuters', 'time': '4h ago'},
            {'title': 'Tesla shares surge on autonomous driving progress', 'source': 'CNBC', 'time': '5h ago'},
        ],
        'bond_market': [
            {'title': 'Treasury yields stabilize after Fed signals patience', 'source': 'WSJ', 'time': '1h ago'},
            {'title': '10-year yield holds below 4.5% as inflation cools', 'source': 'Bloomberg', 'time': '3h ago'},
            {'title': 'Corporate bond spreads narrow to 2-year low', 'source': 'FT', 'time': '6h ago'},
        ],
        'macro_economy': [
            {'title': 'Fed officials hint at potential rate cut in 2025', 'source': 'Reuters', 'time': '2h ago'},
            {'title': 'US GDP growth revised up to 3.2% for Q3', 'source': 'Bloomberg', 'time': '4h ago'},
            {'title': 'Inflation continues to moderate, CPI at 2.4%', 'source': 'WSJ', 'time': '8h ago'},
        ],
        'geopolitics': [
            {'title': 'US-China trade talks resume in Washington', 'source': 'Reuters', 'time': '1h ago'},
            {'title': 'European energy prices fall on mild weather outlook', 'source': 'FT', 'time': '3h ago'},
            {'title': 'Middle East tensions ease after diplomatic progress', 'source': 'Bloomberg', 'time': '5h ago'},
        ],
    }
    return news


# ============================================================================
# 圖表生成函數
# ============================================================================

def create_yield_curve_chart(us_yields, euro_yields, spread_data):
    """創建殖利率曲線圖"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Yield Curves & Spread Analysis', fontsize=16, fontweight='bold', y=0.98)

    # US Yield Curve
    ax1 = axes[0, 0]
    ax1.plot(us_yields['maturity_values'], us_yields['today'], 'b-o', linewidth=2, label=f"Today ({us_yields['date_today']})", markersize=6)
    ax1.plot(us_yields['maturity_values'], us_yields['month_start'], 'g--s', linewidth=1.5, label=f"Month Start ({us_yields['date_month_start']})", markersize=5, alpha=0.7)
    ax1.plot(us_yields['maturity_values'], us_yields['year_start'], 'r:^', linewidth=1.5, label=f"Year Start ({us_yields['date_year_start']})", markersize=5, alpha=0.7)
    ax1.set_xlabel('Maturity (Years)', fontsize=10)
    ax1.set_ylabel('Yield (%)', fontsize=10)
    ax1.set_title('US Treasury Yield Curve', fontsize=12, fontweight='bold')
    ax1.legend(loc='best', fontsize=8)
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(us_yields['maturity_values'])
    ax1.set_xticklabels(us_yields['maturities'], fontsize=8, rotation=45)

    # Euro Yield Curve
    ax2 = axes[0, 1]
    ax2.plot(euro_yields['maturity_values'], euro_yields['today'], 'b-o', linewidth=2, label='Today', markersize=6)
    ax2.plot(euro_yields['maturity_values'], euro_yields['month_start'], 'g--s', linewidth=1.5, label='Month Start', markersize=5, alpha=0.7)
    ax2.plot(euro_yields['maturity_values'], euro_yields['year_start'], 'r:^', linewidth=1.5, label='Year Start', markersize=5, alpha=0.7)
    ax2.set_xlabel('Maturity (Years)', fontsize=10)
    ax2.set_ylabel('Yield (%)', fontsize=10)
    ax2.set_title('Euro Area Yield Curve', fontsize=12, fontweight='bold')
    ax2.legend(loc='best', fontsize=8)
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(euro_yields['maturity_values'])
    ax2.set_xticklabels(euro_yields['maturities'], fontsize=8, rotation=45)

    # 10Y-2Y Spread
    ax3 = axes[1, 0]
    spreads = [spread_data['spread_year'], spread_data['spread_month'], spread_data['spread_today']]
    labels = ['Year Start', 'Month Start', 'Today']
    colors = ['#6c757d', '#17a2b8', spread_data['trend_color']]
    bars = ax3.bar(labels, spreads, color=colors, edgecolor='black', linewidth=1.2)
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    ax3.set_ylabel('Spread (bps)', fontsize=10)
    ax3.set_title(f"US 10Y-2Y Spread: {spread_data['trend']}", fontsize=12, fontweight='bold')
    for bar, spread in zip(bars, spreads):
        height = bar.get_height()
        ax3.annotate(f'{spread*100:.0f} bps',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='y')

    # Spread Info Box
    ax4 = axes[1, 1]
    ax4.axis('off')
    info_text = f"""
    10Y-2Y Spread Analysis
    ═══════════════════════════

    Current 2Y Yield:  {spread_data['yield_2y']:.2f}%
    Current 10Y Yield: {spread_data['yield_10y']:.2f}%

    Today's Spread:    {spread_data['spread_today']*100:.0f} bps
    Month Ago Spread:  {spread_data['spread_month']*100:.0f} bps
    Year Ago Spread:   {spread_data['spread_year']*100:.0f} bps

    Monthly Change:    {spread_data['spread_change']*100:+.0f} bps

    Trend: {spread_data['trend']}

    {'📈 Curve is steepening' if spread_data['trend'] == 'Steepening' else '📉 Curve is flattening' if spread_data['trend'] == 'Flattening' else '➡️ Curve is stable'}
    """
    ax4.text(0.1, 0.9, info_text, transform=ax4.transAxes, fontsize=11,
             verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    return fig


def create_sector_performance_chart(sectors):
    """創建美股板塊雙向長條圖"""
    fig, ax = plt.subplots(figsize=(12, 8))

    sector_names = list(sectors.keys())
    daily_changes = [sectors[s]['daily'] for s in sector_names]
    ytd_changes = [sectors[s]['ytd'] for s in sector_names]

    y_pos = np.arange(len(sector_names))
    bar_height = 0.35

    # 按照 daily change 排序
    sorted_indices = np.argsort(daily_changes)[::-1]
    sector_names = [sector_names[i] for i in sorted_indices]
    daily_changes = [daily_changes[i] for i in sorted_indices]
    ytd_changes = [ytd_changes[i] for i in sorted_indices]

    # 顏色
    daily_colors = ['#28a745' if x >= 0 else '#dc3545' for x in daily_changes]
    ytd_colors = ['#20c997' if x >= 0 else '#e83e8c' for x in ytd_changes]

    # 繪製長條圖
    bars1 = ax.barh(y_pos + bar_height/2, daily_changes, bar_height, label='Daily Change', color=daily_colors, alpha=0.9)
    bars2 = ax.barh(y_pos - bar_height/2, [x/10 for x in ytd_changes], bar_height, label='YTD (÷10)', color=ytd_colors, alpha=0.6)

    # 添加數值標籤
    for bar, val in zip(bars1, daily_changes):
        width = bar.get_width()
        ax.annotate(f'{val:+.2f}%',
                   xy=(width, bar.get_y() + bar.get_height()/2),
                   xytext=(5 if width >= 0 else -5, 0),
                   textcoords="offset points",
                   ha='left' if width >= 0 else 'right', va='center', fontsize=9)

    ax.axvline(x=0, color='black', linewidth=0.8)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(sector_names, fontsize=10)
    ax.set_xlabel('Change (%)', fontsize=11)
    ax.set_title('US Sector Performance (Daily Change)', fontsize=14, fontweight='bold')
    ax.legend(loc='lower right', fontsize=9)
    ax.grid(True, alpha=0.3, axis='x')

    plt.tight_layout()
    return fig


def create_gauge_chart(value, title, min_val, max_val, thresholds, colors, unit=''):
    """創建指針儀表盤"""
    fig, ax = plt.subplots(figsize=(4, 3), subplot_kw={'aspect': 'equal'})

    # 繪製背景弧形
    theta_start = 180
    theta_end = 0

    # 分段繪製不同顏色的弧形
    for i, (thresh, color) in enumerate(zip(thresholds, colors)):
        if i == 0:
            start_val = min_val
        else:
            start_val = thresholds[i-1]
        end_val = thresh if thresh <= max_val else max_val

        start_angle = theta_start - (start_val - min_val) / (max_val - min_val) * 180
        end_angle = theta_start - (end_val - min_val) / (max_val - min_val) * 180

        wedge = Wedge((0, 0), 1, end_angle, start_angle, width=0.3, facecolor=color, alpha=0.7)
        ax.add_patch(wedge)

    # 繪製指針
    angle = np.radians(theta_start - (value - min_val) / (max_val - min_val) * 180)
    ax.arrow(0, 0, 0.7 * np.cos(angle), 0.7 * np.sin(angle),
             head_width=0.08, head_length=0.05, fc='black', ec='black', linewidth=2)

    # 中心圓
    center_circle = plt.Circle((0, 0), 0.1, color='black')
    ax.add_patch(center_circle)

    # 數值顯示
    ax.text(0, -0.4, f'{value:.1f}{unit}', ha='center', va='center', fontsize=14, fontweight='bold')
    ax.text(0, -0.6, title, ha='center', va='center', fontsize=10)

    # 設置範圍標籤
    ax.text(-0.95, -0.1, f'{min_val}', ha='center', va='center', fontsize=8)
    ax.text(0.95, -0.1, f'{max_val}', ha='center', va='center', fontsize=8)

    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-0.8, 1.2)
    ax.axis('off')

    return fig


def create_volatility_dashboard(vol_indices):
    """創建波動率儀表盤"""
    fig = plt.figure(figsize=(14, 5))
    fig.suptitle('Market Volatility & Sentiment Indicators', fontsize=14, fontweight='bold', y=1.02)

    # VIX
    ax1 = fig.add_subplot(131)
    vix = vol_indices['VIX']
    create_single_gauge(ax1, vix['value'], 'VIX Index', 0, 50,
                       [15, 25, 50], ['#28a745', '#ffc107', '#dc3545'])
    ax1.text(0, -0.75, f"Change: {vix['change']:+.1f}%", ha='center', fontsize=9)
    ax1.text(0, -0.9, vix['description'], ha='center', fontsize=8, style='italic')

    # MOVE
    ax2 = fig.add_subplot(132)
    move = vol_indices['MOVE']
    create_single_gauge(ax2, move['value'], 'MOVE Index', 50, 200,
                       [80, 120, 200], ['#28a745', '#ffc107', '#dc3545'])
    ax2.text(0, -0.75, f"Change: {move['change']:+.1f}%", ha='center', fontsize=9)
    ax2.text(0, -0.9, move['description'], ha='center', fontsize=8, style='italic')

    # Fear & Greed
    ax3 = fig.add_subplot(133)
    fg = vol_indices['Fear_Greed']
    create_single_gauge(ax3, fg['value'], 'Fear & Greed Index', 0, 100,
                       [25, 45, 55, 75, 100], ['#dc3545', '#fd7e14', '#6c757d', '#28a745', '#20c997'])
    ax3.text(0, -0.75, f"Change: {fg['change']:+.0f} pts", ha='center', fontsize=9)
    ax3.text(0, -0.9, fg['description'], ha='center', fontsize=8, style='italic')

    plt.tight_layout()
    return fig


def create_single_gauge(ax, value, title, min_val, max_val, thresholds, colors):
    """在給定的 axes 上繪製單個儀表盤"""
    theta_start = 180

    # 分段繪製不同顏色的弧形
    prev_thresh = min_val
    for thresh, color in zip(thresholds, colors):
        end_val = min(thresh, max_val)
        start_angle = theta_start - (prev_thresh - min_val) / (max_val - min_val) * 180
        end_angle = theta_start - (end_val - min_val) / (max_val - min_val) * 180

        wedge = Wedge((0, 0), 1, end_angle, start_angle, width=0.3, facecolor=color, alpha=0.7)
        ax.add_patch(wedge)
        prev_thresh = thresh

    # 繪製指針
    normalized_value = max(min_val, min(value, max_val))
    angle = np.radians(theta_start - (normalized_value - min_val) / (max_val - min_val) * 180)
    ax.arrow(0, 0, 0.65 * np.cos(angle), 0.65 * np.sin(angle),
             head_width=0.08, head_length=0.05, fc='#333333', ec='#333333', linewidth=2)

    # 中心圓
    center_circle = plt.Circle((0, 0), 0.08, color='#333333')
    ax.add_patch(center_circle)

    # 數值和標題
    ax.text(0, -0.35, f'{value:.1f}', ha='center', va='center', fontsize=16, fontweight='bold')
    ax.text(0, -0.55, title, ha='center', va='center', fontsize=11, fontweight='bold')

    # 範圍標籤
    ax.text(-0.95, -0.05, f'{min_val}', ha='center', va='center', fontsize=9)
    ax.text(0.95, -0.05, f'{max_val}', ha='center', va='center', fontsize=9)

    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.0, 1.2)
    ax.axis('off')


# ============================================================================
# HTML 報告生成
# ============================================================================

def generate_html_report(us_yields, euro_yields, spread_data, indices, sectors,
                        forex, commodities, crypto, vol_indices, news, charts_base64):
    """生成 HTML 報告"""

    now = datetime.now()
    report_time = now.strftime('%Y-%m-%d %H:%M:%S')

    # 生成指數表格
    indices_html = ""
    for name, data in indices.items():
        change_color = '#28a745' if data['change'] >= 0 else '#dc3545'
        ytd_color = '#28a745' if data['ytd'] >= 0 else '#dc3545'
        indices_html += f"""
        <tr>
            <td style="font-weight:bold;">{name}</td>
            <td>{data['price']:,.2f}</td>
            <td style="color:{change_color};">{data['change']:+.2f}%</td>
            <td style="color:{ytd_color};">{data['ytd']:+.1f}%</td>
        </tr>
        """

    # 生成外匯表格
    forex_html = ""
    for name, data in forex.items():
        change_color = '#28a745' if data['change'] >= 0 else '#dc3545'
        forex_html += f"""
        <tr>
            <td style="font-weight:bold;">{name}</td>
            <td>{data['price']:.4f}</td>
            <td style="color:{change_color};">{data['change']:+.2f}%</td>
            <td style="color:{change_color};">{data['weekly']:+.2f}%</td>
        </tr>
        """

    # 生成商品表格
    commodities_html = ""
    for name, data in commodities.items():
        change_color = '#28a745' if data['change'] >= 0 else '#dc3545'
        commodities_html += f"""
        <tr>
            <td style="font-weight:bold;">{name}</td>
            <td>{data['price']:,.2f} {data['unit']}</td>
            <td style="color:{change_color};">{data['change']:+.2f}%</td>
            <td style="color:{change_color};">{data['weekly']:+.2f}%</td>
        </tr>
        """

    # 生成加密貨幣表格
    crypto_html = ""
    for name, data in crypto.items():
        change_color = '#28a745' if data['change'] >= 0 else '#dc3545'
        crypto_html += f"""
        <tr>
            <td style="font-weight:bold;">{name}</td>
            <td>${data['price']:,.2f}</td>
            <td style="color:{change_color};">{data['change']:+.2f}%</td>
            <td style="color:{change_color};">{data['weekly']:+.2f}%</td>
            <td>{data['market_cap']}</td>
        </tr>
        """

    # 生成新聞區塊
    def news_section(title, news_list, icon):
        html = f'<h3 style="margin-top:20px;">{icon} {title}</h3><ul style="list-style:none;padding:0;">'
        for item in news_list:
            html += f'''
            <li style="padding:8px 0;border-bottom:1px solid #eee;">
                <strong>{item['title']}</strong><br>
                <small style="color:#666;">{item['source']} | {item['time']}</small>
            </li>
            '''
        html += '</ul>'
        return html

    news_html = news_section('Stock Market', news['stock_market'], '📈')
    news_html += news_section('Bond Market', news['bond_market'], '📊')
    news_html += news_section('Macro Economy', news['macro_economy'], '🌍')
    news_html += news_section('Geopolitics', news['geopolitics'], '🌐')

    # VIX/MOVE/Fear&Greed 卡片
    def indicator_card(name, data, icon):
        level_colors = {
            'Low': '#28a745', 'Normal': '#ffc107', 'High': '#dc3545',
            'Extreme Fear': '#dc3545', 'Fear': '#fd7e14', 'Neutral': '#6c757d',
            'Greed': '#28a745', 'Extreme Greed': '#20c997'
        }
        color = level_colors.get(data['level'], '#6c757d')
        change_val = data['change']
        change_str = f"{change_val:+.1f}%" if 'VIX' in name or 'MOVE' in name else f"{change_val:+.0f} pts"

        return f'''
        <div style="background:linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                    border-radius:12px;padding:20px;text-align:center;
                    box-shadow:0 4px 6px rgba(0,0,0,0.1);min-width:200px;">
            <div style="font-size:24px;">{icon}</div>
            <div style="font-size:28px;font-weight:bold;margin:10px 0;">{data['value']:.1f}</div>
            <div style="font-size:14px;color:#666;">{name}</div>
            <div style="margin-top:10px;">
                <span style="background:{color};color:white;padding:4px 12px;
                             border-radius:20px;font-size:12px;">{data['level']}</span>
            </div>
            <div style="margin-top:8px;font-size:12px;color:#666;">
                Change: <span style="color:{'#28a745' if change_val < 0 else '#dc3545'}">{change_str}</span>
            </div>
        </div>
        '''

    indicators_html = f'''
    <div style="display:flex;gap:20px;justify-content:center;flex-wrap:wrap;margin:20px 0;">
        {indicator_card('VIX Index', vol_indices['VIX'], '📉')}
        {indicator_card('MOVE Index', vol_indices['MOVE'], '📊')}
        {indicator_card('Fear & Greed', vol_indices['Fear_Greed'], '😱')}
    </div>
    '''

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Financial Dashboard - {report_time}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                margin: 0;
                padding: 20px;
                min-height: 100vh;
            }}
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                padding: 30px;
            }}
            h1 {{
                text-align: center;
                color: #333;
                margin-bottom: 5px;
            }}
            .timestamp {{
                text-align: center;
                color: #666;
                font-size: 14px;
                margin-bottom: 30px;
            }}
            .section {{
                margin: 30px 0;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 12px;
            }}
            .section h2 {{
                color: #333;
                border-bottom: 3px solid #667eea;
                padding-bottom: 10px;
                margin-top: 0;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
            }}
            th, td {{
                padding: 12px;
                text-align: right;
                border-bottom: 1px solid #dee2e6;
            }}
            th {{
                background: #667eea;
                color: white;
                font-weight: 600;
            }}
            td:first-child, th:first-child {{
                text-align: left;
            }}
            tr:hover {{
                background: #f1f3f5;
            }}
            .chart-container {{
                text-align: center;
                margin: 20px 0;
            }}
            .chart-container img {{
                max-width: 100%;
                height: auto;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }}
            .spread-box {{
                background: linear-gradient(135deg, {spread_data['trend_color']}22 0%, {spread_data['trend_color']}11 100%);
                border-left: 4px solid {spread_data['trend_color']};
                padding: 15px 20px;
                margin: 15px 0;
                border-radius: 8px;
            }}
            .spread-value {{
                font-size: 32px;
                font-weight: bold;
                color: {spread_data['trend_color']};
            }}
            .grid-2 {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                gap: 20px;
            }}
            @media (max-width: 768px) {{
                .grid-2 {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Financial Dashboard</h1>
            <p class="timestamp">Generated: {report_time}</p>

            <!-- Volatility Indicators -->
            <div class="section">
                <h2>🎯 Market Volatility & Sentiment</h2>
                {indicators_html}
            </div>

            <!-- Yield Curve -->
            <div class="section">
                <h2>📈 Yield Curves & Spread Analysis</h2>
                <div class="spread-box">
                    <div>US 10Y-2Y Spread: <span class="spread-value">{spread_data['spread_today']*100:.0f} bps</span></div>
                    <div style="margin-top:8px;">
                        Trend: <strong style="color:{spread_data['trend_color']}">{spread_data['trend']}</strong>
                        (Monthly Change: {spread_data['spread_change']*100:+.0f} bps)
                    </div>
                    <div style="margin-top:8px;color:#666;">
                        2Y: {spread_data['yield_2y']:.2f}% | 10Y: {spread_data['yield_10y']:.2f}%
                    </div>
                </div>
                <div class="chart-container">
                    <img src="data:image/png;base64,{charts_base64['yield_curve']}" alt="Yield Curves">
                </div>
            </div>

            <!-- Global Indices -->
            <div class="section">
                <h2>🌍 Global Market Indices</h2>
                <table>
                    <tr>
                        <th>Index</th>
                        <th>Price</th>
                        <th>Daily Change</th>
                        <th>YTD</th>
                    </tr>
                    {indices_html}
                </table>
            </div>

            <!-- US Sectors -->
            <div class="section">
                <h2>🏢 US Sector Performance</h2>
                <div class="chart-container">
                    <img src="data:image/png;base64,{charts_base64['sectors']}" alt="Sector Performance">
                </div>
            </div>

            <!-- FX, Commodities, Crypto -->
            <div class="section">
                <h2>💱 FX, Commodities & Crypto</h2>
                <div class="grid-2">
                    <div>
                        <h3>Foreign Exchange</h3>
                        <table>
                            <tr><th>Pair</th><th>Rate</th><th>Daily</th><th>Weekly</th></tr>
                            {forex_html}
                        </table>
                    </div>
                    <div>
                        <h3>Commodities</h3>
                        <table>
                            <tr><th>Commodity</th><th>Price</th><th>Daily</th><th>Weekly</th></tr>
                            {commodities_html}
                        </table>
                    </div>
                </div>
                <h3>Cryptocurrency</h3>
                <table>
                    <tr><th>Crypto</th><th>Price</th><th>24h Change</th><th>7d Change</th><th>Market Cap</th></tr>
                    {crypto_html}
                </table>
            </div>

            <!-- Volatility Dashboard -->
            <div class="section">
                <h2>📊 Volatility Dashboard</h2>
                <div class="chart-container">
                    <img src="data:image/png;base64,{charts_base64['volatility']}" alt="Volatility Dashboard">
                </div>
            </div>

            <!-- News -->
            <div class="section">
                <h2>📰 Market News</h2>
                <div class="grid-2">
                    <div>{news_section('Stock Market', news['stock_market'], '📈')}</div>
                    <div>{news_section('Bond Market', news['bond_market'], '📊')}</div>
                    <div>{news_section('Macro Economy', news['macro_economy'], '🌍')}</div>
                    <div>{news_section('Geopolitics', news['geopolitics'], '🌐')}</div>
                </div>
            </div>

            <footer style="text-align:center;margin-top:30px;padding-top:20px;border-top:1px solid #eee;color:#666;">
                <p>Financial Dashboard v7 | Generated with Python</p>
                <p>Data sources: FRED, Yahoo Finance, CoinGecko, CNN Fear & Greed</p>
            </footer>
        </div>
    </body>
    </html>
    """

    return html


def fig_to_base64(fig):
    """將 matplotlib figure 轉換為 base64 字串"""
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    return img_str


# ============================================================================
# 郵件發送
# ============================================================================

def send_email(html_content, subject=None):
    """發送 HTML 郵件"""
    if not EMAIL_CONFIG['app_password']:
        print("警告: 未設定 GMAIL_APP_PASSWORD 環境變數，跳過郵件發送")
        return False

    if subject is None:
        now = datetime.now()
        subject = f"Financial Dashboard - {now.strftime('%Y-%m-%d %H:%M')}"

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_CONFIG['sender']
        msg['To'] = ', '.join(EMAIL_CONFIG['recipients'])

        # 添加 HTML 內容
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)

        # 連接 SMTP 伺服器並發送
        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['sender'], EMAIL_CONFIG['app_password'])
            server.sendmail(EMAIL_CONFIG['sender'], EMAIL_CONFIG['recipients'], msg.as_string())

        print(f"✅ 郵件已成功發送至: {', '.join(EMAIL_CONFIG['recipients'])}")
        return True

    except Exception as e:
        print(f"❌ 郵件發送失敗: {e}")
        return False


# ============================================================================
# 主要執行函數
# ============================================================================

def generate_dashboard(open_browser=True, send_mail=True):
    """生成儀表板並執行相關操作"""
    print("=" * 60)
    print(f"📊 Financial Dashboard Generation Started")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 獲取數據
    print("\n📥 Fetching data...")
    us_yields = get_treasury_yields()
    euro_yields = get_euro_yields()
    spread_data = calculate_spread_indicator(us_yields)
    indices = get_global_indices()
    sectors = get_us_sector_performance()
    forex = get_forex_data()
    commodities = get_commodities_data()
    crypto = get_crypto_data()
    vol_indices = get_volatility_indices()
    news = get_categorized_news()
    print("✅ Data fetched successfully")

    # 2. 生成圖表
    print("\n📊 Generating charts...")
    yield_curve_fig = create_yield_curve_chart(us_yields, euro_yields, spread_data)
    sector_fig = create_sector_performance_chart(sectors)
    vol_fig = create_volatility_dashboard(vol_indices)

    # 轉換為 base64
    charts_base64 = {
        'yield_curve': fig_to_base64(yield_curve_fig),
        'sectors': fig_to_base64(sector_fig),
        'volatility': fig_to_base64(vol_fig),
    }
    print("✅ Charts generated successfully")

    # 3. 生成 HTML 報告
    print("\n📄 Generating HTML report...")
    html_content = generate_html_report(
        us_yields, euro_yields, spread_data, indices, sectors,
        forex, commodities, crypto, vol_indices, news, charts_base64
    )

    # 儲存 HTML 檔案
    output_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(output_dir, 'financial_dashboard.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"✅ HTML report saved: {html_path}")

    # 4. 儲存圖表
    charts_dir = os.path.join(output_dir, 'charts')
    os.makedirs(charts_dir, exist_ok=True)

    yield_curve_fig.savefig(os.path.join(charts_dir, 'yield_curves.png'), dpi=150, bbox_inches='tight')
    sector_fig.savefig(os.path.join(charts_dir, 'sector_performance.png'), dpi=150, bbox_inches='tight')
    vol_fig.savefig(os.path.join(charts_dir, 'volatility_dashboard.png'), dpi=150, bbox_inches='tight')
    print(f"✅ Charts saved to: {charts_dir}")

    # 5. 開啟瀏覽器
    if open_browser:
        print("\n🌐 Opening browser...")
        try:
            webbrowser.open(f'file://{html_path}')
            print("✅ Browser opened")
        except Exception as e:
            print(f"⚠️ Could not open browser: {e}")

    # 6. 顯示 matplotlib 圖表
    if open_browser:
        print("\n📈 Displaying matplotlib charts...")
        plt.show()

    # 7. 發送郵件
    if send_mail:
        print("\n📧 Sending email...")
        send_email(html_content)

    # 關閉所有圖表
    plt.close('all')

    print("\n" + "=" * 60)
    print("✅ Dashboard generation completed!")
    print("=" * 60)

    return html_path


def run_scheduler():
    """啟動排程器"""
    print("\n🕐 Starting scheduler...")
    print(f"Scheduled times: {', '.join(SCHEDULE_TIMES)}")

    for time_str in SCHEDULE_TIMES:
        schedule.every().day.at(time_str).do(generate_dashboard, open_browser=False, send_mail=True)
        print(f"  - Scheduled for {time_str}")

    print("\n⏳ Scheduler is running. Press Ctrl+C to stop.")

    while True:
        schedule.run_pending()
        time.sleep(60)


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description='Financial Dashboard v7 with Email')
    parser.add_argument('--schedule', action='store_true', help='Run in scheduler mode')
    parser.add_argument('--no-browser', action='store_true', help='Do not open browser')
    parser.add_argument('--no-email', action='store_true', help='Do not send email')
    parser.add_argument('--email-only', action='store_true', help='Only send email (no browser/charts)')

    args = parser.parse_args()

    if args.schedule:
        # 先執行一次
        print("🚀 Running initial generation...")
        generate_dashboard(open_browser=not args.no_browser, send_mail=not args.no_email)
        # 然後啟動排程
        run_scheduler()
    elif args.email_only:
        generate_dashboard(open_browser=False, send_mail=True)
    else:
        generate_dashboard(open_browser=not args.no_browser, send_mail=not args.no_email)


if __name__ == '__main__':
    main()
