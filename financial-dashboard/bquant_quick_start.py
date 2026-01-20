"""
Financial Dashboard for Bloomberg BQuant - Quick Start
======================================================
直接複製此程式碼到 BQuant Notebook 中執行即可

使用方式：
1. 在 BQuant 中建立新的 Python Notebook
2. 複製整個程式碼到第一個 cell
3. 執行 cell
4. 儀表板會自動顯示
"""

# ============================================================================
# Cell 1: 初始化與套件導入
# ============================================================================

import bql
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from bqplot import Figure, Axis, Lines, Bars, LinearScale, OrdinalScale
from IPython.display import display, HTML
import ipywidgets as widgets

# 初始化 BQL
bq = bql.Service()
print('✅ BQL Service initialized')

# ============================================================================
# Cell 2: 數據獲取函數
# ============================================================================

def get_us_treasury_yields():
    """獲取美國國債殖利率"""
    tickers = ['GB1 Govt', 'GB3 Govt', 'GB6 Govt', 'GB12 Govt',
               'GT2 Govt', 'GT3 Govt', 'GT5 Govt', 'GT7 Govt',
               'GT10 Govt', 'GT20 Govt', 'GT30 Govt']

    maturities = ['1M', '3M', '6M', '1Y', '2Y', '3Y', '5Y', '7Y', '10Y', '20Y', '30Y']
    maturity_values = [1/12, 3/12, 6/12, 1, 2, 3, 5, 7, 10, 20, 30]

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
        'date_today': today.strftime('%Y-%m-%d'),
    }


def get_euro_yields():
    """獲取歐洲（德國）國債殖利率"""
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
    """獲取全球股市指數"""
    indices = {
        'S&P 500': 'SPX Index',
        'NASDAQ': 'CCMP Index',
        'Dow Jones': 'INDU Index',
        'Russell 2000': 'RTY Index',
        'STOXX 600': 'SXXP Index',
        'DAX': 'DAX Index',
        'FTSE 100': 'UKX Index',
        'Nikkei 225': 'NKY Index',
        'Hang Seng': 'HSI Index',
        'Shanghai Comp': 'SHCOMP Index',
        'TAIEX': 'TWSE Index',
        'KOSPI': 'KOSPI Index',
    }

    tickers = list(indices.values())
    names = list(indices.keys())
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
    df['YTD'] = ((df['Price'] - df['YTD_Start']) / df['YTD_Start'] * 100)
    df['Name'] = names

    return df[['Name', 'Price', 'Change', 'YTD']]


def get_us_sectors():
    """獲取美股板塊 ETF 表現"""
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
    year_start = datetime.now().replace(month=1, day=1)

    request = bql.Request(
        tickers,
        {
            'Price': bq.data.px_last(),
            'Daily': bq.data.day_to_day_total_return(),
            'YearStart': bq.data.px_last(dates=year_start.strftime('%Y-%m-%d')),
        }
    )

    response = bq.execute(request)
    df = response[0].df()
    df['YTD'] = ((df['Price'] - df['YearStart']) / df['YearStart'] * 100)
    df['Name'] = names

    return df.sort_values('Daily', ascending=False)


def get_fx_commodities():
    """獲取外匯和商品數據"""
    fx_tickers = {
        'EUR/USD': 'EURUSD Curncy',
        'USD/JPY': 'USDJPY Curncy',
        'GBP/USD': 'GBPUSD Curncy',
        'USD/CNY': 'USDCNY Curncy',
        'USD/TWD': 'USDTWD Curncy',
        'DXY': 'DXY Curncy',
    }

    comm_tickers = {
        'Gold': 'GC1 Comdty',
        'Silver': 'SI1 Comdty',
        'WTI Crude': 'CL1 Comdty',
        'Brent Crude': 'CO1 Comdty',
        'Natural Gas': 'NG1 Comdty',
        'Copper': 'HG1 Comdty',
    }

    all_tickers = list(fx_tickers.values()) + list(comm_tickers.values())
    all_names = list(fx_tickers.keys()) + list(comm_tickers.keys())

    week_ago = datetime.now() - timedelta(days=7)

    request = bql.Request(
        all_tickers,
        {
            'Price': bq.data.px_last(),
            'Change': bq.data.day_to_day_total_return(),
            'WeekAgo': bq.data.px_last(dates=week_ago.strftime('%Y-%m-%d')),
        }
    )

    response = bq.execute(request)
    df = response[0].df()
    df['Weekly'] = ((df['Price'] - df['WeekAgo']) / df['WeekAgo'] * 100)
    df['Name'] = all_names

    fx_df = df.head(len(fx_tickers))
    comm_df = df.tail(len(comm_tickers))

    return fx_df, comm_df


def get_volatility():
    """獲取波動率指標"""
    tickers = ['VIX Index', 'MOVE Index']
    names = ['VIX', 'MOVE']

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
    df['Change'] = ((df['Value'] - df['Yesterday']) / df['Yesterday'] * 100)
    df['Name'] = names

    return df


# ============================================================================
# Cell 3: 圖表生成函數
# ============================================================================

def create_yield_curve_chart(yields_data, title, width='800px', height='400px'):
    """創建殖利率曲線圖"""
    x_scale = LinearScale()
    y_scale = LinearScale()

    x_axis = Axis(scale=x_scale, label='Maturity (Years)', grid_lines='solid')
    y_axis = Axis(scale=y_scale, orientation='vertical', label='Yield (%)', grid_lines='solid')

    line_today = Lines(
        x=yields_data['maturity_values'],
        y=yields_data['today'],
        scales={'x': x_scale, 'y': y_scale},
        colors=['#2196F3'],
        labels=['Today'],
        display_legend=True,
        marker='circle'
    )

    line_month = Lines(
        x=yields_data['maturity_values'],
        y=yields_data['month_start'],
        scales={'x': x_scale, 'y': y_scale},
        colors=['#4CAF50'],
        labels=['Month Start'],
        display_legend=True,
        marker='square',
        line_style='dashed'
    )

    line_year = Lines(
        x=yields_data['maturity_values'],
        y=yields_data['year_start'],
        scales={'x': x_scale, 'y': y_scale},
        colors=['#F44336'],
        labels=['Year Start'],
        display_legend=True,
        marker='triangle-up',
        line_style='dotted'
    )

    fig = Figure(
        marks=[line_today, line_month, line_year],
        axes=[x_axis, y_axis],
        title=title,
        legend_location='top-right',
        layout=widgets.Layout(width=width, height=height)
    )

    return fig


def create_spread_analysis(yields_data):
    """創建利差分析 Widget"""
    idx_2y = yields_data['maturities'].index('2Y')
    idx_10y = yields_data['maturities'].index('10Y')

    spread_today = (yields_data['today'][idx_10y] - yields_data['today'][idx_2y]) * 100
    spread_month = (yields_data['month_start'][idx_10y] - yields_data['month_start'][idx_2y]) * 100
    spread_year = (yields_data['year_start'][idx_10y] - yields_data['year_start'][idx_2y]) * 100

    spread_change = spread_today - spread_month

    if spread_change > 5:
        trend = 'Steepening'
        trend_color = '#4CAF50'
        trend_icon = '📈'
    elif spread_change < -5:
        trend = 'Flattening'
        trend_color = '#F44336'
        trend_icon = '📉'
    else:
        trend = 'Stable'
        trend_color = '#9E9E9E'
        trend_icon = '➡️'

    # 長條圖
    x_scale = OrdinalScale()
    y_scale = LinearScale()

    bars = Bars(
        x=['Year Start', 'Month Start', 'Today'],
        y=[spread_year, spread_month, spread_today],
        scales={'x': x_scale, 'y': y_scale},
        colors=['#9E9E9E', '#2196F3', trend_color],
        padding=0.4
    )

    fig = Figure(
        marks=[bars],
        axes=[
            Axis(scale=x_scale, grid_lines='none'),
            Axis(scale=y_scale, orientation='vertical', label='Spread (bps)', grid_lines='solid')
        ],
        title=f'US 10Y-2Y Spread: {trend} {trend_icon}',
        layout=widgets.Layout(width='500px', height='300px')
    )

    # 資訊面板
    info_html = f"""
    <div style="padding: 15px; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                border-radius: 12px; margin: 10px;">
        <h3 style="margin-top: 0;">📊 Spread Analysis</h3>
        <table style="width: 100%;">
            <tr><td><b>2Y Yield:</b></td><td>{yields_data['today'][idx_2y]:.2f}%</td></tr>
            <tr><td><b>10Y Yield:</b></td><td>{yields_data['today'][idx_10y]:.2f}%</td></tr>
            <tr><td><b>Today's Spread:</b></td><td><b>{spread_today:.0f} bps</b></td></tr>
            <tr><td><b>Month Ago:</b></td><td>{spread_month:.0f} bps</td></tr>
            <tr><td><b>Year Ago:</b></td><td>{spread_year:.0f} bps</td></tr>
            <tr><td><b>Monthly Change:</b></td>
                <td style="color: {trend_color}; font-weight: bold;">{spread_change:+.0f} bps</td></tr>
            <tr><td><b>Trend:</b></td>
                <td style="color: {trend_color}; font-weight: bold;">{trend} {trend_icon}</td></tr>
        </table>
    </div>
    """

    return widgets.HBox([fig, widgets.HTML(value=info_html)])


def create_sector_chart(sectors_df):
    """創建板塊長條圖"""
    names = sectors_df['Name'].tolist()
    daily = sectors_df['Daily'].tolist()
    colors = ['#4CAF50' if x >= 0 else '#F44336' for x in daily]

    x_scale = LinearScale()
    y_scale = OrdinalScale()

    bars = Bars(
        x=daily,
        y=names,
        scales={'x': x_scale, 'y': y_scale},
        colors=colors,
        orientation='horizontal',
        padding=0.2
    )

    fig = Figure(
        marks=[bars],
        axes=[
            Axis(scale=x_scale, label='Daily Change (%)', grid_lines='solid'),
            Axis(scale=y_scale, orientation='vertical', grid_lines='none')
        ],
        title='🏢 US Sector Performance',
        layout=widgets.Layout(width='700px', height='450px'),
        fig_margin={'top': 60, 'bottom': 60, 'left': 140, 'right': 60}
    )

    return fig


# ============================================================================
# Cell 4: 主儀表板函數
# ============================================================================

def create_dashboard():
    """創建完整的金融儀表板"""
    print("📊 Loading Financial Dashboard...")
    print("⏳ Fetching data from Bloomberg...\n")

    # 標題
    title_html = f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; padding: 25px; border-radius: 16px; margin-bottom: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);">
        <h1 style="margin: 0; text-align: center; font-size: 28px;">📊 Financial Dashboard</h1>
        <p style="text-align: center; margin: 10px 0 0 0; opacity: 0.9;">
            Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Bloomberg BQuant
        </p>
    </div>
    """

    tab_contents = []
    tab_titles = []

    # ===== Tab 1: Yield Curves =====
    try:
        print("📈 Loading US Treasury yields...")
        us_yields = get_us_treasury_yields()
        print("📈 Loading Euro yields...")
        euro_yields = get_euro_yields()

        us_chart = create_yield_curve_chart(us_yields, '🇺🇸 US Treasury Yield Curve')
        eu_chart = create_yield_curve_chart(euro_yields, '🇪🇺 Euro Yield Curve (Germany)')
        spread_widget = create_spread_analysis(us_yields)

        yield_tab = widgets.VBox([
            widgets.HBox([us_chart, eu_chart]),
            spread_widget
        ])
        tab_contents.append(yield_tab)
        tab_titles.append('Yield Curves')
        print("✅ Yield curves loaded\n")
    except Exception as e:
        print(f"⚠️ Error loading yields: {e}\n")

    # ===== Tab 2: Global Indices =====
    try:
        print("🌍 Loading global indices...")
        indices_df = get_global_indices()

        indices_html = """
        <style>
            .idx-table { width: 100%; border-collapse: collapse; max-width: 900px; }
            .idx-table th { background: #667eea; color: white; padding: 12px; text-align: left; }
            .idx-table td { padding: 10px; border-bottom: 1px solid #ddd; }
            .idx-table tr:hover { background: #f5f5f5; }
            .pos { color: #4CAF50; font-weight: bold; }
            .neg { color: #F44336; font-weight: bold; }
        </style>
        <h2>🌍 Global Market Indices</h2>
        <table class="idx-table">
            <tr><th>Index</th><th style="text-align:right;">Price</th>
                <th style="text-align:right;">Daily</th><th style="text-align:right;">YTD</th></tr>
        """

        for _, row in indices_df.iterrows():
            d_cls = 'pos' if row['Change'] >= 0 else 'neg'
            y_cls = 'pos' if row['YTD'] >= 0 else 'neg'
            indices_html += f"""
            <tr>
                <td><b>{row['Name']}</b></td>
                <td style="text-align:right;">{row['Price']:,.2f}</td>
                <td style="text-align:right;" class="{d_cls}">{row['Change']:+.2f}%</td>
                <td style="text-align:right;" class="{y_cls}">{row['YTD']:+.1f}%</td>
            </tr>
            """
        indices_html += "</table>"

        tab_contents.append(widgets.HTML(value=indices_html))
        tab_titles.append('Global Indices')
        print("✅ Global indices loaded\n")
    except Exception as e:
        print(f"⚠️ Error loading indices: {e}\n")

    # ===== Tab 3: US Sectors =====
    try:
        print("🏢 Loading US sectors...")
        sectors_df = get_us_sectors()
        sector_chart = create_sector_chart(sectors_df)
        tab_contents.append(sector_chart)
        tab_titles.append('US Sectors')
        print("✅ US sectors loaded\n")
    except Exception as e:
        print(f"⚠️ Error loading sectors: {e}\n")

    # ===== Tab 4: FX & Commodities =====
    try:
        print("💱 Loading FX & Commodities...")
        fx_df, comm_df = get_fx_commodities()

        def make_table(df, title):
            html = f"<h3>{title}</h3><table style='width:100%;border-collapse:collapse;'>"
            html += "<tr style='background:#667eea;color:white;'>"
            html += "<th style='padding:10px;text-align:left;'>Name</th>"
            html += "<th style='padding:10px;text-align:right;'>Price</th>"
            html += "<th style='padding:10px;text-align:right;'>Daily</th>"
            html += "<th style='padding:10px;text-align:right;'>Weekly</th></tr>"

            for _, row in df.iterrows():
                d_color = '#4CAF50' if row['Change'] >= 0 else '#F44336'
                w_color = '#4CAF50' if row['Weekly'] >= 0 else '#F44336'
                html += f"""
                <tr style='border-bottom:1px solid #ddd;'>
                    <td style='padding:8px;'><b>{row['Name']}</b></td>
                    <td style='padding:8px;text-align:right;'>{row['Price']:.4f}</td>
                    <td style='padding:8px;text-align:right;color:{d_color};'>{row['Change']:+.2f}%</td>
                    <td style='padding:8px;text-align:right;color:{w_color};'>{row['Weekly']:+.2f}%</td>
                </tr>
                """
            html += "</table>"
            return html

        fx_comm_html = f"""
        <div style="display:flex;gap:40px;flex-wrap:wrap;">
            <div style="flex:1;min-width:350px;">{make_table(fx_df, '💱 Foreign Exchange')}</div>
            <div style="flex:1;min-width:350px;">{make_table(comm_df, '🛢️ Commodities')}</div>
        </div>
        """

        tab_contents.append(widgets.HTML(value=fx_comm_html))
        tab_titles.append('FX & Commodities')
        print("✅ FX & Commodities loaded\n")
    except Exception as e:
        print(f"⚠️ Error loading FX/Commodities: {e}\n")

    # ===== Tab 5: Volatility =====
    try:
        print("📊 Loading volatility indices...")
        vol_df = get_volatility()

        def get_level(name, value):
            if name == 'VIX':
                if value < 15: return 'Low', '#4CAF50'
                elif value < 25: return 'Normal', '#FFC107'
                else: return 'High', '#F44336'
            else:  # MOVE
                if value < 80: return 'Low', '#4CAF50'
                elif value < 120: return 'Normal', '#FFC107'
                else: return 'High', '#F44336'

        vol_html = "<h2>📊 Volatility Indicators</h2><div style='display:flex;gap:30px;justify-content:center;'>"

        for _, row in vol_df.iterrows():
            level, color = get_level(row['Name'], row['Value'])
            chg_color = '#4CAF50' if row['Change'] < 0 else '#F44336'

            vol_html += f"""
            <div style="background:linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                        border-radius:16px; padding:30px; text-align:center; min-width:220px;
                        box-shadow: 0 6px 20px rgba(0,0,0,0.1);">
                <div style="font-size:16px; color:#666;">{row['Name']} Index</div>
                <div style="font-size:48px; font-weight:bold; margin:15px 0;">{row['Value']:.1f}</div>
                <div style="background:{color}; color:white; padding:8px 20px;
                            border-radius:25px; display:inline-block; font-weight:bold;">{level}</div>
                <div style="margin-top:15px; color:{chg_color}; font-size:14px;">
                    Change: {row['Change']:+.1f}%
                </div>
            </div>
            """

        vol_html += "</div>"
        tab_contents.append(widgets.HTML(value=vol_html))
        tab_titles.append('Volatility')
        print("✅ Volatility loaded\n")
    except Exception as e:
        print(f"⚠️ Error loading volatility: {e}\n")

    # 建立 Tab Widget
    tab = widgets.Tab(children=tab_contents)
    for i, title in enumerate(tab_titles):
        tab.set_title(i, title)

    # 組合儀表板
    dashboard = widgets.VBox([
        widgets.HTML(value=title_html),
        tab
    ])

    print("=" * 50)
    print("✅ Dashboard ready!")
    print("=" * 50)

    return dashboard


# ============================================================================
# 執行儀表板
# ============================================================================

# 建立並顯示儀表板
dashboard = create_dashboard()
display(dashboard)
