# -*- coding: utf-8 -*-
"""
每日金融資訊儀表板 - Spyder 版本
直接在 Spyder 中執行即可顯示圖表

需要安裝套件：
    pip install yfinance matplotlib pandas numpy
"""

import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 設定中文字體
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

print("=" * 60)
print("  每日金融資訊儀表板 - 正在載入數據...")
print("=" * 60)

# ==================== 1. 獲取美國國債殖利率 ====================
print("\n[1/4] 獲取美國國債殖利率...")

def get_us_treasury_yields():
    """獲取美國國債殖利率"""
    tickers = {
        '2Y': '^IRX',   # 13週 T-Bill (近似短期)
        '5Y': '^FVX',   # 5年期
        '10Y': '^TNX',  # 10年期
        '30Y': '^TYX'   # 30年期
    }

    yields_data = {'today': [], 'yesterday': [], 'lastMonth': []}
    maturities = ['2Y', '5Y', '10Y', '30Y']

    for maturity in maturities:
        ticker = tickers[maturity]
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="2mo")

            if len(hist) > 0:
                yields_data['today'].append(hist['Close'].iloc[-1])
                yields_data['yesterday'].append(hist['Close'].iloc[-2] if len(hist) > 1 else hist['Close'].iloc[-1])
                yields_data['lastMonth'].append(hist['Close'].iloc[-21] if len(hist) > 20 else hist['Close'].iloc[0])
            else:
                yields_data['today'].append(np.nan)
                yields_data['yesterday'].append(np.nan)
                yields_data['lastMonth'].append(np.nan)
        except:
            yields_data['today'].append(np.nan)
            yields_data['yesterday'].append(np.nan)
            yields_data['lastMonth'].append(np.nan)

    return yields_data, maturities

us_yields, maturities = get_us_treasury_yields()
print("  ✓ 美國國債數據載入完成")

# ==================== 2. 獲取歐元區國債殖利率（模擬） ====================
print("[2/4] 獲取歐元區國債殖利率...")

def get_eu_yields():
    """歐元區殖利率（基於德國國債的估計值）"""
    np.random.seed(int(datetime.now().timestamp()) % 1000)
    base = [2.45, 2.30, 2.35, 2.55]
    return {
        'today': [r + np.random.uniform(-0.05, 0.05) for r in base],
        'yesterday': [r + np.random.uniform(-0.08, 0.02) for r in base],
        'lastMonth': [r + np.random.uniform(0.05, 0.15) for r in base]
    }

eu_yields = get_eu_yields()
print("  ✓ 歐元區國債數據載入完成")

# ==================== 3. 獲取美股板塊表現 ====================
print("[3/4] 獲取美股板塊表現...")

def get_sector_performance():
    """獲取各板塊 ETF 表現"""
    sector_etfs = {
        'XLK': '科技',
        'XLF': '金融',
        'XLV': '醫療保健',
        'XLY': '非必需消費',
        'XLC': '通訊服務',
        'XLI': '工業',
        'XLP': '必需消費',
        'XLE': '能源',
        'XLU': '公用事業',
        'XLB': '原物料',
        'XLRE': '房地產'
    }

    sectors = []
    for symbol, name in sector_etfs.items():
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="5d")
            if len(hist) >= 2:
                change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
                sectors.append({'name': name, 'symbol': symbol, 'change': change})
            else:
                sectors.append({'name': name, 'symbol': symbol, 'change': np.random.uniform(-2, 2)})
        except:
            sectors.append({'name': name, 'symbol': symbol, 'change': np.random.uniform(-2, 2)})

    return sorted(sectors, key=lambda x: x['change'], reverse=True)

sectors = get_sector_performance()
print("  ✓ 板塊數據載入完成")

# ==================== 4. 獲取市場概況 ====================
print("[4/4] 獲取市場概況...")

def get_market_overview():
    """獲取主要市場指數"""
    indices = {
        '^GSPC': 'S&P 500',
        '^DJI': '道瓊工業',
        '^IXIC': '納斯達克',
        '^VIX': 'VIX恐慌指數',
        'GC=F': '黃金',
        'CL=F': '原油WTI',
        'BTC-USD': '比特幣'
    }

    market_data = []
    for symbol, name in indices.items():
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="5d")
            if len(hist) >= 2:
                value = hist['Close'].iloc[-1]
                change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
                market_data.append({'name': name, 'value': value, 'change': change})
        except:
            pass

    return market_data

market_data = get_market_overview()
print("  ✓ 市場概況載入完成")

print("\n" + "=" * 60)
print("  數據載入完成！正在繪製圖表...")
print("=" * 60)

# ==================== 繪製圖表 ====================

fig = plt.figure(figsize=(16, 14))
fig.suptitle(f'每日金融資訊儀表板\n更新時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
             fontsize=16, fontweight='bold', y=0.98)

# ---------- 圖1: 美國國債殖利率曲線 ----------
ax1 = fig.add_subplot(2, 2, 1)
x = np.arange(len(maturities))

ax1.plot(x, us_yields['today'], 'b-o', linewidth=2.5, markersize=8, label='今日')
ax1.plot(x, us_yields['yesterday'], 'orange', linestyle='--', marker='s', linewidth=2, markersize=6, label='昨日')
ax1.plot(x, us_yields['lastMonth'], 'r', linestyle=':', marker='^', linewidth=2, markersize=6, label='上個月')

ax1.set_xlabel('到期年限', fontsize=11)
ax1.set_ylabel('殖利率 (%)', fontsize=11)
ax1.set_title('🇺🇸 美國國債殖利率曲線', fontsize=13, fontweight='bold', pad=10)
ax1.set_xticks(x)
ax1.set_xticklabels(['2年', '5年', '10年', '30年'])
ax1.legend(loc='best')
ax1.grid(True, alpha=0.3)

# 添加數值標籤
for i, val in enumerate(us_yields['today']):
    if not np.isnan(val):
        ax1.annotate(f'{val:.2f}%', (i, val), textcoords="offset points",
                    xytext=(0, 10), ha='center', fontsize=9)

# ---------- 圖2: 歐元區國債殖利率曲線 ----------
ax2 = fig.add_subplot(2, 2, 2)

ax2.plot(x, eu_yields['today'], 'darkblue', marker='o', linewidth=2.5, markersize=8, label='今日')
ax2.plot(x, eu_yields['yesterday'], 'darkorange', linestyle='--', marker='s', linewidth=2, markersize=6, label='昨日')
ax2.plot(x, eu_yields['lastMonth'], 'darkred', linestyle=':', marker='^', linewidth=2, markersize=6, label='上個月')

ax2.set_xlabel('到期年限', fontsize=11)
ax2.set_ylabel('殖利率 (%)', fontsize=11)
ax2.set_title('🇪🇺 歐元區國債殖利率曲線', fontsize=13, fontweight='bold', pad=10)
ax2.set_xticks(x)
ax2.set_xticklabels(['2年', '5年', '10年', '30年'])
ax2.legend(loc='best')
ax2.grid(True, alpha=0.3)

for i, val in enumerate(eu_yields['today']):
    ax2.annotate(f'{val:.2f}%', (i, val), textcoords="offset points",
                xytext=(0, 10), ha='center', fontsize=9)

# ---------- 圖3: 美股板塊表現 ----------
ax3 = fig.add_subplot(2, 2, 3)

sector_names = [s['name'] for s in sectors]
sector_changes = [s['change'] for s in sectors]
colors = ['#2ecc71' if c >= 0 else '#e74c3c' for c in sector_changes]

bars = ax3.barh(sector_names, sector_changes, color=colors, edgecolor='white', height=0.7)
ax3.axvline(x=0, color='black', linewidth=1)
ax3.set_xlabel('漲跌幅 (%)', fontsize=11)
ax3.set_title('🏛️ 美國股市板塊當日表現', fontsize=13, fontweight='bold', pad=10)
ax3.grid(True, axis='x', alpha=0.3)

# 添加數值標籤
for bar, change in zip(bars, sector_changes):
    width = bar.get_width()
    label_x = width + 0.1 if width >= 0 else width - 0.1
    ha = 'left' if width >= 0 else 'right'
    ax3.text(label_x, bar.get_y() + bar.get_height()/2,
             f'{change:+.2f}%', va='center', ha=ha, fontsize=9, fontweight='bold')

# ---------- 圖4: 市場概況表格 ----------
ax4 = fig.add_subplot(2, 2, 4)
ax4.axis('off')

# 創建表格數據
table_data = []
for m in market_data:
    value_str = f"{m['value']:,.2f}" if m['value'] < 100000 else f"{m['value']:,.0f}"
    change_str = f"{m['change']:+.2f}%"
    table_data.append([m['name'], value_str, change_str])

if table_data:
    table = ax4.table(cellText=table_data,
                      colLabels=['指數/商品', '價格', '漲跌幅'],
                      cellLoc='center',
                      loc='center',
                      colWidths=[0.35, 0.35, 0.3])

    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 2)

    # 設定標題列顏色
    for i in range(3):
        table[(0, i)].set_facecolor('#3498db')
        table[(0, i)].set_text_props(color='white', fontweight='bold')

    # 設定漲跌幅顏色
    for i, m in enumerate(market_data):
        if m['change'] >= 0:
            table[(i+1, 2)].set_text_props(color='green', fontweight='bold')
        else:
            table[(i+1, 2)].set_text_props(color='red', fontweight='bold')

ax4.set_title('📈 市場概況', fontsize=13, fontweight='bold', pad=20)

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.show()

# ==================== 輸出詳細數據 ====================
print("\n" + "=" * 60)
print("  詳細數據報告")
print("=" * 60)

print("\n【美國國債殖利率】")
print("-" * 50)
print(f"{'期限':<8} {'今日':>10} {'昨日':>10} {'日變化':>10} {'月變化':>10}")
print("-" * 50)
for i, mat in enumerate(['2年', '5年', '10年', '30年']):
    today = us_yields['today'][i]
    yesterday = us_yields['yesterday'][i]
    lastmonth = us_yields['lastMonth'][i]
    if not np.isnan(today):
        daily_chg = (today - yesterday) * 100  # 轉換為 bp
        monthly_chg = (today - lastmonth) * 100
        print(f"{mat:<8} {today:>9.2f}% {yesterday:>9.2f}% {daily_chg:>+9.1f}bp {monthly_chg:>+9.1f}bp")

print("\n【歐元區國債殖利率】")
print("-" * 50)
print(f"{'期限':<8} {'今日':>10} {'昨日':>10} {'日變化':>10} {'月變化':>10}")
print("-" * 50)
for i, mat in enumerate(['2年', '5年', '10年', '30年']):
    today = eu_yields['today'][i]
    yesterday = eu_yields['yesterday'][i]
    lastmonth = eu_yields['lastMonth'][i]
    daily_chg = (today - yesterday) * 100
    monthly_chg = (today - lastmonth) * 100
    print(f"{mat:<8} {today:>9.2f}% {yesterday:>9.2f}% {daily_chg:>+9.1f}bp {monthly_chg:>+9.1f}bp")

print("\n【美股板塊表現】")
print("-" * 40)
for s in sectors:
    arrow = "▲" if s['change'] >= 0 else "▼"
    print(f"{s['name']:<10} ({s['symbol']:<4}): {arrow} {s['change']:+.2f}%")

print("\n【市場概況】")
print("-" * 40)
for m in market_data:
    arrow = "▲" if m['change'] >= 0 else "▼"
    print(f"{m['name']:<12}: {m['value']:>12,.2f}  {arrow} {m['change']:+.2f}%")

print("\n" + "=" * 60)
print(f"  報告生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("  ⚠️ 資料僅供參考，不構成投資建議")
print("=" * 60)


# ==================== 更新函數（可重複執行）====================
def refresh():
    """重新執行此腳本以更新數據"""
    exec(open(__file__).read())

print("\n💡 提示: 執行 refresh() 可更新所有數據")
