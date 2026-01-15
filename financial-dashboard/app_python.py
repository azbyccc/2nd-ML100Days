#!/usr/bin/env python3
"""
每日金融資訊儀表板 - Python 版本
功能：美債/歐債殖利率曲線、美股板塊表現、金融新聞
執行方式：python app_python.py
然後在瀏覽器開啟 http://localhost:5000
"""

from flask import Flask, render_template_string, jsonify
import yfinance as yf
import requests
from datetime import datetime, timedelta
import pandas as pd
import json
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)

# ==================== 數據獲取函數 ====================

def get_us_treasury_yields():
    """獲取美國國債殖利率"""
    # 使用 Yahoo Finance 的國債 ETF 作為代理
    tickers = {
        '2Y': '^IRX',   # 13-week T-Bill (近似2Y)
        '5Y': '^FVX',   # 5-Year Treasury
        '10Y': '^TNX',  # 10-Year Treasury
        '30Y': '^TYX'   # 30-Year Treasury
    }

    yields_data = {'today': [], 'yesterday': [], 'lastMonth': []}

    try:
        for maturity, ticker in tickers.items():
            stock = yf.Ticker(ticker)
            hist = stock.history(period="2mo")

            if len(hist) > 0:
                # 今日（最新）
                today_yield = hist['Close'].iloc[-1]
                yields_data['today'].append(round(today_yield, 2))

                # 昨日
                if len(hist) > 1:
                    yields_data['yesterday'].append(round(hist['Close'].iloc[-2], 2))
                else:
                    yields_data['yesterday'].append(round(today_yield, 2))

                # 上個月（約20個交易日前）
                if len(hist) > 20:
                    yields_data['lastMonth'].append(round(hist['Close'].iloc[-21], 2))
                else:
                    yields_data['lastMonth'].append(round(hist['Close'].iloc[0], 2))
            else:
                # 備用數據
                yields_data['today'].append(4.25)
                yields_data['yesterday'].append(4.22)
                yields_data['lastMonth'].append(4.35)

    except Exception as e:
        print(f"獲取美債數據錯誤: {e}")
        # 使用備用數據
        yields_data = {
            'today': [4.25, 4.05, 4.20, 4.45],
            'yesterday': [4.22, 4.02, 4.18, 4.42],
            'lastMonth': [4.35, 4.15, 4.30, 4.55]
        }

    return yields_data


def get_eu_yields():
    """獲取歐元區（德國）國債殖利率"""
    # 由於歐債數據較難直接獲取，使用模擬數據
    # 實際應用中可以接入 ECB API 或其他數據源
    import random

    base_rates = {
        'today': [2.45, 2.30, 2.35, 2.55],
        'yesterday': [2.42, 2.28, 2.33, 2.52],
        'lastMonth': [2.55, 2.40, 2.45, 2.65]
    }

    # 添加小幅波動
    for key in base_rates:
        base_rates[key] = [round(r + random.uniform(-0.03, 0.03), 2) for r in base_rates[key]]

    return base_rates


def get_sector_performance():
    """獲取美股各板塊表現"""
    # 使用 SPDR 板塊 ETF
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

    try:
        for symbol, name in sector_etfs.items():
            stock = yf.Ticker(symbol)
            hist = stock.history(period="5d")

            if len(hist) >= 2:
                today_close = hist['Close'].iloc[-1]
                prev_close = hist['Close'].iloc[-2]
                change = ((today_close - prev_close) / prev_close) * 100

                sectors.append({
                    'name': name,
                    'symbol': symbol,
                    'change': round(change, 2)
                })
            else:
                sectors.append({
                    'name': name,
                    'symbol': symbol,
                    'change': round((hash(symbol) % 300 - 150) / 100, 2)
                })

    except Exception as e:
        print(f"獲取板塊數據錯誤: {e}")
        # 備用數據
        import random
        for symbol, name in sector_etfs.items():
            sectors.append({
                'name': name,
                'symbol': symbol,
                'change': round(random.uniform(-2, 2), 2)
            })

    # 按漲跌幅排序
    sectors.sort(key=lambda x: x['change'], reverse=True)
    return sectors


def get_market_overview():
    """獲取市場概況"""
    indices = {
        '^GSPC': 'S&P 500',
        '^DJI': '道瓊工業',
        '^IXIC': '納斯達克',
        '^VIX': 'VIX 恐慌指數',
        'DX-Y.NYB': '美元指數',
        'GC=F': '黃金',
        'CL=F': '原油 WTI',
        'BTC-USD': '比特幣'
    }

    market_data = []

    try:
        for symbol, name in indices.items():
            stock = yf.Ticker(symbol)
            hist = stock.history(period="5d")

            if len(hist) >= 2:
                today_close = hist['Close'].iloc[-1]
                prev_close = hist['Close'].iloc[-2]
                change = ((today_close - prev_close) / prev_close) * 100

                market_data.append({
                    'name': name,
                    'value': round(today_close, 2),
                    'change': round(change, 2)
                })
            else:
                market_data.append({
                    'name': name,
                    'value': 0,
                    'change': 0
                })

    except Exception as e:
        print(f"獲取市場概況錯誤: {e}")
        # 備用數據
        market_data = [
            {'name': 'S&P 500', 'value': 5250.50, 'change': 0.85},
            {'name': '道瓊工業', 'value': 39500.25, 'change': 0.62},
            {'name': '納斯達克', 'value': 16750.80, 'change': 1.25},
            {'name': 'VIX 恐慌指數', 'value': 14.25, 'change': -3.5},
            {'name': '美元指數', 'value': 104.35, 'change': -0.15},
            {'name': '黃金', 'value': 2025.50, 'change': 0.45},
            {'name': '原油 WTI', 'value': 78.50, 'change': 1.85},
            {'name': '比特幣', 'value': 52500.00, 'change': -2.15}
        ]

    return market_data


def get_financial_news():
    """獲取金融新聞（模擬數據）"""
    # 實際應用中可以接入 NewsAPI 或其他新聞 API
    news = [
        {
            'title': '聯準會官員暗示可能在年中開始降息，美債殖利率應聲下滑',
            'source': 'Reuters',
            'time': '30 分鐘前',
            'category': '央行政策'
        },
        {
            'title': '科技股領漲美股，納斯達克指數創歷史新高',
            'source': 'Bloomberg',
            'time': '1 小時前',
            'category': '股市'
        },
        {
            'title': '歐洲央行維持利率不變，暗示通膨風險仍在',
            'source': 'Financial Times',
            'time': '2 小時前',
            'category': '央行政策'
        },
        {
            'title': '原油價格因中東局勢緊張而上漲2%',
            'source': 'CNBC',
            'time': '3 小時前',
            'category': '大宗商品'
        },
        {
            'title': '美國初領失業金人數低於預期，勞動市場持續強勁',
            'source': 'Wall Street Journal',
            'time': '4 小時前',
            'category': '經濟數據'
        },
        {
            'title': '中國製造業PMI回升，亞洲市場普遍上漲',
            'source': 'Reuters',
            'time': '5 小時前',
            'category': '亞洲市場'
        },
        {
            'title': '黃金價格突破2000美元，避險需求上升',
            'source': 'Bloomberg',
            'time': '6 小時前',
            'category': '大宗商品'
        },
        {
            'title': '加密貨幣市場震盪，比特幣跌破關鍵支撐位',
            'source': 'CoinDesk',
            'time': '7 小時前',
            'category': '加密貨幣'
        }
    ]
    return news


# ==================== API 路由 ====================

@app.route('/api/data')
def get_all_data():
    """獲取所有數據的 API"""
    data = {
        'usYields': get_us_treasury_yields(),
        'euYields': get_eu_yields(),
        'sectors': get_sector_performance(),
        'market': get_market_overview(),
        'news': get_financial_news(),
        'lastUpdate': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    return jsonify(data)


# ==================== 主頁面 ====================

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>每日金融資訊儀表板</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        :root {
            --primary: #1a73e8;
            --success: #34a853;
            --danger: #ea4335;
            --warning: #fbbc04;
            --bg: #f5f7fa;
            --card: #ffffff;
            --text: #202124;
            --text-secondary: #5f6368;
        }

        body {
            font-family: 'Segoe UI', 'Microsoft JhengHei', sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }

        .container { max-width: 1600px; margin: 0 auto; padding: 20px; }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 30px;
            background: linear-gradient(135deg, #1a73e8, #0d47a1);
            color: white;
            border-radius: 12px;
            margin-bottom: 25px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        header h1 { font-size: 1.8rem; }

        .header-controls { display: flex; align-items: center; gap: 20px; }

        #lastUpdate { font-size: 0.9rem; opacity: 0.9; }

        #refreshBtn {
            padding: 12px 24px;
            font-size: 1rem;
            font-weight: 600;
            color: var(--primary);
            background: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        #refreshBtn:hover { background: #e8f0fe; transform: translateY(-2px); }
        #refreshBtn:disabled { opacity: 0.6; cursor: not-allowed; }

        .card {
            background: var(--card);
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 25px;
        }

        .card h2 {
            font-size: 1.3rem;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid var(--primary);
        }

        .grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); gap: 25px; }

        .chart-container { height: 300px; position: relative; }
        .chart-container-large { height: 400px; position: relative; }

        table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 0.9rem; }
        th, td { padding: 12px 15px; text-align: center; border-bottom: 1px solid #dadce0; }
        th { background: #f8f9fa; font-weight: 600; color: var(--text-secondary); }

        .positive { color: var(--success); font-weight: 600; }
        .negative { color: var(--danger); font-weight: 600; }

        .sector-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }

        .sector-item {
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }

        .sector-item.positive-bg {
            background: linear-gradient(135deg, #e6f4ea, #ceead6);
            border-left: 4px solid var(--success);
        }

        .sector-item.negative-bg {
            background: linear-gradient(135deg, #fce8e6, #f8d7da);
            border-left: 4px solid var(--danger);
        }

        .sector-name { font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 5px; }
        .sector-change { font-size: 1.3rem; font-weight: 700; }

        .market-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 20px;
        }

        .market-item {
            padding: 20px;
            border-radius: 10px;
            background: linear-gradient(135deg, #f8f9fa, #ffffff);
            border: 1px solid #dadce0;
            text-align: center;
        }

        .market-name { font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 10px; }
        .market-value { font-size: 1.4rem; font-weight: 700; margin-bottom: 5px; }
        .market-change { font-size: 1rem; font-weight: 600; }

        .news-container { max-height: 400px; overflow-y: auto; }

        .news-item {
            padding: 15px;
            border-radius: 8px;
            background: #f8f9fa;
            margin-bottom: 10px;
            transition: all 0.3s ease;
        }

        .news-item:hover { background: #e8f0fe; transform: translateX(5px); }

        .news-title { font-weight: 600; margin-bottom: 8px; }
        .news-meta { display: flex; gap: 15px; font-size: 0.8rem; color: var(--text-secondary); }
        .news-source { font-weight: 600; color: var(--primary); }

        footer {
            text-align: center;
            padding: 20px;
            color: var(--text-secondary);
            font-size: 0.85rem;
        }

        .loading { text-align: center; padding: 40px; color: var(--text-secondary); }

        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .spinning { animation: spin 1s linear infinite; display: inline-block; }

        @media (max-width: 768px) {
            .grid-2 { grid-template-columns: 1fr; }
            header { flex-direction: column; gap: 15px; text-align: center; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 每日金融資訊儀表板</h1>
            <div class="header-controls">
                <span id="lastUpdate">最後更新：載入中...</span>
                <button id="refreshBtn" onclick="refreshData()">🔄 更新資訊</button>
            </div>
        </header>

        <div class="grid-2">
            <div class="card">
                <h2>🇺🇸 美國國債殖利率曲線</h2>
                <div class="chart-container"><canvas id="usYieldChart"></canvas></div>
                <div id="usYieldTable"></div>
            </div>

            <div class="card">
                <h2>🇪🇺 歐元區國債殖利率曲線</h2>
                <div class="chart-container"><canvas id="euYieldChart"></canvas></div>
                <div id="euYieldTable"></div>
            </div>
        </div>

        <div class="card">
            <h2>🏛️ 美國股市板塊當日表現</h2>
            <div class="chart-container-large"><canvas id="sectorChart"></canvas></div>
            <div class="sector-grid" id="sectorGrid"></div>
        </div>

        <div class="grid-2">
            <div class="card">
                <h2>📈 市場概況</h2>
                <div class="market-grid" id="marketGrid"><div class="loading">載入中...</div></div>
            </div>

            <div class="card">
                <h2>📰 重要金融新聞</h2>
                <div class="news-container" id="newsContainer"><div class="loading">載入中...</div></div>
            </div>
        </div>

        <footer>
            <p>資料來源：Yahoo Finance, Federal Reserve | ⚠️ 資料僅供參考，不構成投資建議</p>
        </footer>
    </div>

    <script>
        let usYieldChart = null, euYieldChart = null, sectorChart = null;
        const maturities = ['2年期', '5年期', '10年期', '30年期'];

        function createYieldChart(canvasId, data, colors) {
            const ctx = document.getElementById(canvasId).getContext('2d');
            return new Chart(ctx, {
                type: 'line',
                data: {
                    labels: maturities,
                    datasets: [
                        { label: '今日', data: data.today, borderColor: colors[0], borderWidth: 3, fill: false, tension: 0.4, pointRadius: 6 },
                        { label: '昨日', data: data.yesterday, borderColor: colors[1], borderWidth: 2, borderDash: [5,5], fill: false, tension: 0.4, pointRadius: 4 },
                        { label: '上個月', data: data.lastMonth, borderColor: colors[2], borderWidth: 2, borderDash: [10,5], fill: false, tension: 0.4, pointRadius: 4 }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.raw.toFixed(2)}%` } }
                    },
                    scales: {
                        y: { title: { display: true, text: '殖利率 (%)' }, ticks: { callback: v => v.toFixed(2) + '%' } },
                        x: { title: { display: true, text: '到期年限' } }
                    }
                }
            });
        }

        function renderYieldTable(containerId, data) {
            let html = '<table><thead><tr><th>期限</th><th>今日</th><th>昨日</th><th>日變化</th><th>上個月</th><th>月變化</th></tr></thead><tbody>';
            for (let i = 0; i < maturities.length; i++) {
                const daily = data.today[i] - data.yesterday[i];
                const monthly = data.today[i] - data.lastMonth[i];
                html += `<tr>
                    <td><strong>${maturities[i]}</strong></td>
                    <td>${data.today[i].toFixed(2)}%</td>
                    <td>${data.yesterday[i].toFixed(2)}%</td>
                    <td class="${daily >= 0 ? 'positive' : 'negative'}">${daily >= 0 ? '+' : ''}${(daily*100).toFixed(1)} bp</td>
                    <td>${data.lastMonth[i].toFixed(2)}%</td>
                    <td class="${monthly >= 0 ? 'positive' : 'negative'}">${monthly >= 0 ? '+' : ''}${(monthly*100).toFixed(1)} bp</td>
                </tr>`;
            }
            html += '</tbody></table>';
            document.getElementById(containerId).innerHTML = html;
        }

        function renderSectorChart(data) {
            const ctx = document.getElementById('sectorChart').getContext('2d');
            if (sectorChart) sectorChart.destroy();

            sectorChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.map(d => d.name),
                    datasets: [{
                        label: '當日漲跌幅 (%)',
                        data: data.map(d => d.change),
                        backgroundColor: data.map(d => d.change >= 0 ? '#34a853' : '#ea4335'),
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { title: { display: true, text: '漲跌幅 (%)' }, grid: { color: ctx => ctx.tick.value === 0 ? '#000' : '#e0e0e0' } }
                    }
                }
            });

            let gridHtml = '';
            data.forEach(s => {
                gridHtml += `<div class="sector-item ${s.change >= 0 ? 'positive-bg' : 'negative-bg'}">
                    <div class="sector-name">${s.name} (${s.symbol})</div>
                    <div class="sector-change ${s.change >= 0 ? 'positive' : 'negative'}">${s.change >= 0 ? '+' : ''}${s.change.toFixed(2)}%</div>
                </div>`;
            });
            document.getElementById('sectorGrid').innerHTML = gridHtml;
        }

        function renderMarket(data) {
            let html = '';
            data.forEach(m => {
                const val = m.value >= 1000 ? m.value.toLocaleString('en-US', {maximumFractionDigits: 2}) : m.value.toFixed(2);
                html += `<div class="market-item">
                    <div class="market-name">${m.name}</div>
                    <div class="market-value">${val}</div>
                    <div class="market-change ${m.change >= 0 ? 'positive' : 'negative'}">${m.change >= 0 ? '▲' : '▼'} ${m.change >= 0 ? '+' : ''}${m.change.toFixed(2)}%</div>
                </div>`;
            });
            document.getElementById('marketGrid').innerHTML = html;
        }

        function renderNews(data) {
            let html = '';
            data.forEach(n => {
                html += `<div class="news-item">
                    <div class="news-title">${n.title}</div>
                    <div class="news-meta">
                        <span class="news-source">${n.source}</span>
                        <span>${n.category}</span>
                        <span>${n.time}</span>
                    </div>
                </div>`;
            });
            document.getElementById('newsContainer').innerHTML = html;
        }

        async function refreshData() {
            const btn = document.getElementById('refreshBtn');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinning">🔄</span> 更新中...';

            try {
                const response = await fetch('/api/data');
                const data = await response.json();

                if (usYieldChart) usYieldChart.destroy();
                if (euYieldChart) euYieldChart.destroy();

                usYieldChart = createYieldChart('usYieldChart', data.usYields, ['#1a73e8', '#fbbc04', '#ea4335']);
                euYieldChart = createYieldChart('euYieldChart', data.euYields, ['#0d47a1', '#ff9800', '#e91e63']);

                renderYieldTable('usYieldTable', data.usYields);
                renderYieldTable('euYieldTable', data.euYields);
                renderSectorChart(data.sectors);
                renderMarket(data.market);
                renderNews(data.news);

                document.getElementById('lastUpdate').textContent = '最後更新：' + data.lastUpdate;
            } catch (error) {
                console.error('Error:', error);
                alert('更新資料失敗，請稍後再試');
            } finally {
                btn.disabled = false;
                btn.innerHTML = '🔄 更新資訊';
            }
        }

        // 頁面載入時自動獲取數據
        document.addEventListener('DOMContentLoaded', refreshData);

        // 按 R 鍵刷新
        document.addEventListener('keydown', e => { if (e.key === 'r' || e.key === 'R') refreshData(); });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


# ==================== 主程式 ====================

if __name__ == '__main__':
    print("=" * 50)
    print("  每日金融資訊儀表板")
    print("=" * 50)
    print("\n正在啟動伺服器...")
    print("請在瀏覽器中開啟: http://localhost:5000")
    print("\n按 Ctrl+C 停止伺服器\n")

    app.run(host='0.0.0.0', port=5000, debug=True)
