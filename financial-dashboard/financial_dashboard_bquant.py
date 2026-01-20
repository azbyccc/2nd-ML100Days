"""
Financial Dashboard for Bloomberg BQuant
=========================================
Bloomberg Terminal 專用版本，使用 BQL 和 bqplot 呈現：
- 美歐殖利率曲線（Today/Month Start/Year Start）
- 10Y-2Y 利差計算 + Flatten/Steepen 指標
- 全球股市指數、美股板塊表現（雙向長條圖）
- 外匯、商品、加密貨幣表格
- VIX、MOVE、恐懼貪婪指數（指針儀表盤）

使用方式：在 BQuant 環境中執行此 notebook
"""

import bql
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# BQuant 特定套件
import bqplot as bqp
from bqplot import pyplot as plt
from bqplot import Figure, Axis, Lines, Bars, LinearScale, OrdinalScale, ColorScale
import bqwidgets as bqw
from IPython.display import display, HTML
import ipywidgets as widgets

# 初始化 BQL
bq = bql.Service()

# ============================================================================
# BQL 數據獲取函數
# ============================================================================

def get_us_treasury_yields():
    """
    獲取美國國債殖利率數據
    使用 Bloomberg Ticker
    """
    # 美國國債 Ticker
    tickers = {
        '1M': 'GB1 Govt',
        '3M': 'GB3 Govt',
        '6M': 'GB6 Govt',
        '1Y': 'GB12 Govt',
        '2Y': 'GT2 Govt',
        '3Y': 'GT3 Govt',
        '5Y': 'GT5 Govt',
        '7Y': 'GT7 Govt',
        '10Y': 'GT10 Govt',
        '20Y': 'GT20 Govt',
        '30Y': 'GT30 Govt',
    }

    today = datetime.now()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    results = {
        'maturities': list(tickers.keys()),
        'maturity_values': [1/12, 3/12, 6/12, 1, 2, 3, 5, 7, 10, 20, 30],
        'today': [],
        'month_start': [],
        'year_start': [],
    }

    for maturity, ticker in tickers.items():
        try:
            # 今日收益率
            req_today = bql.Request(ticker, {'YLD': bq.data.px_last()})
            resp_today = bq.execute(req_today)
            results['today'].append(resp_today[0].df()['YLD'].values[0])

            # 月初收益率
            req_month = bql.Request(ticker, {
                'YLD': bq.data.px_last(dates=month_start.strftime('%Y-%m-%d'))
            })
            resp_month = bq.execute(req_month)
            results['month_start'].append(resp_month[0].df()['YLD'].values[0])

            # 年初收益率
            req_year = bql.Request(ticker, {
                'YLD': bq.data.px_last(dates=year_start.strftime('%Y-%m-%d'))
            })
            resp_year = bq.execute(req_year)
            results['year_start'].append(resp_year[0].df()['YLD'].values[0])

        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            results['today'].append(np.nan)
            results['month_start'].append(np.nan)
            results['year_start'].append(np.nan)

    return results


def get_us_yields_bulk():
    """
    使用 BQL 批量獲取美國國債殖利率（更高效的方式）
    """
    tickers = ['GB1 Govt', 'GB3 Govt', 'GB6 Govt', 'GB12 Govt',
               'GT2 Govt', 'GT3 Govt', 'GT5 Govt', 'GT7 Govt',
               'GT10 Govt', 'GT20 Govt', 'GT30 Govt']

    maturities = ['1M', '3M', '6M', '1Y', '2Y', '3Y', '5Y', '7Y', '10Y', '20Y', '30Y']
    maturity_values = [1/12, 3/12, 6/12, 1, 2, 3, 5, 7, 10, 20, 30]

    today = datetime.now()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    # BQL 查詢
    request = bql.Request(
        tickers,
        {
            'Today': bq.data.px_last(),
            'MonthStart': bq.data.px_last(dates=month_start.strftime('%Y-%m-%d')),
            'YearStart': bq.data.px_last(dates=year_start.strftime('%Y-%m-%d')),
        }
    )

    response = bq.execute(request)
    df = response[0].df()

    return {
        'maturities': maturities,
        'maturity_values': maturity_values,
        'today': df['Today'].tolist(),
        'month_start': df['MonthStart'].tolist(),
        'year_start': df['YearStart'].tolist(),
        'date_today': today.strftime('%Y-%m-%d'),
        'date_month_start': month_start.strftime('%Y-%m-%d'),
        'date_year_start': year_start.strftime('%Y-%m-%d'),
    }


def get_euro_yields_bulk():
    """
    獲取歐洲（德國）國債殖利率
    """
    tickers = ['GTDEM3M Govt', 'GTDEM6M Govt', 'GTDEM1Y Govt',
               'GTDEM2Y Govt', 'GTDEM3Y Govt', 'GTDEM5Y Govt',
               'GTDEM7Y Govt', 'GTDEM10Y Govt', 'GTDEM20Y Govt', 'GTDEM30Y Govt']

    maturities = ['3M', '6M', '1Y', '2Y', '3Y', '5Y', '7Y', '10Y', '20Y', '30Y']
    maturity_values = [3/12, 6/12, 1, 2, 3, 5, 7, 10, 20, 30]

    today = datetime.now()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    request = bql.Request(
        tickers,
        {
            'Today': bq.data.px_last(),
            'MonthStart': bq.data.px_last(dates=month_start.strftime('%Y-%m-%d')),
            'YearStart': bq.data.px_last(dates=year_start.strftime('%Y-%m-%d')),
        }
    )

    response = bq.execute(request)
    df = response[0].df()

    return {
        'maturities': maturities,
        'maturity_values': maturity_values,
        'today': df['Today'].tolist(),
        'month_start': df['MonthStart'].tolist(),
        'year_start': df['YearStart'].tolist(),
    }


def get_global_indices():
    """
    獲取全球股市指數
    """
    indices = {
        'S&P 500': 'SPX Index',
        'NASDAQ': 'CCMP Index',
        'Dow Jones': 'INDU Index',
        'Russell 2000': 'RTY Index',
        'STOXX 600': 'SXXP Index',
        'DAX': 'DAX Index',
        'FTSE 100': 'UKX Index',
        'CAC 40': 'CAC Index',
        'Nikkei 225': 'NKY Index',
        'Hang Seng': 'HSI Index',
        'Shanghai Comp': 'SHCOMP Index',
        'TAIEX': 'TWSE Index',
        'KOSPI': 'KOSPI Index',
    }

    tickers = list(indices.values())
    names = list(indices.keys())

    # 計算 YTD 開始日期
    year_start = datetime.now().replace(month=1, day=1)

    request = bql.Request(
        tickers,
        {
            'Price': bq.data.px_last(),
            'Change': bq.data.day_to_day_total_return(),
            'YTD_Start': bq.data.px_last(dates=year_start.strftime('%Y-%m-%d')),
        }
    )

    response = bq.execute(request)
    df = response[0].df()

    # 計算 YTD
    df['YTD'] = ((df['Price'] - df['YTD_Start']) / df['YTD_Start'] * 100)

    result = {}
    for i, name in enumerate(names):
        result[name] = {
            'price': df.iloc[i]['Price'],
            'change': df.iloc[i]['Change'],
            'ytd': df.iloc[i]['YTD'],
        }

    return result


def get_us_sectors():
    """
    獲取美股板塊 ETF 表現
    """
    sectors = {
        'Technology': 'XLK US Equity',
        'Healthcare': 'XLV US Equity',
        'Financials': 'XLF US Equity',
        'Consumer Disc.': 'XLY US Equity',
        'Industrials': 'XLI US Equity',
        'Energy': 'XLE US Equity',
        'Materials': 'XLB US Equity',
        'Utilities': 'XLU US Equity',
        'Real Estate': 'XLRE US Equity',
        'Comm. Services': 'XLC US Equity',
        'Consumer Staples': 'XLP US Equity',
    }

    tickers = list(sectors.values())
    names = list(sectors.keys())

    today = datetime.now()
    week_ago = today - timedelta(days=7)
    month_ago = today - relativedelta(months=1)
    year_start = today.replace(month=1, day=1)

    request = bql.Request(
        tickers,
        {
            'Price': bq.data.px_last(),
            'Daily': bq.data.day_to_day_total_return(),
            'WeekAgo': bq.data.px_last(dates=week_ago.strftime('%Y-%m-%d')),
            'MonthAgo': bq.data.px_last(dates=month_ago.strftime('%Y-%m-%d')),
            'YearStart': bq.data.px_last(dates=year_start.strftime('%Y-%m-%d')),
        }
    )

    response = bq.execute(request)
    df = response[0].df()

    result = {}
    for i, name in enumerate(names):
        price = df.iloc[i]['Price']
        result[name] = {
            'daily': df.iloc[i]['Daily'],
            'weekly': (price - df.iloc[i]['WeekAgo']) / df.iloc[i]['WeekAgo'] * 100,
            'monthly': (price - df.iloc[i]['MonthAgo']) / df.iloc[i]['MonthAgo'] * 100,
            'ytd': (price - df.iloc[i]['YearStart']) / df.iloc[i]['YearStart'] * 100,
        }

    return result


def get_forex():
    """
    獲取外匯數據
    """
    pairs = {
        'EUR/USD': 'EURUSD Curncy',
        'USD/JPY': 'USDJPY Curncy',
        'GBP/USD': 'GBPUSD Curncy',
        'USD/CNY': 'USDCNY Curncy',
        'USD/TWD': 'USDTWD Curncy',
        'AUD/USD': 'AUDUSD Curncy',
        'USD/CHF': 'USDCHF Curncy',
        'DXY': 'DXY Curncy',
    }

    tickers = list(pairs.values())
    names = list(pairs.keys())

    week_ago = datetime.now() - timedelta(days=7)

    request = bql.Request(
        tickers,
        {
            'Price': bq.data.px_last(),
            'Change': bq.data.day_to_day_total_return(),
            'WeekAgo': bq.data.px_last(dates=week_ago.strftime('%Y-%m-%d')),
        }
    )

    response = bq.execute(request)
    df = response[0].df()

    result = {}
    for i, name in enumerate(names):
        price = df.iloc[i]['Price']
        result[name] = {
            'price': price,
            'change': df.iloc[i]['Change'],
            'weekly': (price - df.iloc[i]['WeekAgo']) / df.iloc[i]['WeekAgo'] * 100,
        }

    return result


def get_commodities():
    """
    獲取商品數據
    """
    commodities = {
        'Gold': ('GC1 Comdty', '$/oz'),
        'Silver': ('SI1 Comdty', '$/oz'),
        'WTI Crude': ('CL1 Comdty', '$/bbl'),
        'Brent Crude': ('CO1 Comdty', '$/bbl'),
        'Natural Gas': ('NG1 Comdty', '$/MMBtu'),
        'Copper': ('HG1 Comdty', '$/lb'),
        'Wheat': ('W 1 Comdty', '¢/bu'),
        'Corn': ('C 1 Comdty', '¢/bu'),
    }

    tickers = [v[0] for v in commodities.values()]
    names = list(commodities.keys())
    units = [v[1] for v in commodities.values()]

    week_ago = datetime.now() - timedelta(days=7)

    request = bql.Request(
        tickers,
        {
            'Price': bq.data.px_last(),
            'Change': bq.data.day_to_day_total_return(),
            'WeekAgo': bq.data.px_last(dates=week_ago.strftime('%Y-%m-%d')),
        }
    )

    response = bq.execute(request)
    df = response[0].df()

    result = {}
    for i, name in enumerate(names):
        price = df.iloc[i]['Price']
        result[name] = {
            'price': price,
            'change': df.iloc[i]['Change'],
            'weekly': (price - df.iloc[i]['WeekAgo']) / df.iloc[i]['WeekAgo'] * 100,
            'unit': units[i],
        }

    return result


def get_crypto():
    """
    獲取加密貨幣數據
    """
    crypto = {
        'Bitcoin': 'XBTUSD BGN Curncy',
        'Ethereum': 'XETUSD BGN Curncy',
    }

    tickers = list(crypto.values())
    names = list(crypto.keys())

    week_ago = datetime.now() - timedelta(days=7)

    request = bql.Request(
        tickers,
        {
            'Price': bq.data.px_last(),
            'Change': bq.data.day_to_day_total_return(),
            'WeekAgo': bq.data.px_last(dates=week_ago.strftime('%Y-%m-%d')),
        }
    )

    response = bq.execute(request)
    df = response[0].df()

    result = {}
    for i, name in enumerate(names):
        price = df.iloc[i]['Price']
        result[name] = {
            'price': price,
            'change': df.iloc[i]['Change'],
            'weekly': (price - df.iloc[i]['WeekAgo']) / df.iloc[i]['WeekAgo'] * 100,
        }

    return result


def get_volatility_indices():
    """
    獲取波動率指數
    """
    indices = {
        'VIX': 'VIX Index',
        'MOVE': 'MOVE Index',
    }

    tickers = list(indices.values())
    names = list(indices.keys())

    yesterday = datetime.now() - timedelta(days=1)

    request = bql.Request(
        tickers,
        {
            'Value': bq.data.px_last(),
            'Yesterday': bq.data.px_last(dates=yesterday.strftime('%Y-%m-%d')),
        }
    )

    response = bq.execute(request)
    df = response[0].df()

    result = {}
    for i, name in enumerate(names):
        value = df.iloc[i]['Value']
        yesterday_val = df.iloc[i]['Yesterday']
        change = (value - yesterday_val) / yesterday_val * 100 if yesterday_val else 0

        if name == 'VIX':
            level = 'Low' if value < 15 else 'Normal' if value < 25 else 'High'
        else:  # MOVE
            level = 'Low' if value < 80 else 'Normal' if value < 120 else 'High'

        result[name] = {
            'value': value,
            'change': change,
            'level': level,
        }

    return result


# ============================================================================
# bqplot 圖表函數
# ============================================================================

def create_yield_curve_widget(us_yields, euro_yields):
    """
    使用 bqplot 創建殖利率曲線圖
    """
    # US Yield Curve
    x_scale_us = LinearScale()
    y_scale_us = LinearScale()

    x_axis_us = Axis(scale=x_scale_us, label='Maturity (Years)', grid_lines='solid')
    y_axis_us = Axis(scale=y_scale_us, orientation='vertical', label='Yield (%)', grid_lines='solid')

    line_today_us = Lines(
        x=us_yields['maturity_values'],
        y=us_yields['today'],
        scales={'x': x_scale_us, 'y': y_scale_us},
        colors=['#2196F3'],
        labels=['Today'],
        display_legend=True,
        marker='circle'
    )

    line_month_us = Lines(
        x=us_yields['maturity_values'],
        y=us_yields['month_start'],
        scales={'x': x_scale_us, 'y': y_scale_us},
        colors=['#4CAF50'],
        labels=['Month Start'],
        display_legend=True,
        marker='square',
        line_style='dashed'
    )

    line_year_us = Lines(
        x=us_yields['maturity_values'],
        y=us_yields['year_start'],
        scales={'x': x_scale_us, 'y': y_scale_us},
        colors=['#F44336'],
        labels=['Year Start'],
        display_legend=True,
        marker='triangle-up',
        line_style='dotted'
    )

    fig_us = Figure(
        marks=[line_today_us, line_month_us, line_year_us],
        axes=[x_axis_us, y_axis_us],
        title='US Treasury Yield Curve',
        legend_location='top-right',
        fig_margin={'top': 60, 'bottom': 60, 'left': 60, 'right': 100}
    )

    # Euro Yield Curve
    x_scale_eu = LinearScale()
    y_scale_eu = LinearScale()

    x_axis_eu = Axis(scale=x_scale_eu, label='Maturity (Years)', grid_lines='solid')
    y_axis_eu = Axis(scale=y_scale_eu, orientation='vertical', label='Yield (%)', grid_lines='solid')

    line_today_eu = Lines(
        x=euro_yields['maturity_values'],
        y=euro_yields['today'],
        scales={'x': x_scale_eu, 'y': y_scale_eu},
        colors=['#2196F3'],
        labels=['Today'],
        display_legend=True,
        marker='circle'
    )

    line_month_eu = Lines(
        x=euro_yields['maturity_values'],
        y=euro_yields['month_start'],
        scales={'x': x_scale_eu, 'y': y_scale_eu},
        colors=['#4CAF50'],
        labels=['Month Start'],
        display_legend=True,
        marker='square',
        line_style='dashed'
    )

    line_year_eu = Lines(
        x=euro_yields['maturity_values'],
        y=euro_yields['year_start'],
        scales={'x': x_scale_eu, 'y': y_scale_eu},
        colors=['#F44336'],
        labels=['Year Start'],
        display_legend=True,
        marker='triangle-up',
        line_style='dotted'
    )

    fig_eu = Figure(
        marks=[line_today_eu, line_month_eu, line_year_eu],
        axes=[x_axis_eu, y_axis_eu],
        title='Euro Area Yield Curve (Germany)',
        legend_location='top-right',
        fig_margin={'top': 60, 'bottom': 60, 'left': 60, 'right': 100}
    )

    return widgets.HBox([fig_us, fig_eu])


def create_spread_widget(us_yields):
    """
    創建 10Y-2Y 利差分析 Widget
    """
    idx_2y = us_yields['maturities'].index('2Y')
    idx_10y = us_yields['maturities'].index('10Y')

    spread_today = (us_yields['today'][idx_10y] - us_yields['today'][idx_2y]) * 100
    spread_month = (us_yields['month_start'][idx_10y] - us_yields['month_start'][idx_2y]) * 100
    spread_year = (us_yields['year_start'][idx_10y] - us_yields['year_start'][idx_2y]) * 100

    spread_change = spread_today - spread_month
    trend = 'Steepening' if spread_change > 5 else 'Flattening' if spread_change < -5 else 'Stable'
    trend_color = '#4CAF50' if trend == 'Steepening' else '#F44336' if trend == 'Flattening' else '#9E9E9E'

    # 創建長條圖
    x_scale = OrdinalScale()
    y_scale = LinearScale()

    x_axis = Axis(scale=x_scale, grid_lines='none')
    y_axis = Axis(scale=y_scale, orientation='vertical', label='Spread (bps)', grid_lines='solid')

    colors = ['#9E9E9E', '#2196F3', trend_color]

    bars = Bars(
        x=['Year Start', 'Month Start', 'Today'],
        y=[spread_year, spread_month, spread_today],
        scales={'x': x_scale, 'y': y_scale},
        colors=colors,
        padding=0.4
    )

    fig = Figure(
        marks=[bars],
        axes=[x_axis, y_axis],
        title=f'US 10Y-2Y Spread: {trend}',
        fig_margin={'top': 60, 'bottom': 60, 'left': 70, 'right': 40}
    )

    # 資訊面板
    info_html = f"""
    <div style="padding: 15px; background: #f5f5f5; border-radius: 8px; margin: 10px;">
        <h3 style="margin-top: 0;">10Y-2Y Spread Analysis</h3>
        <table style="width: 100%;">
            <tr><td><b>2Y Yield:</b></td><td>{us_yields['today'][idx_2y]:.2f}%</td></tr>
            <tr><td><b>10Y Yield:</b></td><td>{us_yields['today'][idx_10y]:.2f}%</td></tr>
            <tr><td><b>Today's Spread:</b></td><td>{spread_today:.0f} bps</td></tr>
            <tr><td><b>Month Ago:</b></td><td>{spread_month:.0f} bps</td></tr>
            <tr><td><b>Year Ago:</b></td><td>{spread_year:.0f} bps</td></tr>
            <tr><td><b>Monthly Change:</b></td><td style="color: {trend_color};">{spread_change:+.0f} bps</td></tr>
            <tr><td><b>Trend:</b></td><td style="color: {trend_color}; font-weight: bold;">{trend}</td></tr>
        </table>
    </div>
    """

    info_widget = widgets.HTML(value=info_html)

    return widgets.HBox([fig, info_widget])


def create_sector_chart(sectors):
    """
    創建美股板塊雙向長條圖
    """
    # 按照 daily change 排序
    sorted_sectors = sorted(sectors.items(), key=lambda x: x[1]['daily'], reverse=True)
    names = [s[0] for s in sorted_sectors]
    daily_changes = [s[1]['daily'] for s in sorted_sectors]

    # 顏色
    colors = ['#4CAF50' if x >= 0 else '#F44336' for x in daily_changes]

    x_scale = LinearScale()
    y_scale = OrdinalScale()

    x_axis = Axis(scale=x_scale, label='Daily Change (%)', grid_lines='solid')
    y_axis = Axis(scale=y_scale, orientation='vertical', grid_lines='none')

    bars = Bars(
        x=daily_changes,
        y=names,
        scales={'x': x_scale, 'y': y_scale},
        colors=colors,
        orientation='horizontal',
        padding=0.2
    )

    fig = Figure(
        marks=[bars],
        axes=[x_axis, y_axis],
        title='US Sector Performance (Daily Change)',
        fig_margin={'top': 60, 'bottom': 60, 'left': 140, 'right': 40}
    )

    return fig


def create_gauge_widget(value, title, min_val, max_val, thresholds, colors_list):
    """
    創建儀表盤 Widget（使用 HTML/CSS）
    """
    # 計算指針角度
    normalized = (value - min_val) / (max_val - min_val)
    angle = 180 - normalized * 180  # 從左到右 180 到 0 度

    # 決定顏色
    color = colors_list[-1]
    for i, thresh in enumerate(thresholds):
        if value <= thresh:
            color = colors_list[i]
            break

    html = f"""
    <div style="text-align: center; padding: 20px; background: #f8f9fa; border-radius: 12px; margin: 10px;">
        <svg width="200" height="120" viewBox="0 0 200 120">
            <!-- 背景弧形 -->
            <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="#e0e0e0" stroke-width="15"/>

            <!-- 彩色弧形 -->
            <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="{color}" stroke-width="15"
                  stroke-dasharray="{normalized * 251.2} 251.2"/>

            <!-- 指針 -->
            <line x1="100" y1="100" x2="{100 + 60 * np.cos(np.radians(angle))}" y2="{100 - 60 * np.sin(np.radians(angle))}"
                  stroke="#333" stroke-width="3" stroke-linecap="round"/>

            <!-- 中心圓 -->
            <circle cx="100" cy="100" r="8" fill="#333"/>

            <!-- 數值 -->
            <text x="100" y="85" text-anchor="middle" font-size="24" font-weight="bold">{value:.1f}</text>
        </svg>
        <div style="font-size: 14px; font-weight: bold; margin-top: 5px;">{title}</div>
        <div style="font-size: 11px; color: #666;">{min_val} - {max_val}</div>
    </div>
    """

    return widgets.HTML(value=html)


def create_volatility_dashboard(vol_indices):
    """
    創建波動率儀表盤
    """
    vix_widget = create_gauge_widget(
        vol_indices['VIX']['value'], 'VIX Index',
        0, 50, [15, 25, 50], ['#4CAF50', '#FFC107', '#F44336']
    )

    move_widget = create_gauge_widget(
        vol_indices['MOVE']['value'], 'MOVE Index',
        50, 200, [80, 120, 200], ['#4CAF50', '#FFC107', '#F44336']
    )

    return widgets.HBox([vix_widget, move_widget])


def create_data_table(data, title, columns):
    """
    創建數據表格
    """
    df = pd.DataFrame(data).T
    df.index.name = columns[0]
    df = df.reset_index()
    df.columns = columns

    # 格式化顯示
    html = f"<h3>{title}</h3>"
    html += df.to_html(index=False, classes='table table-striped', escape=False)

    return widgets.HTML(value=html)


# ============================================================================
# 主儀表板
# ============================================================================

def create_dashboard():
    """
    創建完整的金融儀表板
    """
    print("📊 Loading Financial Dashboard...")
    print("⏳ Fetching data from Bloomberg...")

    # 獲取數據
    try:
        us_yields = get_us_yields_bulk()
        print("✅ US Treasury yields loaded")
    except Exception as e:
        print(f"⚠️ Error loading US yields: {e}")
        us_yields = None

    try:
        euro_yields = get_euro_yields_bulk()
        print("✅ Euro yields loaded")
    except Exception as e:
        print(f"⚠️ Error loading Euro yields: {e}")
        euro_yields = None

    try:
        indices = get_global_indices()
        print("✅ Global indices loaded")
    except Exception as e:
        print(f"⚠️ Error loading indices: {e}")
        indices = {}

    try:
        sectors = get_us_sectors()
        print("✅ US sectors loaded")
    except Exception as e:
        print(f"⚠️ Error loading sectors: {e}")
        sectors = {}

    try:
        forex = get_forex()
        print("✅ FX data loaded")
    except Exception as e:
        print(f"⚠️ Error loading FX: {e}")
        forex = {}

    try:
        commodities = get_commodities()
        print("✅ Commodities loaded")
    except Exception as e:
        print(f"⚠️ Error loading commodities: {e}")
        commodities = {}

    try:
        vol_indices = get_volatility_indices()
        print("✅ Volatility indices loaded")
    except Exception as e:
        print(f"⚠️ Error loading volatility: {e}")
        vol_indices = {}

    print("\n📈 Building dashboard...")

    # 標題
    title_html = f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; padding: 20px; border-radius: 12px; margin-bottom: 20px;">
        <h1 style="margin: 0; text-align: center;">📊 Financial Dashboard</h1>
        <p style="text-align: center; margin: 10px 0 0 0;">
            Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </div>
    """
    title_widget = widgets.HTML(value=title_html)

    # 建立各區塊
    tab_contents = []
    tab_titles = []

    # Tab 1: Yield Curves
    if us_yields and euro_yields:
        yield_widgets = widgets.VBox([
            create_yield_curve_widget(us_yields, euro_yields),
            create_spread_widget(us_yields)
        ])
        tab_contents.append(yield_widgets)
        tab_titles.append('Yield Curves')

    # Tab 2: Global Markets
    if indices:
        indices_df = pd.DataFrame(indices).T
        indices_df = indices_df.round({'price': 2, 'change': 2, 'ytd': 1})

        indices_html = """
        <style>
            .positive { color: #4CAF50; }
            .negative { color: #F44336; }
        </style>
        <h3>Global Market Indices</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <tr style="background: #667eea; color: white;">
                <th style="padding: 10px; text-align: left;">Index</th>
                <th style="padding: 10px; text-align: right;">Price</th>
                <th style="padding: 10px; text-align: right;">Daily</th>
                <th style="padding: 10px; text-align: right;">YTD</th>
            </tr>
        """

        for idx, row in indices_df.iterrows():
            daily_class = 'positive' if row['change'] >= 0 else 'negative'
            ytd_class = 'positive' if row['ytd'] >= 0 else 'negative'
            indices_html += f"""
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px;"><b>{idx}</b></td>
                <td style="padding: 8px; text-align: right;">{row['price']:,.2f}</td>
                <td style="padding: 8px; text-align: right;" class="{daily_class}">{row['change']:+.2f}%</td>
                <td style="padding: 8px; text-align: right;" class="{ytd_class}">{row['ytd']:+.1f}%</td>
            </tr>
            """

        indices_html += "</table>"
        tab_contents.append(widgets.HTML(value=indices_html))
        tab_titles.append('Global Indices')

    # Tab 3: US Sectors
    if sectors:
        sector_chart = create_sector_chart(sectors)
        tab_contents.append(sector_chart)
        tab_titles.append('US Sectors')

    # Tab 4: FX & Commodities
    if forex or commodities:
        fx_comm_widgets = []

        if forex:
            forex_html = "<h3>Foreign Exchange</h3><table style='width:100%;'>"
            forex_html += "<tr style='background:#667eea;color:white;'><th>Pair</th><th>Rate</th><th>Daily</th><th>Weekly</th></tr>"
            for name, data in forex.items():
                chg_class = 'positive' if data['change'] >= 0 else 'negative'
                forex_html += f"<tr><td><b>{name}</b></td><td>{data['price']:.4f}</td><td class='{chg_class}'>{data['change']:+.2f}%</td><td class='{chg_class}'>{data['weekly']:+.2f}%</td></tr>"
            forex_html += "</table>"
            fx_comm_widgets.append(widgets.HTML(value=forex_html))

        if commodities:
            comm_html = "<h3>Commodities</h3><table style='width:100%;'>"
            comm_html += "<tr style='background:#667eea;color:white;'><th>Commodity</th><th>Price</th><th>Daily</th><th>Weekly</th></tr>"
            for name, data in commodities.items():
                chg_class = 'positive' if data['change'] >= 0 else 'negative'
                comm_html += f"<tr><td><b>{name}</b></td><td>{data['price']:.2f} {data['unit']}</td><td class='{chg_class}'>{data['change']:+.2f}%</td><td class='{chg_class}'>{data['weekly']:+.2f}%</td></tr>"
            comm_html += "</table>"
            fx_comm_widgets.append(widgets.HTML(value=comm_html))

        tab_contents.append(widgets.VBox(fx_comm_widgets))
        tab_titles.append('FX & Commodities')

    # Tab 5: Volatility
    if vol_indices:
        vol_dashboard = create_volatility_dashboard(vol_indices)
        tab_contents.append(vol_dashboard)
        tab_titles.append('Volatility')

    # 建立 Tab
    tab = widgets.Tab(children=tab_contents)
    for i, title in enumerate(tab_titles):
        tab.set_title(i, title)

    # 組合儀表板
    dashboard = widgets.VBox([title_widget, tab])

    print("✅ Dashboard ready!")

    return dashboard


# ============================================================================
# 執行入口
# ============================================================================

# 在 BQuant 中執行以下程式碼來顯示儀表板：
# dashboard = create_dashboard()
# display(dashboard)

if __name__ == '__main__':
    print("=" * 60)
    print("Financial Dashboard for Bloomberg BQuant")
    print("=" * 60)
    print("\n請在 BQuant 環境中執行以下程式碼：")
    print("\n  dashboard = create_dashboard()")
    print("  display(dashboard)")
    print("\n" + "=" * 60)
