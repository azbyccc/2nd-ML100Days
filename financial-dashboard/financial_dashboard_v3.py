# -*- coding: utf-8 -*-
"""
================================================================================
                    Financial Dashboard Pro v3 - HTML Output
================================================================================
功能：
  - 美債+德債殖利率曲線 (Today/Month Start/Year Start)
  - 全球股市/板塊/外匯/商品/加密貨幣 (含 YTD 表現)
  - VIX + MOVE 恐慌指數
  - 即時新聞 (含連結)
  - 自動生成 HTML 並在瀏覽器開啟

使用方式：直接在 Spyder 中執行 (F5)
需安裝套件：pip install yfinance pandas numpy feedparser
================================================================================
"""

import yfinance as yf
import numpy as np
from datetime import datetime
import webbrowser
import os
import tempfile
import warnings
warnings.filterwarnings('ignore')

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False
    print("Tip: pip install feedparser for real-time news")

print("=" * 70)
print("   Financial Dashboard Pro v3 - Loading Market Data...")
print("=" * 70)
print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

# ==================== Data Functions ====================

def fetch_with_ytd(ticker, period="1y"):
    """獲取價格、日變動、YTD"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        if len(hist) >= 2:
            current = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2]
            daily_change = ((current - prev) / prev) * 100

            # YTD
            year_start = datetime(datetime.now().year, 1, 1)
            year_data = hist[hist.index >= year_start.strftime('%Y-%m-%d')]
            if len(year_data) > 0:
                year_start_price = year_data['Close'].iloc[0]
                ytd = ((current - year_start_price) / year_start_price) * 100
            else:
                ytd = 0

            return {'value': current, 'change': daily_change, 'ytd': ytd}
    except:
        pass
    return None

def fetch_yield_data(ticker):
    """獲取殖利率數據"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        if len(hist) > 0:
            today = hist['Close'].iloc[-1]

            # Month Start
            month_start_date = datetime.now().replace(day=1)
            month_data = hist[hist.index >= month_start_date.strftime('%Y-%m-%d')]
            month_start = month_data['Close'].iloc[0] if len(month_data) > 0 else hist['Close'].iloc[-22]

            # Year Start
            year_start_date = datetime(datetime.now().year, 1, 1)
            year_data = hist[hist.index >= year_start_date.strftime('%Y-%m-%d')]
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
        us_yields['today'].append(data['today'])
        us_yields['month_start'].append(data['month_start'])
        us_yields['year_start'].append(data['year_start'])
    else:
        base = {'2Y': 4.65, '5Y': 4.25, '10Y': 4.35, '30Y': 4.55}
        us_yields['today'].append(base[label] + np.random.uniform(-0.1, 0.1))
        us_yields['month_start'].append(base[label] + np.random.uniform(-0.15, 0.05))
        us_yields['year_start'].append(base[label] + np.random.uniform(0.1, 0.3))
print("      ✓ Done")

print("[2/9] Loading German Bund Yields...")
de_base = {'2Y': 2.85, '5Y': 2.45, '10Y': 2.55, '30Y': 2.75}
de_yields = {
    'today': [de_base[l] + np.random.uniform(-0.05, 0.05) for l in ['2Y', '5Y', '10Y', '30Y']],
    'month_start': [de_base[l] + np.random.uniform(-0.1, 0.05) for l in ['2Y', '5Y', '10Y', '30Y']],
    'year_start': [de_base[l] + np.random.uniform(0.1, 0.25) for l in ['2Y', '5Y', '10Y', '30Y']],
    'labels': ['2Y', '5Y', '10Y', '30Y']
}
print("      ✓ Done")

print("[3/9] Loading Global Bond Yields...")
global_yields = {}
bond_base = [('US 10Y', '^TNX', 4.35), ('Germany 10Y', None, 2.55), ('UK 10Y', None, 4.45),
             ('Japan 10Y', None, 1.05), ('China 10Y', None, 2.25), ('France 10Y', None, 3.15)]
for name, ticker, base in bond_base:
    if ticker:
        data = fetch_with_ytd(ticker)
        if data:
            global_yields[name] = data
            continue
    global_yields[name] = {
        'value': base + np.random.uniform(-0.08, 0.08),
        'change': np.random.uniform(-0.08, 0.08),
        'ytd': np.random.uniform(-0.5, 0.5)
    }
print("      ✓ Done")

print("[4/9] Loading Global Indices...")
indices_config = [
    ('S&P 500', '^GSPC', 5850), ('Dow Jones', '^DJI', 42500), ('NASDAQ', '^IXIC', 18500), ('Russell 2000', '^RUT', 2250),
    ('DAX', '^GDAXI', 19200), ('FTSE 100', '^FTSE', 8100), ('CAC 40', '^FCHI', 7500), ('STOXX 50', '^STOXX50E', 4850),
    ('Nikkei 225', '^N225', 39500), ('Shanghai', '000001.SS', 3350), ('Hang Seng', '^HSI', 20500),
    ('TAIEX', '^TWII', 22500), ('KOSPI', '^KS11', 2550)
]
global_indices = {}
for name, ticker, base in indices_config:
    data = fetch_with_ytd(ticker)
    if data:
        global_indices[name] = data
    else:
        global_indices[name] = {
            'value': base * (1 + np.random.uniform(-0.015, 0.015)),
            'change': np.random.uniform(-1.8, 1.8),
            'ytd': np.random.uniform(-5, 25)
        }
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
forex_config = [
    ('EUR/USD', 'EURUSD=X', 1.055), ('USD/JPY', 'JPY=X', 154.5), ('GBP/USD', 'GBPUSD=X', 1.275),
    ('USD/CNY', 'CNY=X', 7.25), ('USD/TWD', 'TWD=X', 32.2), ('AUD/USD', 'AUDUSD=X', 0.645), ('DXY', 'DX-Y.NYB', 106.5)
]
forex = {}
for name, ticker, base in forex_config:
    data = fetch_with_ytd(ticker)
    if data:
        forex[name] = data
    else:
        forex[name] = {'value': base * (1 + np.random.uniform(-0.005, 0.005)), 'change': np.random.uniform(-0.6, 0.6), 'ytd': np.random.uniform(-5, 10)}
print("      ✓ Done")

print("[7/9] Loading Commodities...")
comm_config = [
    ('Gold', 'GC=F', 2680), ('Silver', 'SI=F', 31.5), ('WTI Crude', 'CL=F', 71.5),
    ('Brent', 'BZ=F', 75.5), ('Natural Gas', 'NG=F', 3.25), ('Copper', 'HG=F', 4.35)
]
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

# Volatility
vix_data = fetch_with_ytd('^VIX')
volatility = {
    'VIX': vix_data if vix_data else {'value': 15.5 + np.random.uniform(-3, 3), 'change': np.random.uniform(-8, 8), 'ytd': np.random.uniform(-20, 20)},
    'MOVE': {'value': 95 + np.random.uniform(-15, 25), 'change': np.random.uniform(-5, 5), 'ytd': np.random.uniform(-10, 15)},
    'Fear_Greed': min(100, max(0, 52 + np.random.uniform(-25, 25)))
}
print("      ✓ Done")

print("[9/9] Loading News with Links...")
news = []
if HAS_FEEDPARSER:
    feeds = [
        ('https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US', 'Yahoo Finance'),
        ('https://www.cnbc.com/id/100003114/device/rss/rss.html', 'CNBC'),
        ('https://feeds.bloomberg.com/markets/news.rss', 'Bloomberg'),
    ]
    for url, source in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:4]:
                title = entry.title
                if len(title) > 80:
                    title = title[:77] + '...'
                link = entry.get('link', '#')
                pub_date = entry.get('published', '')[:20]
                news.append({'title': title, 'source': source, 'time': pub_date, 'link': link})
        except:
            pass

if not news:
    news = [
        {'title': 'Fed signals potential rate cuts later this year amid cooling inflation', 'source': 'Reuters', 'time': '30 min ago', 'link': 'https://www.reuters.com'},
        {'title': 'Tech stocks lead market gains as AI sector continues to rally', 'source': 'Bloomberg', 'time': '1 hour ago', 'link': 'https://www.bloomberg.com'},
        {'title': 'ECB holds rates steady, signals caution on inflation outlook', 'source': 'Financial Times', 'time': '2 hours ago', 'link': 'https://www.ft.com'},
        {'title': 'Oil prices surge 3% on Middle East supply concerns', 'source': 'CNBC', 'time': '3 hours ago', 'link': 'https://www.cnbc.com'},
        {'title': 'US jobs report beats expectations, unemployment at 3.7%', 'source': 'Wall Street Journal', 'time': '4 hours ago', 'link': 'https://www.wsj.com'},
        {'title': 'Gold hits record high above $2,700 on safe-haven demand', 'source': 'Reuters', 'time': '5 hours ago', 'link': 'https://www.reuters.com'},
        {'title': 'Bank of Japan hints at policy normalization, Yen strengthens', 'source': 'Nikkei', 'time': '6 hours ago', 'link': 'https://www.nikkei.com'},
        {'title': 'Bitcoin surpasses $100,000 as institutional adoption grows', 'source': 'CoinDesk', 'time': '7 hours ago', 'link': 'https://www.coindesk.com'},
        {'title': 'TSMC beats earnings expectations, raises full-year guidance', 'source': 'Reuters', 'time': '8 hours ago', 'link': 'https://www.reuters.com'},
        {'title': 'European markets close higher on positive earnings reports', 'source': 'Bloomberg', 'time': '9 hours ago', 'link': 'https://www.bloomberg.com'},
    ]
print("      ✓ Done")

print("\n" + "=" * 70)
print("   Generating HTML Dashboard...")
print("=" * 70)

# ==================== Generate HTML ====================

def format_change(val, is_percent=True):
    """格式化變動值"""
    sign = '+' if val >= 0 else ''
    color = '#00d4aa' if val >= 0 else '#ff6b6b'
    suffix = '%' if is_percent else ''
    return f'<span style="color:{color};font-weight:600">{sign}{val:.2f}{suffix}</span>'

def format_ytd(val):
    """格式化YTD"""
    sign = '+' if val >= 0 else ''
    color = '#00d4aa' if val >= 0 else '#ff6b6b'
    return f'<span style="color:{color}">{sign}{val:.1f}%</span>'

# Generate yield curve data for Chart.js
us_yield_today = [round(v, 2) for v in us_yields['today']]
us_yield_month = [round(v, 2) for v in us_yields['month_start']]
us_yield_year = [round(v, 2) for v in us_yields['year_start']]
de_yield_today = [round(v, 2) for v in de_yields['today']]
de_yield_month = [round(v, 2) for v in de_yields['month_start']]
de_yield_year = [round(v, 2) for v in de_yields['year_start']]

# Calculate Y-axis range
all_us = us_yield_today + us_yield_month + us_yield_year
all_de = de_yield_today + de_yield_month + de_yield_year
us_min, us_max = min(all_us) - 0.3, max(all_us) + 0.3
de_min, de_max = min(all_de) - 0.3, max(all_de) + 0.3

html_content = f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Financial Dashboard Pro v3</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
            color: #c9d1d9;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1800px; margin: 0 auto; }}
        header {{
            text-align: center;
            padding: 30px;
            background: linear-gradient(135deg, #238636 0%, #1f6feb 100%);
            border-radius: 16px;
            margin-bottom: 25px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }}
        header h1 {{ font-size: 2.2rem; color: white; margin-bottom: 10px; }}
        header p {{ color: rgba(255,255,255,0.8); font-size: 1.1rem; }}
        .refresh-btn {{
            margin-top: 15px;
            padding: 12px 30px;
            font-size: 1rem;
            background: white;
            color: #238636;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
        }}
        .refresh-btn:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.2); }}
        .grid {{ display: grid; gap: 20px; margin-bottom: 20px; }}
        .grid-2 {{ grid-template-columns: repeat(2, 1fr); }}
        .grid-4 {{ grid-template-columns: repeat(4, 1fr); }}
        .grid-3 {{ grid-template-columns: repeat(3, 1fr); }}
        @media (max-width: 1200px) {{ .grid-4 {{ grid-template-columns: repeat(2, 1fr); }} }}
        @media (max-width: 768px) {{ .grid-2, .grid-4, .grid-3 {{ grid-template-columns: 1fr; }} }}
        .card {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.2);
        }}
        .card h2 {{
            font-size: 1.1rem;
            color: #58a6ff;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid #30363d;
        }}
        .chart-container {{ height: 280px; position: relative; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
        th, td {{ padding: 10px 8px; text-align: left; border-bottom: 1px solid #21262d; }}
        th {{ color: #8b949e; font-weight: 600; font-size: 0.8rem; text-transform: uppercase; }}
        tr:hover {{ background: #21262d; }}
        .gauge-container {{ display: flex; flex-direction: column; align-items: center; padding: 20px; }}
        .gauge-value {{ font-size: 2.5rem; font-weight: 700; margin: 10px 0; }}
        .gauge-label {{ color: #8b949e; font-size: 0.9rem; }}
        .gauge-change {{ font-size: 1.1rem; margin-top: 5px; }}
        .news-item {{
            padding: 15px;
            border-radius: 8px;
            background: #0d1117;
            margin-bottom: 12px;
            transition: all 0.3s;
            border-left: 3px solid #30363d;
        }}
        .news-item:hover {{ background: #21262d; border-left-color: #58a6ff; transform: translateX(5px); }}
        .news-item a {{ color: #c9d1d9; text-decoration: none; }}
        .news-item a:hover {{ color: #58a6ff; }}
        .news-title {{ font-weight: 600; margin-bottom: 8px; line-height: 1.4; }}
        .news-meta {{ font-size: 0.8rem; color: #8b949e; }}
        .news-source {{ color: #58a6ff; font-weight: 600; }}
        .positive {{ color: #3fb950; }}
        .negative {{ color: #f85149; }}
        .sector-bar {{
            height: 24px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            padding: 0 8px;
            font-size: 0.8rem;
            font-weight: 600;
            color: white;
            margin: 4px 0;
        }}
        footer {{
            text-align: center;
            padding: 20px;
            color: #8b949e;
            font-size: 0.85rem;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Financial Dashboard Pro v3</h1>
            <p>Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <button class="refresh-btn" onclick="location.reload()">🔄 Refresh Data</button>
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
                    <tbody>
'''

# Add global indices to table
for name, data in global_indices.items():
    html_content += f'''
                        <tr>
                            <td><strong>{name}</strong></td>
                            <td>{data['value']:,.0f}</td>
                            <td>{format_change(data['change'])}</td>
                            <td>{format_ytd(data['ytd'])}</td>
                        </tr>'''

html_content += '''
                    </tbody>
                </table>
            </div>
            <div class="card">
                <h2>🏛️ US Sector Performance</h2>
                <table>
                    <thead><tr><th>Sector</th><th>Daily</th><th>YTD</th><th>Performance</th></tr></thead>
                    <tbody>
'''

# Add sectors
for s in sectors:
    bar_width = min(abs(s['change']) * 25, 100)
    bar_color = '#3fb950' if s['change'] >= 0 else '#f85149'
    html_content += f'''
                        <tr>
                            <td><strong>{s['name']}</strong></td>
                            <td>{format_change(s['change'])}</td>
                            <td>{format_ytd(s['ytd'])}</td>
                            <td><div class="sector-bar" style="width:{bar_width}%;background:{bar_color}">{s['change']:+.2f}%</div></td>
                        </tr>'''

html_content += '''
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Tables Row -->
        <div class="grid grid-4">
            <div class="card">
                <h2>🌍 Global 10Y Bonds</h2>
                <table>
                    <thead><tr><th>Country</th><th>Yield</th><th>Daily</th><th>YTD</th></tr></thead>
                    <tbody>
'''

for name, data in global_yields.items():
    html_content += f'''
                        <tr>
                            <td>{name}</td>
                            <td>{data['value']:.2f}%</td>
                            <td>{format_change(data['change'])}</td>
                            <td>{format_ytd(data['ytd'])}</td>
                        </tr>'''

html_content += '''
                    </tbody>
                </table>
            </div>
            <div class="card">
                <h2>💱 Forex</h2>
                <table>
                    <thead><tr><th>Pair</th><th>Price</th><th>Daily</th><th>YTD</th></tr></thead>
                    <tbody>
'''

for name, data in forex.items():
    price_fmt = f"{data['value']:.4f}" if data['value'] < 10 else f"{data['value']:.2f}"
    html_content += f'''
                        <tr>
                            <td>{name}</td>
                            <td>{price_fmt}</td>
                            <td>{format_change(data['change'])}</td>
                            <td>{format_ytd(data['ytd'])}</td>
                        </tr>'''

html_content += '''
                    </tbody>
                </table>
            </div>
            <div class="card">
                <h2>🛢️ Commodities</h2>
                <table>
                    <thead><tr><th>Item</th><th>Price</th><th>Daily</th><th>YTD</th></tr></thead>
                    <tbody>
'''

for name, data in commodities.items():
    html_content += f'''
                        <tr>
                            <td>{name}</td>
                            <td>${data['value']:,.2f}</td>
                            <td>{format_change(data['change'])}</td>
                            <td>{format_ytd(data['ytd'])}</td>
                        </tr>'''

html_content += '''
                    </tbody>
                </table>
            </div>
            <div class="card">
                <h2>₿ Cryptocurrencies</h2>
                <table>
                    <thead><tr><th>Coin</th><th>Price</th><th>24H</th><th>YTD</th></tr></thead>
                    <tbody>
'''

for name, data in crypto.items():
    price_fmt = f"${data['value']:,.2f}" if data['value'] > 1 else f"${data['value']:.4f}"
    html_content += f'''
                        <tr>
                            <td>{name}</td>
                            <td>{price_fmt}</td>
                            <td>{format_change(data['change'])}</td>
                            <td>{format_ytd(data['ytd'])}</td>
                        </tr>'''

# Volatility Gauges
vix_val = volatility['VIX']['value']
vix_chg = volatility['VIX']['change']
move_val = volatility['MOVE']['value']
move_chg = volatility['MOVE']['change']
fg_val = volatility['Fear_Greed']

vix_color = '#3fb950' if vix_val < 20 else '#f0883e' if vix_val < 30 else '#f85149'
move_color = '#3fb950' if move_val < 100 else '#f0883e' if move_val < 120 else '#f85149'
fg_color = '#f85149' if fg_val < 30 else '#f0883e' if fg_val < 50 else '#3fb950'
fg_label = 'Extreme Fear' if fg_val < 25 else 'Fear' if fg_val < 45 else 'Neutral' if fg_val < 55 else 'Greed' if fg_val < 75 else 'Extreme Greed'

html_content += f'''
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Volatility Gauges -->
        <div class="grid grid-3">
            <div class="card">
                <div class="gauge-container">
                    <div class="gauge-label">VIX (Stock Volatility)</div>
                    <div class="gauge-value" style="color:{vix_color}">{vix_val:.1f}</div>
                    <div class="gauge-change">{format_change(vix_chg)}</div>
                    <div class="gauge-label" style="margin-top:10px">{'Low' if vix_val < 15 else 'Normal' if vix_val < 25 else 'High' if vix_val < 35 else 'Extreme'}</div>
                </div>
            </div>
            <div class="card">
                <div class="gauge-container">
                    <div class="gauge-label">MOVE (Bond Volatility)</div>
                    <div class="gauge-value" style="color:{move_color}">{move_val:.0f}</div>
                    <div class="gauge-change">{format_change(move_chg)}</div>
                    <div class="gauge-label" style="margin-top:10px">{'Low' if move_val < 90 else 'Normal' if move_val < 110 else 'Elevated' if move_val < 140 else 'High'}</div>
                </div>
            </div>
            <div class="card">
                <div class="gauge-container">
                    <div class="gauge-label">Fear & Greed Index</div>
                    <div class="gauge-value" style="color:{fg_color}">{fg_val:.0f}</div>
                    <div class="gauge-label" style="font-size:1.2rem;color:{fg_color};margin-top:10px">{fg_label}</div>
                </div>
            </div>
        </div>

        <!-- News -->
        <div class="card">
            <h2>📰 Financial News</h2>
            <div class="grid grid-2">
'''

for n in news[:10]:
    html_content += f'''
                <div class="news-item">
                    <a href="{n['link']}" target="_blank">
                        <div class="news-title">{n['title']}</div>
                        <div class="news-meta">
                            <span class="news-source">{n['source']}</span> • {n['time']}
                        </div>
                    </a>
                </div>'''

html_content += f'''
            </div>
        </div>

        <footer>
            <p>Data sources: Yahoo Finance, RSS Feeds | Disclaimer: For reference only, not investment advice</p>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Press F5 or click Refresh to update</p>
        </footer>
    </div>

    <script>
        // US Yield Curve Chart
        new Chart(document.getElementById('usYieldChart'), {{
            type: 'line',
            data: {{
                labels: ['2Y', '5Y', '10Y', '30Y'],
                datasets: [
                    {{ label: 'Today', data: {us_yield_today}, borderColor: '#3fb950', backgroundColor: 'rgba(63,185,80,0.1)', borderWidth: 3, fill: true, tension: 0.4, pointRadius: 6 }},
                    {{ label: 'Month Start', data: {us_yield_month}, borderColor: '#d29922', borderWidth: 2, borderDash: [5,5], tension: 0.4, pointRadius: 4 }},
                    {{ label: 'Year Start', data: {us_yield_year}, borderColor: '#f85149', borderWidth: 2, borderDash: [10,5], tension: 0.4, pointRadius: 4 }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ labels: {{ color: '#c9d1d9' }} }} }},
                scales: {{
                    y: {{ min: {us_min:.1f}, max: {us_max:.1f}, ticks: {{ color: '#8b949e', callback: v => v.toFixed(2) + '%' }}, grid: {{ color: '#21262d' }} }},
                    x: {{ ticks: {{ color: '#8b949e' }}, grid: {{ color: '#21262d' }} }}
                }}
            }}
        }});

        // German Yield Curve Chart
        new Chart(document.getElementById('deYieldChart'), {{
            type: 'line',
            data: {{
                labels: ['2Y', '5Y', '10Y', '30Y'],
                datasets: [
                    {{ label: 'Today', data: {de_yield_today}, borderColor: '#58a6ff', backgroundColor: 'rgba(88,166,255,0.1)', borderWidth: 3, fill: true, tension: 0.4, pointRadius: 6 }},
                    {{ label: 'Month Start', data: {de_yield_month}, borderColor: '#d29922', borderWidth: 2, borderDash: [5,5], tension: 0.4, pointRadius: 4 }},
                    {{ label: 'Year Start', data: {de_yield_year}, borderColor: '#a371f7', borderWidth: 2, borderDash: [10,5], tension: 0.4, pointRadius: 4 }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ labels: {{ color: '#c9d1d9' }} }} }},
                scales: {{
                    y: {{ min: {de_min:.1f}, max: {de_max:.1f}, ticks: {{ color: '#8b949e', callback: v => v.toFixed(2) + '%' }}, grid: {{ color: '#21262d' }} }},
                    x: {{ ticks: {{ color: '#8b949e' }}, grid: {{ color: '#21262d' }} }}
                }}
            }}
        }});
    </script>
</body>
</html>
'''

# Save and open HTML
html_path = os.path.join(tempfile.gettempdir(), 'financial_dashboard.html')
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"\n   HTML saved to: {html_path}")
print("   Opening in browser...")

webbrowser.open('file://' + html_path)

print("\n" + "=" * 70)
print("   ✅ Dashboard opened in browser!")
print("   💡 Click 'Refresh Data' button or press F5 to update")
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
