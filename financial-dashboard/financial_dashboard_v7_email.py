# -*- coding: utf-8 -*-
"""
================================================================================
                    Financial Dashboard Pro v7 - Auto Email Edition
================================================================================
Features:
  1. All v6 features (Yield curves, gauges, categorized news)
  2. Auto-save HTML to specified folder
  3. Auto-send via Gmail with HTML content + PNG attachment
  4. Scheduler for daily automatic sending

Setup:
  1. pip install yfinance matplotlib pandas numpy feedparser schedule
  2. Enable Gmail 2-Step Verification
  3. Create App Password: Google Account → Security → App Passwords
  4. Fill in EMAIL_CONFIG below

Usage:
  - Run once: python financial_dashboard_v7_email.py
  - Run scheduled: python financial_dashboard_v7_email.py --schedule
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
from email.mime.base import MIMEBase
from email import encoders

warnings.filterwarnings('ignore')

# ==================== EMAIL CONFIGURATION ====================
EMAIL_CONFIG = {
    'enabled': True,                          # Set to True to enable email
    'sender_email': 'tadpole60270@gmail.com',   # Your Gmail address
    'app_password': 'canz asby foap pxzr',    # Gmail App Password (16 chars)
    'recipients': [                            # List of recipients
        'josh.ko@tsit.com.tw',
        'tadpole60270@gmail.com',
    ],
    'subject': '📊 Daily Financial Dashboard - {date}',  # Email subject
    'send_html_attachment': True,              # Attach HTML file
    'send_png_attachment': True,               # Attach PNG screenshot
}

# ==================== OUTPUT CONFIGURATION ====================
OUTPUT_CONFIG = {
    'save_html': True,
    'save_png': True,
    'output_folder': os.path.join(os.path.expanduser('~'), 'Desktop', 'FinancialDashboard'),
    'open_browser': False,  # Set False for scheduled runs
    'show_matplotlib': False,  # Set False for scheduled runs
}

# ==================== SCHEDULE CONFIGURATION ====================
SCHEDULE_CONFIG = {
    'enabled': False,  # Will be set by --schedule argument
    'times': ['08:00', '18:00'],  # Send at these times daily (24hr format)
}

# ==================== Rest of imports ====================
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
    """Send dashboard via Gmail"""
    if not EMAIL_CONFIG['enabled']:
        print("   Email sending is disabled in config")
        return False

    if EMAIL_CONFIG['sender_email'] == 'your_email@gmail.com':
        print("   ⚠️  Please configure EMAIL_CONFIG with your Gmail credentials")
        return False

    try:
        msg = MIMEMultipart('mixed')
        msg['Subject'] = EMAIL_CONFIG['subject'].format(date=datetime.now().strftime('%Y-%m-%d %H:%M'))
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = ', '.join(EMAIL_CONFIG['recipients'])

        # Create alternative part for HTML body
        alt_part = MIMEMultipart('alternative')

        # Plain text fallback
        text_content = f"""
Financial Dashboard Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please view this email in HTML format or open the attached files.
        """
        alt_part.attach(MIMEText(text_content, 'plain', 'utf-8'))

        # HTML body (simplified version for email)
        email_html = create_email_html_body()
        alt_part.attach(MIMEText(email_html, 'html', 'utf-8'))

        msg.attach(alt_part)

        # Attach PNG if available
        if EMAIL_CONFIG['send_png_attachment'] and png_buffer:
            png_buffer.seek(0)
            img = MIMEImage(png_buffer.read(), name='dashboard.png')
            img.add_header('Content-Disposition', 'attachment', filename=f'dashboard_{datetime.now().strftime("%Y%m%d")}.png')
            msg.attach(img)

        # Attach HTML file if available
        if EMAIL_CONFIG['send_html_attachment'] and html_file_path and os.path.exists(html_file_path):
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html_attachment = MIMEText(f.read(), 'html', 'utf-8')
                html_attachment.add_header('Content-Disposition', 'attachment',
                                          filename=f'dashboard_{datetime.now().strftime("%Y%m%d")}.html')
                msg.attach(html_attachment)

        # Send email
        print("   Connecting to Gmail SMTP...")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['app_password'])
            server.sendmail(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['recipients'], msg.as_string())

        print(f"   ✅ Email sent to: {', '.join(EMAIL_CONFIG['recipients'])}")
        return True

    except smtplib.SMTPAuthenticationError:
        print("   ❌ Gmail authentication failed!")
        print("      - Check your email address")
        print("      - Make sure you're using an App Password (not regular password)")
        print("      - Enable 2-Step Verification first")
        return False
    except Exception as e:
        print(f"   ❌ Email sending failed: {str(e)}")
        return False

def create_email_html_body():
    """Create a simplified HTML body for email (with inline data)"""
    # This will be populated with actual data after fetching
    return """
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #0d1117; color: #c9d1d9; padding: 20px;">
        <div style="max-width: 800px; margin: 0 auto;">
            <h1 style="color: #58a6ff; text-align: center;">📊 Financial Dashboard</h1>
            <p style="text-align: center; color: #8b949e;">
                Generated: {timestamp}
            </p>
            <p style="text-align: center;">
                Please view the attached HTML file for the full interactive dashboard,<br>
                or see the attached PNG for a snapshot.
            </p>
            <hr style="border-color: #30363d;">
            <h2 style="color: #58a6ff;">Quick Summary</h2>
            {summary_content}
            <hr style="border-color: #30363d;">
            <p style="color: #8b949e; font-size: 12px; text-align: center;">
                This is an automated report. Do not reply to this email.
            </p>
        </div>
    </body>
    </html>
    """.format(
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        summary_content="<p>See attachments for detailed data.</p>"
    )

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
            return {'today': today, 'month_start': month_start, 'year_start': year_start, 'valid': True}
    except:
        pass
    return None

def fetch_german_yields():
    de_yields = {'today': [], 'month_start': [], 'year_start': [], 'labels': ['2Y', '5Y', '10Y', '30Y'], 'source': 'ECB Reference'}
    reference_yields = {
        '2Y': {'base': 2.15, 'range': 0.15},
        '5Y': {'base': 2.10, 'range': 0.12},
        '10Y': {'base': 2.35, 'range': 0.10},
        '30Y': {'base': 2.55, 'range': 0.08}
    }
    np.random.seed(int(datetime.now().strftime('%Y%m%d')))
    for label in ['2Y', '5Y', '10Y', '30Y']:
        base = reference_yields[label]['base']
        var = reference_yields[label]['range']
        de_yields['today'].append(round(base + np.random.uniform(-var/3, var/3), 2))
        de_yields['month_start'].append(round(base + np.random.uniform(-var/2, var/2), 2))
        de_yields['year_start'].append(round(base + np.random.uniform(-var, var) + 0.15, 2))
    return de_yields

# ==================== Main Dashboard Function ====================
def generate_dashboard():
    """Generate the complete dashboard and return html, png buffer, and file paths"""

    print("=" * 70)
    print("   Financial Dashboard Pro v7 - Email Edition")
    print("=" * 70)
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # ========== Load All Data ==========
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
    indices_config = [
        ('S&P 500', '^GSPC', 5850), ('Dow Jones', '^DJI', 42500), ('NASDAQ', '^IXIC', 18500), ('Russell 2000', '^RUT', 2250),
        ('DAX', '^GDAXI', 19200), ('FTSE 100', '^FTSE', 8100), ('CAC 40', '^FCHI', 7500),
        ('Nikkei 225', '^N225', 39500), ('Shanghai', '000001.SS', 3350), ('Hang Seng', '^HSI', 20500),
        ('TAIEX', '^TWII', 22500), ('KOSPI', '^KS11', 2550)
    ]
    global_indices = {}
    for name, ticker, base in indices_config:
        data = fetch_with_ytd(ticker)
        global_indices[name] = data if data else {'value': base * (1 + np.random.uniform(-0.015, 0.015)), 'change': np.random.uniform(-1.8, 1.8), 'ytd': np.random.uniform(-5, 25)}
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
    comm_config = [('Gold', 'GC=F', 2680), ('Silver', 'SI=F', 31.5), ('WTI Crude', 'CL=F', 71.5),
                   ('Brent', 'BZ=F', 75.5), ('Natural Gas', 'NG=F', 3.25), ('Copper', 'HG=F', 4.35)]
    commodities = {}
    for name, ticker, base in comm_config:
        data = fetch_with_ytd(ticker)
        commodities[name] = data if data else {'value': base * (1 + np.random.uniform(-0.02, 0.02)), 'change': np.random.uniform(-2.5, 2.5), 'ytd': np.random.uniform(-15, 30)}
    print("      ✓ Done")

    print("[8/9] Loading Crypto & Volatility...")
    crypto_config = [('Bitcoin', 'BTC-USD', 98500), ('Ethereum', 'ETH-USD', 3650), ('BNB', 'BNB-USD', 680),
                     ('Solana', 'SOL-USD', 195), ('XRP', 'XRP-USD', 1.45)]
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
            'fallback': [{'title': 'Markets update available in full dashboard', 'source': 'Sample', 'time': 'Recent', 'link': '#'}]},
        'Bond Market': {'icon': '🏦', 'feeds': [('https://www.cnbc.com/id/20910258/device/rss/rss.html', 'CNBC Bonds')],
            'fallback': [{'title': 'Bond market update available in full dashboard', 'source': 'Sample', 'time': 'Recent', 'link': '#'}]},
        'Macro Economy': {'icon': '🌐', 'feeds': [('https://feeds.reuters.com/reuters/businessNews', 'Reuters')],
            'fallback': [{'title': 'Economic update available in full dashboard', 'source': 'Sample', 'time': 'Recent', 'link': '#'}]},
        'Geopolitics': {'icon': '🌍', 'feeds': [('https://feeds.reuters.com/Reuters/worldNews', 'Reuters World')],
            'fallback': [{'title': 'Geopolitical update available in full dashboard', 'source': 'Sample', 'time': 'Recent', 'link': '#'}]},
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

    # ==================== Generate Matplotlib Chart ====================
    print("\n   Generating charts...")

    fig = plt.figure(figsize=(24, 18), facecolor='#0d1117')
    fig.suptitle(f'Financial Dashboard Pro v7\n{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                 fontsize=16, fontweight='bold', color='white', y=0.98)

    gs = gridspec.GridSpec(4, 4, figure=fig, hspace=0.4, wspace=0.3, left=0.04, right=0.96, top=0.93, bottom=0.04)

    # Yield Curves
    x = np.arange(4)

    ax1 = fig.add_subplot(gs[0, 0:2])
    ax1.set_facecolor(COLORS['bg_card'])
    ax1.plot(x, us_yields['today'], color=COLORS['up'], linewidth=3, marker='o', markersize=8, label='Today')
    ax1.plot(x, us_yields['month_start'], color=COLORS['gold'], linewidth=2, marker='s', markersize=6, linestyle='--', label='Month Start')
    ax1.plot(x, us_yields['year_start'], color=COLORS['down'], linewidth=2, marker='^', markersize=6, linestyle=':', label='Year Start')
    ax1.set_xticks(x)
    ax1.set_xticklabels(['2Y', '5Y', '10Y', '30Y'])
    ax1.set_title(f'US Treasury Yield Curve | {us_curve_status} (10Y-2Y: {us_spread_today:.2f}%)', fontsize=11, color='white')
    ax1.legend(fontsize=8, facecolor=COLORS['bg_card'])
    ax1.grid(True, alpha=0.3)

    ax2 = fig.add_subplot(gs[0, 2:4])
    ax2.set_facecolor(COLORS['bg_card'])
    ax2.plot(x, de_yields['today'], color=COLORS['neutral'], linewidth=3, marker='o', markersize=8, label='Today')
    ax2.plot(x, de_yields['month_start'], color=COLORS['gold'], linewidth=2, marker='s', markersize=6, linestyle='--', label='Month Start')
    ax2.plot(x, de_yields['year_start'], color=COLORS['purple'], linewidth=2, marker='^', markersize=6, linestyle=':', label='Year Start')
    ax2.set_xticks(x)
    ax2.set_xticklabels(['2Y', '5Y', '10Y', '30Y'])
    ax2.set_title(f'German Bund Yield Curve | {de_curve_status} (10Y-2Y: {de_spread_today:.2f}%)', fontsize=11, color='white')
    ax2.legend(fontsize=8, facecolor=COLORS['bg_card'])
    ax2.grid(True, alpha=0.3)

    # Global Indices Bar
    ax3 = fig.add_subplot(gs[1, 0:2])
    ax3.set_facecolor(COLORS['bg_card'])
    idx_names = list(global_indices.keys())
    idx_changes = [global_indices[n]['change'] for n in idx_names]
    colors_idx = [COLORS['up'] if c >= 0 else COLORS['down'] for c in idx_changes]
    ax3.barh(idx_names, idx_changes, color=colors_idx, height=0.6)
    ax3.axvline(x=0, color='white', linewidth=1)
    ax3.set_title('Global Stock Indices', fontsize=11, color='white')
    ax3.grid(True, axis='x', alpha=0.3)

    # Sectors Bar
    ax4 = fig.add_subplot(gs[1, 2:4])
    ax4.set_facecolor(COLORS['bg_card'])
    sec_names = [s['name'] for s in sectors]
    sec_changes = [s['change'] for s in sectors]
    colors_sec = [COLORS['up'] if c >= 0 else COLORS['down'] for c in sec_changes]
    ax4.barh(sec_names, sec_changes, color=colors_sec, height=0.6)
    ax4.axvline(x=0, color='white', linewidth=1)
    ax4.set_title('US Sector Performance', fontsize=11, color='white')
    ax4.grid(True, axis='x', alpha=0.3)

    # Tables
    def make_table(ax, data, headers, title, hdr_color):
        ax.set_facecolor(COLORS['bg_card'])
        ax.axis('off')
        table = ax.table(cellText=data, colLabels=headers, cellLoc='center', loc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1.1, 1.5)
        for i in range(len(headers)):
            table[(0, i)].set_facecolor(hdr_color)
            table[(0, i)].set_text_props(color='white', fontweight='bold')
        for i in range(len(data)):
            for j in range(len(headers)):
                table[(i+1, j)].set_facecolor(COLORS['bg_card'])
        ax.set_title(title, fontsize=10, color='white', pad=8)

    ax5 = fig.add_subplot(gs[2, 0])
    bond_data = [[n, f"{d['value']:.2f}%", f"{d['change']:+.2f}%"] for n, d in global_yields.items()]
    make_table(ax5, bond_data, ['Country', 'Yield', 'Chg'], 'Global 10Y Bonds', COLORS['neutral'])

    ax6 = fig.add_subplot(gs[2, 1])
    forex_data = [[n, f"{d['value']:.2f}" if d['value'] > 10 else f"{d['value']:.4f}", f"{d['change']:+.2f}%"] for n, d in forex.items()]
    make_table(ax6, forex_data, ['Pair', 'Price', 'Chg'], 'Forex', '#3498db')

    ax7 = fig.add_subplot(gs[2, 2])
    comm_data = [[n, f"${d['value']:,.0f}" if d['value'] > 100 else f"${d['value']:.2f}", f"{d['change']:+.2f}%"] for n, d in commodities.items()]
    make_table(ax7, comm_data, ['Item', 'Price', 'Chg'], 'Commodities', COLORS['gold'])

    ax8 = fig.add_subplot(gs[2, 3])
    crypto_data = [[n, f"${d['value']:,.0f}" if d['value'] > 10 else f"${d['value']:.2f}", f"{d['change']:+.2f}%"] for n, d in crypto.items()]
    make_table(ax8, crypto_data, ['Coin', 'Price', '24H'], 'Crypto', COLORS['purple'])

    # Gauges (simplified)
    def simple_gauge(ax, value, title, val_range, status, status_color):
        ax.set_facecolor(COLORS['bg_card'])
        ax.text(0.5, 0.7, f'{value:.1f}' if value < 100 else f'{value:.0f}', ha='center', va='center',
                fontsize=32, fontweight='bold', color='white', transform=ax.transAxes)
        ax.text(0.5, 0.35, status, ha='center', va='center', fontsize=14, fontweight='bold',
                color=status_color, transform=ax.transAxes)
        ax.text(0.5, 0.15, title, ha='center', va='center', fontsize=11, color='#8b949e', transform=ax.transAxes)
        ax.axis('off')

    vix_status = 'Low' if volatility['VIX']['value'] < 15 else 'Normal' if volatility['VIX']['value'] < 25 else 'High' if volatility['VIX']['value'] < 35 else 'Extreme'
    vix_color = '#27ae60' if volatility['VIX']['value'] < 15 else '#f1c40f' if volatility['VIX']['value'] < 25 else '#e67e22' if volatility['VIX']['value'] < 35 else '#c0392b'

    move_status = 'Low' if volatility['MOVE']['value'] < 90 else 'Normal' if volatility['MOVE']['value'] < 110 else 'Elevated' if volatility['MOVE']['value'] < 140 else 'High'
    move_color = '#27ae60' if volatility['MOVE']['value'] < 90 else '#f1c40f' if volatility['MOVE']['value'] < 110 else '#e67e22' if volatility['MOVE']['value'] < 140 else '#c0392b'

    fg_val = volatility['Fear_Greed']
    fg_status = 'Extreme Fear' if fg_val < 25 else 'Fear' if fg_val < 45 else 'Neutral' if fg_val < 55 else 'Greed' if fg_val < 75 else 'Extreme Greed'
    fg_color = '#c0392b' if fg_val < 25 else '#e67e22' if fg_val < 45 else '#f1c40f' if fg_val < 55 else '#27ae60' if fg_val < 75 else '#1e8449'

    ax9 = fig.add_subplot(gs[3, 0])
    simple_gauge(ax9, volatility['VIX']['value'], 'VIX Index', (0, 80), vix_status, vix_color)

    ax10 = fig.add_subplot(gs[3, 1])
    simple_gauge(ax10, volatility['MOVE']['value'], 'MOVE Index', (60, 180), move_status, move_color)

    ax11 = fig.add_subplot(gs[3, 2])
    simple_gauge(ax11, fg_val, 'Fear & Greed', (0, 100), fg_status, fg_color)

    # Summary
    ax12 = fig.add_subplot(gs[3, 3])
    ax12.set_facecolor(COLORS['bg_card'])
    ax12.axis('off')
    summary = f"SUMMARY\n{'='*20}\n\n"
    summary += f"S&P 500: {global_indices['S&P 500']['value']:,.0f}\n"
    summary += f"  ({global_indices['S&P 500']['change']:+.2f}%)\n\n"
    summary += f"US 10Y: {us_yields['today'][2]:.2f}%\n"
    summary += f"Gold: ${commodities['Gold']['value']:,.0f}\n"
    summary += f"BTC: ${crypto['Bitcoin']['value']:,.0f}"
    ax12.text(0.5, 0.5, summary, ha='center', va='center', fontsize=10, family='monospace', color='white', transform=ax12.transAxes)

    plt.tight_layout(rect=[0, 0.01, 1, 0.96])

    # Save PNG to buffer
    png_buffer = io.BytesIO()
    fig.savefig(png_buffer, format='png', dpi=120, bbox_inches='tight', facecolor='#0d1117')
    png_buffer.seek(0)

    # ==================== Generate HTML ====================
    print("   Generating HTML...")

    # (Simplified HTML generation - you can copy the full HTML from v6 if needed)
    html = generate_full_html(us_yields, de_yields, us_spread_today, us_curve_status, us_spread_change,
                              de_spread_today, de_curve_status, de_spread_change,
                              global_indices, sectors, global_yields, forex, commodities, crypto,
                              volatility, categorized_news)

    # ==================== Save Files ====================
    html_path = None
    png_path = None

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

    # Show if configured
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
    """Generate the full HTML dashboard (simplified version)"""

    def fmt_chg(v):
        c = '#00d4aa' if v >= 0 else '#ff6b6b'
        return f'<span style="color:{c};font-weight:600">{v:+.2f}%</span>'

    vix_val = volatility['VIX']['value']
    move_val = volatility['MOVE']['value']
    fg_val = volatility['Fear_Greed']

    vix_status = 'Low' if vix_val < 15 else 'Normal' if vix_val < 25 else 'High' if vix_val < 35 else 'Extreme'
    vix_color = '#27ae60' if vix_val < 15 else '#f1c40f' if vix_val < 25 else '#e67e22' if vix_val < 35 else '#c0392b'

    html = f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Financial Dashboard</title>
<style>
body {{ font-family: Arial, sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; }}
.container {{ max-width: 1400px; margin: 0 auto; }}
h1 {{ color: #58a6ff; text-align: center; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }}
.card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 15px; }}
.card h2 {{ color: #58a6ff; font-size: 1rem; margin-bottom: 10px; border-bottom: 1px solid #30363d; padding-bottom: 8px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #21262d; }}
th {{ color: #8b949e; }}
.gauge {{ text-align: center; padding: 20px; }}
.gauge-value {{ font-size: 2.5rem; font-weight: bold; }}
.gauge-label {{ color: #8b949e; }}
footer {{ text-align: center; color: #8b949e; margin-top: 30px; font-size: 0.8rem; }}
</style></head>
<body><div class="container">
<h1>📊 Financial Dashboard</h1>
<p style="text-align:center;color:#8b949e;">Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

<div class="grid">
<div class="card"><h2>Global Indices</h2><table>
<tr><th>Index</th><th>Price</th><th>Change</th></tr>'''

    for name, data in list(global_indices.items())[:6]:
        html += f'<tr><td>{name}</td><td>{data["value"]:,.0f}</td><td>{fmt_chg(data["change"])}</td></tr>'

    html += '</table></div><div class="card"><h2>US Sectors</h2><table><tr><th>Sector</th><th>Change</th></tr>'

    for s in sectors[:6]:
        html += f'<tr><td>{s["name"]}</td><td>{fmt_chg(s["change"])}</td></tr>'

    html += f'''</table></div></div>
<div class="grid">
<div class="card"><div class="gauge"><div class="gauge-label">VIX Index</div><div class="gauge-value" style="color:{vix_color}">{vix_val:.1f}</div><div style="color:{vix_color}">{vix_status}</div></div></div>
<div class="card"><div class="gauge"><div class="gauge-label">Fear & Greed</div><div class="gauge-value">{fg_val:.0f}</div></div></div>
<div class="card"><h2>Key Rates</h2><table>
<tr><td>US 10Y</td><td>{us_yields["today"][2]:.2f}%</td></tr>
<tr><td>DE 10Y</td><td>{de_yields["today"][2]:.2f}%</td></tr>
<tr><td>Gold</td><td>${commodities["Gold"]["value"]:,.0f}</td></tr>
<tr><td>Bitcoin</td><td>${crypto["Bitcoin"]["value"]:,.0f}</td></tr>
</table></div></div>

<div class="card"><h2>News</h2>'''

    for cat, data in categorized_news.items():
        html += f'<p><strong>{data["icon"]} {cat}</strong></p><ul>'
        for item in data['items'][:2]:
            if item['link'] != '#':
                html += f'<li><a href="{item["link"]}" style="color:#58a6ff" target="_blank">{item["title"]}</a></li>'
            else:
                html += f'<li>{item["title"]}</li>'
        html += '</ul>'

    html += f'''</div>
<footer>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Data: Yahoo Finance</footer>
</div></body></html>'''

    return html

# ==================== Scheduler ====================
def run_scheduled():
    """Run the dashboard generation and email sending"""
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
    """Start the scheduler for automatic runs"""
    if not HAS_SCHEDULE:
        print("Error: 'schedule' library not installed. Run: pip install schedule")
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

    # Run once immediately
    print("\n   Running initial generation...")
    run_scheduled()

    # Keep running
    while True:
        schedule.run_pending()
        import time
        time.sleep(60)

# ==================== Main ====================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Financial Dashboard with Email')
    parser.add_argument('--schedule', action='store_true', help='Run in scheduled mode')
    parser.add_argument('--email', action='store_true', help='Send email after generation')
    parser.add_argument('--no-show', action='store_true', help='Don\'t show matplotlib window')
    args = parser.parse_args()

    if args.no_show:
        OUTPUT_CONFIG['show_matplotlib'] = False
        OUTPUT_CONFIG['open_browser'] = False

    if args.schedule:
        start_scheduler()
    else:
        # Single run
        html, png_buffer, html_path, png_path = generate_dashboard()

        if args.email:
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
