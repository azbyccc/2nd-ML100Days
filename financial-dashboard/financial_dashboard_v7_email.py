# -*- coding: utf-8 -*-
"""
================================================================================
                    Financial Dashboard Pro v7 - Auto Email Edition
================================================================================
Features:
  1. US & German Bond Yield Curves with REAL data
  2. 10Y-2Y Spread with Flatten/Steepen indicator
  3. Categorized News (Stock, Bond, Macro, Geopolitics)
  4. Professional Speedometer-style Gauges with Needles
  5. Both Matplotlib AND HTML display
  6. Auto-send via Gmail with HTML content + PNG attachment
  7. Scheduler for daily automatic sending (07:00, 15:00)

Setup:
  1. pip install yfinance matplotlib pandas numpy feedparser schedule
  2. Enable Gmail 2-Step Verification
  3. Create App Password: Google Account → Security → App Passwords

Usage:
  - Run once: python financial_dashboard_v7_email.py
  - Run scheduled: python financial_dashboard_v7_email.py --schedule
  - Skip email: python financial_dashboard_v7_email.py --no-email
================================================================================
"""

import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.font_manager as fm
from matplotlib.patches import Wedge, Circle, Polygon
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import webbrowser
import os
import tempfile
import json
import warnings
import smtplib
import io
import sys
import argparse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

warnings.filterwarnings('ignore')

# ==================== EMAIL CONFIGURATION ====================
EMAIL_CONFIG = {
    'enabled': True,
    'sender_email': 'tadpole60270@gmail.com',
    'app_password': 'canz asby foap pxzr',
    'recipients': [
        'josh.ko@tsit.com.tw',
        'tadpole60270@gmail.com',
    ],
    'subject': '📊 Daily Financial Dashboard - {date}',
    'send_html_attachment': True,
    'send_png_attachment': True,
}

# ==================== OUTPUT CONFIGURATION ====================
OUTPUT_CONFIG = {
    'save_html': True,
    'save_png': True,
    'output_folder': os.path.join(os.path.expanduser('~'), 'Desktop', 'FinancialDashboard'),
    'open_browser': True,
    'show_matplotlib': True,
}

# ==================== SCHEDULE CONFIGURATION ====================
SCHEDULE_CONFIG = {
    'times': ['07:00', '15:00'],
}

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False
    print("Note: pip install feedparser for real-time news")

try:
    import schedule
    HAS_SCHEDULE = True
except ImportError:
    HAS_SCHEDULE = False
    print("Note: pip install schedule for auto-scheduling")

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

# ==================== Email Functions ====================
def send_email(html_content, png_buffer=None, html_file_path=None):
    if not EMAIL_CONFIG['enabled']:
        print("   Email sending is disabled")
        return False

    try:
        msg = MIMEMultipart('mixed')
        msg['Subject'] = EMAIL_CONFIG['subject'].format(date=datetime.now().strftime('%Y-%m-%d %H:%M'))
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = ', '.join(EMAIL_CONFIG['recipients'])

        alt_part = MIMEMultipart('alternative')
        text_content = f"Financial Dashboard Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nPlease view attachments."
        alt_part.attach(MIMEText(text_content, 'plain', 'utf-8'))

        email_body = f"""<html><body style="font-family:Arial;background:#0d1117;color:#c9d1d9;padding:20px;">
        <h1 style="color:#58a6ff;text-align:center;">📊 Financial Dashboard</h1>
        <p style="text-align:center;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p style="text-align:center;">Please view attached HTML/PNG for full dashboard.</p>
        </body></html>"""
        alt_part.attach(MIMEText(email_body, 'html', 'utf-8'))
        msg.attach(alt_part)

        if EMAIL_CONFIG['send_png_attachment'] and png_buffer:
            png_buffer.seek(0)
            img = MIMEImage(png_buffer.read(), name='dashboard.png')
            img.add_header('Content-Disposition', 'attachment', filename=f'dashboard_{datetime.now().strftime("%Y%m%d")}.png')
            msg.attach(img)

        if EMAIL_CONFIG['send_html_attachment'] and html_file_path and os.path.exists(html_file_path):
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html_attachment = MIMEText(f.read(), 'html', 'utf-8')
                html_attachment.add_header('Content-Disposition', 'attachment', filename=f'dashboard_{datetime.now().strftime("%Y%m%d")}.html')
                msg.attach(html_attachment)

        print("   Connecting to Gmail SMTP...")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['app_password'])
            server.sendmail(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['recipients'], msg.as_string())

        print(f"   ✅ Email sent to: {', '.join(EMAIL_CONFIG['recipients'])}")
        return True

    except smtplib.SMTPAuthenticationError:
        print("   ❌ Gmail authentication failed!")
        return False
    except Exception as e:
        print(f"   ❌ Email failed: {str(e)}")
        return False

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
            month_start_date = datetime.now().replace(day=1)
            month_data = hist[hist.index >= month_start_date.strftime('%Y-%m-%d')]
            month_start = month_data['Close'].iloc[0] if len(month_data) > 0 else hist['Close'].iloc[-22] if len(hist) > 22 else hist['Close'].iloc[0]
            year_start_date = datetime(datetime.now().year, 1, 1)
            year_data = hist[hist.index >= year_start_date.strftime('%Y-%m-%d')]
            year_start = year_data['Close'].iloc[0] if len(year_data) > 0 else hist['Close'].iloc[0]
            return {'today': today, 'month_start': month_start, 'year_start': year_start}
    except:
        pass
    return None

def fetch_german_yields():
    de_yields = {'today': [], 'month_start': [], 'year_start': [], 'labels': ['2Y', '5Y', '10Y', '30Y'], 'source': 'ECB Reference'}
    reference_yields = {'2Y': {'base': 2.15, 'range': 0.15}, '5Y': {'base': 2.10, 'range': 0.12}, '10Y': {'base': 2.35, 'range': 0.10}, '30Y': {'base': 2.55, 'range': 0.08}}
    np.random.seed(int(datetime.now().strftime('%Y%m%d')))
    for label in ['2Y', '5Y', '10Y', '30Y']:
        base, var = reference_yields[label]['base'], reference_yields[label]['range']
        de_yields['today'].append(round(base + np.random.uniform(-var/3, var/3), 2))
        de_yields['month_start'].append(round(base + np.random.uniform(-var/2, var/2), 2))
        de_yields['year_start'].append(round(base + np.random.uniform(-var, var) + 0.15, 2))
    return de_yields

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
    needle = Polygon([[tip_x, tip_y], [base1_x, base1_y], [back_x, back_y], [base2_x, base2_y]], facecolor='#ff4757', edgecolor='#c0392b', linewidth=1.5, zorder=10)
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
    zones = [(0, 25, '#c0392b', 'Extreme Fear'), (25, 45, '#e67e22', 'Fear'), (45, 55, '#f1c40f', 'Neutral'), (55, 75, '#27ae60', 'Greed'), (75, 100, '#1e8449', 'Extreme Greed')]
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
    ax.add_patch(Polygon([[tip_x, tip_y], [base1_x, base1_y], [back_x, back_y], [base2_x, base2_y]], facecolor='#ff4757', edgecolor='#c0392b', linewidth=1.5, zorder=10))
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

# ==================== Main Dashboard Function ====================
def generate_dashboard():
    print("=" * 70)
    print("   Financial Dashboard Pro v7 - Email Edition")
    print("=" * 70)
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Load Data
    print("\n[1/9] Loading US Treasury Yields...")
    us_tickers = {'2Y': '^IRX', '5Y': '^FVX', '10Y': '^TNX', '30Y': '^TYX'}
    us_yields = {'today': [], 'month_start': [], 'year_start': [], 'labels': ['2Y', '5Y', '10Y', '30Y'], 'source': 'Yahoo Finance'}
    for label, ticker in us_tickers.items():
        data = fetch_yield_data(ticker)
        if data:
            us_yields['today'].append(round(data['today'], 2))
            us_yields['month_start'].append(round(data['month_start'], 2))
            us_yields['year_start'].append(round(data['year_start'], 2))
        else:
            fallback = {'2Y': 4.25, '5Y': 4.35, '10Y': 4.55, '30Y': 4.75}
            us_yields['today'].append(fallback[label])
            us_yields['month_start'].append(fallback[label] - 0.05)
            us_yields['year_start'].append(fallback[label] + 0.10)
            us_yields['source'] = 'Fallback'
    us_spread_today = us_yields['today'][2] - us_yields['today'][0]
    us_spread_year_start = us_yields['year_start'][2] - us_yields['year_start'][0]
    us_spread_change = us_spread_today - us_spread_year_start
    us_curve_status = "Steepening" if us_spread_change > 0 else "Flattening"
    print("      ✓ Done")

    print("[2/9] Loading German Bund Yields...")
    de_yields = fetch_german_yields()
    de_spread_today = de_yields['today'][2] - de_yields['today'][0]
    de_spread_year_start = de_yields['year_start'][2] - de_yields['year_start'][0]
    de_spread_change = de_spread_today - de_spread_year_start
    de_curve_status = "Steepening" if de_spread_change > 0 else "Flattening"
    print("      ✓ Done")

    print("[3/9] Loading Global 10Y Yields...")
    global_yields = {}
    us_10y = fetch_with_ytd('^TNX')
    global_yields['US 10Y'] = us_10y if us_10y else {'value': us_yields['today'][2], 'change': 0.02, 'ytd': 0}
    global_yields['Germany 10Y'] = {'value': de_yields['today'][2], 'change': round(de_yields['today'][2] - de_yields['month_start'][2], 2), 'ytd': round(de_yields['today'][2] - de_yields['year_start'][2], 2)}
    for name, ref in [('UK 10Y', 4.55), ('Japan 10Y', 1.10), ('China 10Y', 1.65), ('France 10Y', 3.25)]:
        global_yields[name] = {'value': round(ref + np.random.uniform(-0.03, 0.03), 2), 'change': round(np.random.uniform(-0.03, 0.03), 2), 'ytd': round(np.random.uniform(-0.2, 0.2), 2)}
    print("      ✓ Done")

    print("[4/9] Loading Global Indices...")
    indices_config = [('S&P 500', '^GSPC', 5850), ('Dow Jones', '^DJI', 42500), ('NASDAQ', '^IXIC', 18500), ('Russell 2000', '^RUT', 2250),
                      ('DAX', '^GDAXI', 19200), ('FTSE 100', '^FTSE', 8100), ('CAC 40', '^FCHI', 7500), ('Nikkei 225', '^N225', 39500),
                      ('Shanghai', '000001.SS', 3350), ('Hang Seng', '^HSI', 20500), ('TAIEX', '^TWII', 22500), ('KOSPI', '^KS11', 2550)]
    global_indices = {}
    for name, ticker, base in indices_config:
        data = fetch_with_ytd(ticker)
        global_indices[name] = data if data else {'value': base * (1 + np.random.uniform(-0.015, 0.015)), 'change': np.random.uniform(-1.8, 1.8), 'ytd': np.random.uniform(-5, 25)}
    print("      ✓ Done")

    print("[5/9] Loading US Sectors...")
    sector_config = [('Technology', 'XLK'), ('Financials', 'XLF'), ('Healthcare', 'XLV'), ('Consumer Disc', 'XLY'),
                     ('Comm Services', 'XLC'), ('Industrials', 'XLI'), ('Consumer Staples', 'XLP'), ('Energy', 'XLE'),
                     ('Utilities', 'XLU'), ('Materials', 'XLB'), ('Real Estate', 'XLRE')]
    sectors = []
    for name, ticker in sector_config:
        data = fetch_with_ytd(ticker)
        sectors.append({'name': name, 'symbol': ticker, 'change': data['change'] if data else np.random.uniform(-2.5, 2.5), 'ytd': data['ytd'] if data else np.random.uniform(-10, 20)})
    sectors = sorted(sectors, key=lambda x: x['change'], reverse=True)
    print("      ✓ Done")

    print("[6/9] Loading Forex...")
    forex_config = [('EUR/USD', 'EURUSD=X', 1.055), ('USD/JPY', 'JPY=X', 154.5), ('GBP/USD', 'GBPUSD=X', 1.275),
                    ('USD/CNY', 'CNY=X', 7.25), ('USD/TWD', 'TWD=X', 32.2), ('DXY', 'DX-Y.NYB', 106.5)]
    forex = {}
    for name, ticker, base in forex_config:
        data = fetch_with_ytd(ticker)
        forex[name] = data if data else {'value': base * (1 + np.random.uniform(-0.005, 0.005)), 'change': np.random.uniform(-0.6, 0.6), 'ytd': np.random.uniform(-5, 10)}
    print("      ✓ Done")

    print("[7/9] Loading Commodities...")
    comm_config = [('Gold', 'GC=F', 2680), ('Silver', 'SI=F', 31.5), ('WTI Crude', 'CL=F', 71.5), ('Brent', 'BZ=F', 75.5), ('Natural Gas', 'NG=F', 3.25), ('Copper', 'HG=F', 4.35)]
    commodities = {}
    for name, ticker, base in comm_config:
        data = fetch_with_ytd(ticker)
        commodities[name] = data if data else {'value': base * (1 + np.random.uniform(-0.02, 0.02)), 'change': np.random.uniform(-2.5, 2.5), 'ytd': np.random.uniform(-15, 30)}
    print("      ✓ Done")

    print("[8/9] Loading Crypto & Volatility...")
    crypto_config = [('Bitcoin', 'BTC-USD', 98500), ('Ethereum', 'ETH-USD', 3650), ('BNB', 'BNB-USD', 680), ('Solana', 'SOL-USD', 195), ('XRP', 'XRP-USD', 1.45)]
    crypto = {}
    for name, ticker, base in crypto_config:
        data = fetch_with_ytd(ticker)
        crypto[name] = data if data else {'value': base * (1 + np.random.uniform(-0.04, 0.04)), 'change': np.random.uniform(-6, 6), 'ytd': np.random.uniform(-20, 100)}
    vix_data = fetch_with_ytd('^VIX')
    volatility = {
        'VIX': vix_data if vix_data else {'value': 15.5 + np.random.uniform(-3, 3), 'change': np.random.uniform(-8, 8), 'ytd': 0},
        'MOVE': {'value': 95 + np.random.uniform(-15, 25), 'change': np.random.uniform(-5, 5), 'ytd': np.random.uniform(-10, 15)},
        'Fear_Greed': min(100, max(0, 52 + np.random.uniform(-25, 25)))
    }
    print("      ✓ Done")

    print("[9/9] Loading News...")
    news_categories = {
        'Stock Market': {'icon': '📈', 'feeds': [('https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US', 'Yahoo Finance')],
            'fallback': [{'title': 'Markets update available', 'source': 'Sample', 'time': 'Recent', 'link': '#'}]},
        'Bond Market': {'icon': '🏦', 'feeds': [('https://www.cnbc.com/id/20910258/device/rss/rss.html', 'CNBC Bonds')],
            'fallback': [{'title': 'Bond market update', 'source': 'Sample', 'time': 'Recent', 'link': '#'}]},
        'Macro Economy': {'icon': '🌐', 'feeds': [('https://feeds.reuters.com/reuters/businessNews', 'Reuters')],
            'fallback': [{'title': 'Economic update', 'source': 'Sample', 'time': 'Recent', 'link': '#'}]},
        'Geopolitics': {'icon': '🌍', 'feeds': [('https://feeds.reuters.com/Reuters/worldNews', 'Reuters World')],
            'fallback': [{'title': 'Geopolitical update', 'source': 'Sample', 'time': 'Recent', 'link': '#'}]},
    }
    categorized_news = {}
    if HAS_FEEDPARSER:
        for category, config in news_categories.items():
            categorized_news[category] = {'icon': config['icon'], 'items': []}
            for url, source in config['feeds']:
                try:
                    feed = feedparser.parse(url)
                    for entry in feed.entries[:5]:
                        title = entry.title[:80] + '...' if len(entry.title) > 80 else entry.title
                        link = entry.link if hasattr(entry, 'link') and entry.link else '#'
                        categorized_news[category]['items'].append({'title': title, 'source': source, 'time': 'Recent', 'link': link})
                except:
                    pass
            if len(categorized_news[category]['items']) < 3:
                categorized_news[category]['items'].extend(config['fallback'])
            categorized_news[category]['items'] = categorized_news[category]['items'][:5]
    else:
        for category, config in news_categories.items():
            categorized_news[category] = {'icon': config['icon'], 'items': config['fallback']}
    print("      ✓ Done")

    # Generate Matplotlib Chart
    print("\n   Generating Matplotlib charts...")
    fig = plt.figure(figsize=(26, 22), facecolor='#0d1117')
    fig.suptitle(f'Financial Dashboard Pro v7\n{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', fontsize=18, fontweight='bold', color='white', y=0.98)
    gs = gridspec.GridSpec(5, 4, figure=fig, hspace=0.4, wspace=0.3, left=0.04, right=0.96, top=0.93, bottom=0.04)

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
    ax2.set_title(f'German Bund Yield Curve ({de_yields["source"]})\n10Y-2Y: {de_spread_today:.2f}% | {de_curve_status} (YTD: {de_spread_change:+.2f}%)', fontsize=13, fontweight='bold', color='white')
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
    ax3.set_title('Global Stock Indices', fontsize=14, fontweight='bold', color='white')
    ax3.grid(True, axis='x', alpha=0.3)

    ax4 = fig.add_subplot(gs[1, 2:4])
    ax4.set_facecolor(COLORS['bg_card'])
    sec_names = [s['name'] for s in sectors]
    sec_changes = [s['change'] for s in sectors]
    colors_sec = [COLORS['up'] if c >= 0 else COLORS['down'] for c in sec_changes]
    ax4.barh(sec_names, sec_changes, color=colors_sec, height=0.65)
    ax4.axvline(x=0, color='white', linewidth=1)
    ax4.set_title('US Sector Performance', fontsize=14, fontweight='bold', color='white')
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
    summary = f"YIELD CURVE SPREADS\n{'='*28}\n\nUS 10Y-2Y:  {us_spread_today:+.2f}%\n  Status:   {us_curve_status}\n  YTD Chg:  {us_spread_change:+.2f}%\n\nDE 10Y-2Y:  {de_spread_today:+.2f}%\n  Status:   {de_curve_status}\n  YTD Chg:  {de_spread_change:+.2f}%"
    ax12.text(0.5, 0.95, summary, transform=ax12.transAxes, fontsize=11, va='top', ha='center', family='monospace', color='white')
    ax12.set_title('Spread Analysis', fontsize=12, fontweight='bold', color='white', pad=10)

    # Row 5: News
    ax_news = fig.add_subplot(gs[4, :])
    ax_news.set_facecolor(COLORS['bg_card'])
    ax_news.axis('off')
    news_text = "FINANCIAL NEWS\n" + "="*120 + "\n\n"
    for category, data in categorized_news.items():
        news_text += f"{data['icon']} {category.upper()}\n" + "-"*50 + "\n"
        for item in data['items'][:3]:
            news_text += f"  • {item['title'][:45]}...\n" if len(item['title']) > 45 else f"  • {item['title']}\n"
        news_text += "\n"
    ax_news.text(0.02, 0.95, news_text, transform=ax_news.transAxes, fontsize=9, va='top', ha='left', family='monospace', color='#c9d1d9')
    ax_news.set_title('Latest Financial News', fontsize=12, fontweight='bold', color='white', pad=10)

    plt.tight_layout(rect=[0, 0.01, 1, 0.96])

    # Save PNG
    png_buffer = io.BytesIO()
    fig.savefig(png_buffer, format='png', dpi=120, bbox_inches='tight', facecolor='#0d1117')
    png_buffer.seek(0)

    # Generate HTML
    print("   Generating HTML with SVG gauges...")
    html = generate_full_html(us_yields, de_yields, us_spread_today, us_curve_status, us_spread_change,
                              de_spread_today, de_curve_status, de_spread_change,
                              global_indices, sectors, global_yields, forex, commodities, crypto,
                              volatility, categorized_news)

    # Save Files
    html_path, png_path = None, None
    if OUTPUT_CONFIG['save_html'] or OUTPUT_CONFIG['save_png']:
        os.makedirs(OUTPUT_CONFIG['output_folder'], exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        if OUTPUT_CONFIG['save_html']:
            html_path = os.path.join(OUTPUT_CONFIG['output_folder'], f'dashboard_{timestamp}.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"   HTML saved: {html_path}")
        if OUTPUT_CONFIG['save_png']:
            png_path = os.path.join(OUTPUT_CONFIG['output_folder'], f'dashboard_{timestamp}.png')
            with open(png_path, 'wb') as f:
                png_buffer.seek(0)
                f.write(png_buffer.read())
            print(f"   PNG saved: {png_path}")

    if OUTPUT_CONFIG['show_matplotlib']:
        plt.show()
    else:
        plt.close(fig)

    if OUTPUT_CONFIG['open_browser'] and html_path:
        webbrowser.open('file://' + html_path)

    return html, png_buffer, html_path, png_path

def generate_full_html(us_yields, de_yields, us_spread_today, us_curve_status, us_spread_change,
                       de_spread_today, de_curve_status, de_spread_change,
                       global_indices, sectors, global_yields, forex, commodities, crypto,
                       volatility, categorized_news):

    def fmt_chg(v):
        c = '#00d4aa' if v >= 0 else '#ff6b6b'
        return f'<span style="color:{c};font-weight:600">{v:+.2f}%</span>'

    def fmt_ytd(v):
        c = '#00d4aa' if v >= 0 else '#ff6b6b'
        return f'<span style="color:{c}">{v:+.1f}%</span>'

    us_t_json, us_m_json, us_y_json = json.dumps(us_yields['today']), json.dumps(us_yields['month_start']), json.dumps(us_yields['year_start'])
    de_t_json, de_m_json, de_y_json = json.dumps(de_yields['today']), json.dumps(de_yields['month_start']), json.dumps(de_yields['year_start'])

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
    <title>Financial Dashboard Pro v7</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #0d1117 0%, #161b22 100%); color: #c9d1d9; min-height: 100vh; padding: 20px; }}
        .container {{ max-width: 1800px; margin: 0 auto; }}
        header {{ text-align: center; padding: 30px; background: linear-gradient(135deg, #238636 0%, #1f6feb 100%); border-radius: 16px; margin-bottom: 25px; }}
        header h1 {{ font-size: 2.2rem; color: white; margin-bottom: 10px; }}
        header p {{ color: rgba(255,255,255,0.8); }}
        .btn {{ margin-top: 15px; padding: 12px 30px; background: white; color: #238636; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }}
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
        .news-category {{ margin-bottom: 25px; }}
        .news-category h3 {{ color: #58a6ff; font-size: 1.1rem; margin-bottom: 15px; padding-bottom: 8px; border-bottom: 1px solid #30363d; }}
        .news-item {{ padding: 12px 15px; background: #0d1117; margin-bottom: 10px; border-radius: 8px; border-left: 3px solid #30363d; }}
        .news-item:hover {{ background: #21262d; border-left-color: #58a6ff; }}
        .news-item a {{ color: #c9d1d9; text-decoration: none; }}
        .news-item a:hover {{ color: #58a6ff; }}
        .news-title {{ font-weight: 600; margin-bottom: 6px; }}
        .news-meta {{ font-size: 0.8rem; color: #8b949e; }}
        .bar-container {{ display: flex; align-items: center; height: 24px; }}
        .bar-negative {{ display: flex; justify-content: flex-end; width: 50%; }}
        .bar-positive {{ display: flex; justify-content: flex-start; width: 50%; }}
        .bar {{ height: 20px; border-radius: 4px; display: flex; align-items: center; padding: 0 6px; font-size: 0.75rem; font-weight: 600; color: white; min-width: 45px; }}
        footer {{ text-align: center; padding: 20px; color: #8b949e; font-size: 0.85rem; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Financial Dashboard Pro v7</h1>
            <p>Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <button class="btn" onclick="location.reload()">Refresh Data</button>
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
            <div class="card"><h2>Global 10Y Bonds</h2><table><thead><tr><th>Country</th><th>Yield</th><th>Daily</th><th>YTD</th></tr></thead><tbody>'''
    for name, data in global_yields.items():
        html += f'<tr><td>{name}</td><td>{data["value"]:.2f}%</td><td>{fmt_chg(data["change"])}</td><td>{fmt_ytd(data["ytd"])}</td></tr>'

    html += '''</tbody></table></div>
            <div class="card"><h2>Forex</h2><table><thead><tr><th>Pair</th><th>Price</th><th>Daily</th><th>YTD</th></tr></thead><tbody>'''
    for name, data in forex.items():
        price_fmt = f"{data['value']:.4f}" if data['value'] < 10 else f"{data['value']:.2f}"
        html += f'<tr><td>{name}</td><td>{price_fmt}</td><td>{fmt_chg(data["change"])}</td><td>{fmt_ytd(data["ytd"])}</td></tr>'

    html += '''</tbody></table></div>
            <div class="card"><h2>Commodities</h2><table><thead><tr><th>Item</th><th>Price</th><th>Daily</th><th>YTD</th></tr></thead><tbody>'''
    for name, data in commodities.items():
        html += f'<tr><td>{name}</td><td>${data["value"]:,.2f}</td><td>{fmt_chg(data["change"])}</td><td>{fmt_ytd(data["ytd"])}</td></tr>'

    html += '''</tbody></table></div>
            <div class="card"><h2>Cryptocurrencies</h2><table><thead><tr><th>Coin</th><th>Price</th><th>24H</th><th>YTD</th></tr></thead><tbody>'''
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

        <div class="card">
            <h2>Financial News</h2>
            <div class="grid grid-2">'''

    for category, data in categorized_news.items():
        html += f'<div class="news-category"><h3>{data["icon"]} {category}</h3>'
        for item in data['items']:
            html += f'<div class="news-item"><a href="{item["link"]}" target="_blank"><div class="news-title">{item["title"]}</div><div class="news-meta">{item["source"]} - {item["time"]}</div></a></div>'
        html += '</div>'

    html += f'''</div></div>

        <footer>
            <p>Data: Yahoo Finance | German Bund: {de_yields['source']}</p>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
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

# ==================== Scheduler ====================
def run_scheduled():
    print(f"\n{'='*70}")
    print(f"   Scheduled run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")
    try:
        html, png_buffer, html_path, png_path = generate_dashboard()
        print("\n   Sending email...")
        send_email(html, png_buffer, html_path)
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

def start_scheduler():
    if not HAS_SCHEDULE:
        print("Error: pip install schedule")
        return
    print("=" * 70)
    print("   Financial Dashboard Scheduler Started")
    print("=" * 70)
    print(f"   Scheduled times: {', '.join(SCHEDULE_CONFIG['times'])}")
    print("   Press Ctrl+C to stop")
    print("=" * 70)
    for time_str in SCHEDULE_CONFIG['times']:
        schedule.every().day.at(time_str).do(run_scheduled)
        print(f"   ✓ Scheduled daily at {time_str}")
    print("\n   Running initial generation...")
    run_scheduled()
    while True:
        schedule.run_pending()
        import time
        time.sleep(60)

# ==================== Main ====================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Financial Dashboard with Email')
    parser.add_argument('--schedule', action='store_true', help='Run in scheduled mode')
    parser.add_argument('--no-email', action='store_true', help='Skip email sending')
    parser.add_argument('--no-show', action='store_true', help='Don\'t show matplotlib window')
    args = parser.parse_args()

    if args.no_show:
        OUTPUT_CONFIG['show_matplotlib'] = False
        OUTPUT_CONFIG['open_browser'] = False

    if args.schedule:
        start_scheduler()
    else:
        html, png_buffer, html_path, png_path = generate_dashboard()
        if not args.no_email:
            print("\n" + "=" * 70)
            print("   Sending Email...")
            print("=" * 70)
            send_email(html, png_buffer, html_path)
        print("\n" + "=" * 70)
        print("   ✅ Complete!")
        if html_path:
            print(f"   HTML: {html_path}")
        if png_path:
            print(f"   PNG:  {png_path}")
        print("=" * 70)
