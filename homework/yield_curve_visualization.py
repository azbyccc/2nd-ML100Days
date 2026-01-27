"""
美債及德債殖利率曲線視覺化
使用基於真實歷史趨勢的數據展示交互式殖利率曲線
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import numpy as np

# 設定隨機種子確保可重現
np.random.seed(42)


def generate_us_treasury_yields() -> pd.DataFrame:
    """
    生成美國國債殖利率數據
    基於 2022-2024 年實際殖利率走勢模擬
    """
    dates = pd.date_range(start='2022-01-01', end='2024-12-31', freq='D')

    # 各天期的基準殖利率和特性
    # 基於 2022 年初的實際利率水平
    maturities = {
        '1M': {'base': 0.05, 'sensitivity': 1.2},
        '3M': {'base': 0.08, 'sensitivity': 1.15},
        '6M': {'base': 0.22, 'sensitivity': 1.1},
        '1Y': {'base': 0.40, 'sensitivity': 1.0},
        '2Y': {'base': 0.78, 'sensitivity': 0.95},
        '3Y': {'base': 1.04, 'sensitivity': 0.9},
        '5Y': {'base': 1.37, 'sensitivity': 0.8},
        '7Y': {'base': 1.55, 'sensitivity': 0.7},
        '10Y': {'base': 1.63, 'sensitivity': 0.6},
        '20Y': {'base': 2.01, 'sensitivity': 0.5},
        '30Y': {'base': 1.98, 'sensitivity': 0.45},
    }

    data = {}
    n_days = len(dates)

    # 模擬聯準會升息週期 (2022-2023) 和可能的降息 (2024)
    # 聯邦基金利率從 0.25% 升至 5.5%，然後小幅下降
    fed_rate_path = np.zeros(n_days)
    for i in range(n_days):
        progress = i / n_days
        if progress < 0.6:  # 2022-2023 中升息期
            fed_rate_path[i] = 0.25 + (5.25 * (progress / 0.6) ** 0.8)
        elif progress < 0.85:  # 2023 末維持高位
            fed_rate_path[i] = 5.5
        else:  # 2024 開始降息
            fed_rate_path[i] = 5.5 - (0.75 * ((progress - 0.85) / 0.15))

    for maturity, params in maturities.items():
        rates = []
        base = params['base']
        sens = params['sensitivity']

        for i in range(n_days):
            # 基準利率 + 政策影響 + 隨機波動
            policy_effect = fed_rate_path[i] * sens

            # 添加週期性波動和隨機噪聲
            seasonal = 0.05 * np.sin(2 * np.pi * i / 365)
            noise = np.random.normal(0, 0.03)

            rate = base + policy_effect + seasonal + noise
            rates.append(max(0.01, rate))  # 確保利率為正

        data[maturity] = rates

    df = pd.DataFrame(data, index=dates)
    return df


def generate_german_bond_yields() -> pd.DataFrame:
    """
    生成德國國債殖利率數據
    基於 2022-2024 年歐洲央行升息週期模擬
    """
    dates = pd.date_range(start='2022-01-01', end='2024-12-31', freq='D')

    # 德國國債天期配置
    # 2022 年初許多天期仍為負利率
    maturities = {
        '3M': {'base': -0.65, 'sensitivity': 1.1},
        '6M': {'base': -0.60, 'sensitivity': 1.05},
        '1Y': {'base': -0.50, 'sensitivity': 1.0},
        '2Y': {'base': -0.35, 'sensitivity': 0.9},
        '3Y': {'base': -0.25, 'sensitivity': 0.85},
        '5Y': {'base': -0.05, 'sensitivity': 0.75},
        '7Y': {'base': 0.10, 'sensitivity': 0.65},
        '10Y': {'base': 0.25, 'sensitivity': 0.55},
        '15Y': {'base': 0.40, 'sensitivity': 0.45},
        '20Y': {'base': 0.45, 'sensitivity': 0.40},
        '30Y': {'base': 0.35, 'sensitivity': 0.35},
    }

    data = {}
    n_days = len(dates)

    # 模擬歐洲央行升息週期（較美國晚開始）
    # ECB 從 -0.5% 升至 4%
    ecb_rate_path = np.zeros(n_days)
    for i in range(n_days):
        progress = i / n_days
        if progress < 0.2:  # 2022 上半年維持負利率
            ecb_rate_path[i] = -0.5
        elif progress < 0.7:  # 2022-2023 升息期
            ecb_rate_path[i] = -0.5 + (4.5 * ((progress - 0.2) / 0.5) ** 0.7)
        elif progress < 0.9:  # 2023 末維持高位
            ecb_rate_path[i] = 4.0
        else:  # 2024 降息
            ecb_rate_path[i] = 4.0 - (0.5 * ((progress - 0.9) / 0.1))

    for maturity, params in maturities.items():
        rates = []
        base = params['base']
        sens = params['sensitivity']

        for i in range(n_days):
            policy_effect = ecb_rate_path[i] * sens
            seasonal = 0.04 * np.sin(2 * np.pi * i / 365)
            noise = np.random.normal(0, 0.025)

            rate = base + policy_effect + seasonal + noise
            rates.append(rate)

        data[maturity] = rates

    df = pd.DataFrame(data, index=dates)
    return df


def create_interactive_yield_curve(us_data: pd.DataFrame, de_data: pd.DataFrame) -> go.Figure:
    """創建交互式動態殖利率曲線圖"""

    # 將數據重採樣為月頻
    us_monthly = us_data.resample('ME').last().dropna(how='all')
    de_monthly = de_data.resample('ME').last().dropna(how='all')

    # 獲取共同日期範圍
    common_dates = us_monthly.index.intersection(de_monthly.index)

    # 定義天期對應的月數（用於 x 軸）
    maturity_months = {
        '1M': 1, '3M': 3, '6M': 6, '1Y': 12, '2Y': 24, '3Y': 36,
        '5Y': 60, '7Y': 84, '10Y': 120, '15Y': 180, '20Y': 240, '30Y': 360
    }

    # 準備美國數據
    us_cols = [col for col in us_monthly.columns if col in maturity_months]
    us_x = [maturity_months[col] for col in us_cols]

    # 準備德國數據
    de_cols = [col for col in de_monthly.columns if col in maturity_months]
    de_x = [maturity_months[col] for col in de_cols]

    # 創建圖表
    fig = go.Figure()

    # 為每個月份創建 frames
    frames = []

    for date in common_dates:
        date_str = date.strftime('%Y-%m')

        frame_data = []

        # 美國殖利率曲線
        us_values = [us_monthly.loc[date, col] for col in us_cols]
        frame_data.append(go.Scatter(
            x=us_x,
            y=us_values,
            mode='lines+markers',
            name='🇺🇸 美國國債',
            line=dict(color='#1f77b4', width=3),
            marker=dict(size=10, symbol='circle'),
            hovertemplate='天期: %{text}<br>殖利率: %{y:.3f}%<extra>美國國債</extra>',
            text=us_cols
        ))

        # 德國殖利率曲線
        de_values = [de_monthly.loc[date, col] for col in de_cols]
        frame_data.append(go.Scatter(
            x=de_x,
            y=de_values,
            mode='lines+markers',
            name='🇩🇪 德國國債',
            line=dict(color='#ff7f0e', width=3),
            marker=dict(size=10, symbol='diamond'),
            hovertemplate='天期: %{text}<br>殖利率: %{y:.3f}%<extra>德國國債</extra>',
            text=de_cols
        ))

        frames.append(go.Frame(data=frame_data, name=date_str))

    # 設置初始數據（第一個月）
    first_date = common_dates[0]

    # 美國初始數據
    us_values_init = [us_monthly.loc[first_date, col] for col in us_cols]
    fig.add_trace(go.Scatter(
        x=us_x,
        y=us_values_init,
        mode='lines+markers',
        name='🇺🇸 美國國債',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=10, symbol='circle'),
        hovertemplate='天期: %{text}<br>殖利率: %{y:.3f}%<extra>美國國債</extra>',
        text=us_cols
    ))

    # 德國初始數據
    de_values_init = [de_monthly.loc[first_date, col] for col in de_cols]
    fig.add_trace(go.Scatter(
        x=de_x,
        y=de_values_init,
        mode='lines+markers',
        name='🇩🇪 德國國債',
        line=dict(color='#ff7f0e', width=3),
        marker=dict(size=10, symbol='diamond'),
        hovertemplate='天期: %{text}<br>殖利率: %{y:.3f}%<extra>德國國債</extra>',
        text=de_cols
    ))

    # 添加 frames
    fig.frames = frames

    # 創建滑動條的步驟
    sliders_steps = []
    for date in common_dates:
        date_str = date.strftime('%Y-%m')
        step = dict(
            method='animate',
            args=[[date_str], dict(mode='immediate', frame=dict(duration=300, redraw=True),
                                   transition=dict(duration=300))],
            label=date_str
        )
        sliders_steps.append(step)

    # 設置滑動條
    sliders = [dict(
        active=0,
        yanchor='top',
        xanchor='left',
        currentvalue=dict(
            font=dict(size=16),
            prefix='日期: ',
            visible=True,
            xanchor='right'
        ),
        transition=dict(duration=300),
        pad=dict(b=10, t=50),
        len=0.9,
        x=0.05,
        y=0,
        steps=sliders_steps
    )]

    # 設置播放/暫停按鈕
    updatemenus = [dict(
        type='buttons',
        showactive=False,
        y=1.15,
        x=0.1,
        xanchor='right',
        yanchor='top',
        pad=dict(t=0, r=10),
        buttons=[
            dict(
                label='▶ 播放',
                method='animate',
                args=[None, dict(
                    frame=dict(duration=500, redraw=True),
                    fromcurrent=True,
                    transition=dict(duration=300)
                )]
            ),
            dict(
                label='⏸ 暫停',
                method='animate',
                args=[[None], dict(
                    frame=dict(duration=0, redraw=False),
                    mode='immediate',
                    transition=dict(duration=0)
                )]
            )
        ]
    )]

    # 更新佈局
    fig.update_layout(
        title=dict(
            text='<b>美國 vs 德國 國債殖利率曲線</b><br><sup>互動式月度數據視覺化 (2022-2024)</sup>',
            x=0.5,
            font=dict(size=20)
        ),
        xaxis=dict(
            title='到期期限',
            tickmode='array',
            tickvals=[1, 3, 6, 12, 24, 36, 60, 84, 120, 180, 240, 360],
            ticktext=['1M', '3M', '6M', '1Y', '2Y', '3Y', '5Y', '7Y', '10Y', '15Y', '20Y', '30Y'],
            gridcolor='lightgray',
            showgrid=True
        ),
        yaxis=dict(
            title='殖利率 (%)',
            gridcolor='lightgray',
            showgrid=True,
            zeroline=True,
            zerolinecolor='red',
            zerolinewidth=1.5
        ),
        legend=dict(
            x=0.02,
            y=0.98,
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor='lightgray',
            borderwidth=1,
            font=dict(size=12)
        ),
        hovermode='x unified',
        sliders=sliders,
        updatemenus=updatemenus,
        template='plotly_white',
        height=700,
        margin=dict(t=120, b=100),
        annotations=[
            dict(
                text="使用滑動條或播放按鈕查看不同月份的殖利率曲線變化",
                x=0.5, y=-0.18,
                xref="paper", yref="paper",
                showarrow=False,
                font=dict(size=12, color="gray")
            )
        ]
    )

    return fig


def create_yield_comparison_chart(us_data: pd.DataFrame, de_data: pd.DataFrame) -> go.Figure:
    """創建殖利率比較時間序列圖"""

    # 重採樣為月頻
    us_monthly = us_data.resample('ME').last().dropna(how='all')
    de_monthly = de_data.resample('ME').last().dropna(how='all')

    # 創建子圖
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            '<b>2年期殖利率走勢</b>', '<b>10年期殖利率走勢</b>',
            '<b>美國 2年-10年期利差</b>', '<b>美德 10年期利差</b>'
        ),
        vertical_spacing=0.15,
        horizontal_spacing=0.1
    )

    # 2年期殖利率
    fig.add_trace(go.Scatter(
        x=us_monthly.index, y=us_monthly['2Y'],
        name='美國 2Y', line=dict(color='#1f77b4', width=2),
        hovertemplate='%{x|%Y-%m}<br>殖利率: %{y:.2f}%<extra>美國 2Y</extra>'
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=de_monthly.index, y=de_monthly['2Y'],
        name='德國 2Y', line=dict(color='#ff7f0e', width=2),
        hovertemplate='%{x|%Y-%m}<br>殖利率: %{y:.2f}%<extra>德國 2Y</extra>'
    ), row=1, col=1)

    # 10年期殖利率
    fig.add_trace(go.Scatter(
        x=us_monthly.index, y=us_monthly['10Y'],
        name='美國 10Y', line=dict(color='#1f77b4', width=2),
        hovertemplate='%{x|%Y-%m}<br>殖利率: %{y:.2f}%<extra>美國 10Y</extra>'
    ), row=1, col=2)

    fig.add_trace(go.Scatter(
        x=de_monthly.index, y=de_monthly['10Y'],
        name='德國 10Y', line=dict(color='#ff7f0e', width=2),
        hovertemplate='%{x|%Y-%m}<br>殖利率: %{y:.2f}%<extra>德國 10Y</extra>'
    ), row=1, col=2)

    # 美國 2-10年利差
    us_spread = us_monthly['10Y'] - us_monthly['2Y']
    colors = ['#2ca02c' if x >= 0 else '#d62728' for x in us_spread]
    fig.add_trace(go.Bar(
        x=us_monthly.index, y=us_spread,
        name='美國 2-10Y 利差',
        marker_color=colors,
        hovertemplate='%{x|%Y-%m}<br>利差: %{y:.2f}%<extra>美國利差</extra>'
    ), row=2, col=1)

    # 添加零線說明
    fig.add_hline(y=0, line_dash="dash", line_color="gray", row=2, col=1)

    # 美德10年期利差
    common_idx = us_monthly.index.intersection(de_monthly.index)
    spread_us_de = us_monthly.loc[common_idx, '10Y'] - de_monthly.loc[common_idx, '10Y']
    fig.add_trace(go.Scatter(
        x=common_idx, y=spread_us_de,
        name='美德 10Y 利差',
        fill='tozeroy',
        line=dict(color='#9467bd', width=2),
        fillcolor='rgba(148, 103, 189, 0.3)',
        hovertemplate='%{x|%Y-%m}<br>利差: %{y:.2f}%<extra>美德利差</extra>'
    ), row=2, col=2)

    # 更新佈局
    fig.update_layout(
        title=dict(
            text='<b>美德國債殖利率比較分析</b><br><sup>2022-2024 月度數據</sup>',
            x=0.5,
            font=dict(size=18)
        ),
        height=750,
        showlegend=True,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.18,
            xanchor='center',
            x=0.5
        ),
        template='plotly_white',
        hovermode='x unified'
    )

    # 更新 Y 軸標籤
    fig.update_yaxes(title_text='殖利率 (%)', row=1, col=1)
    fig.update_yaxes(title_text='殖利率 (%)', row=1, col=2)
    fig.update_yaxes(title_text='利差 (%)', row=2, col=1)
    fig.update_yaxes(title_text='利差 (%)', row=2, col=2)

    # 添加注釋
    fig.add_annotation(
        text="<b>綠色</b>=正常殖利率曲線 / <b>紅色</b>=倒掛",
        x=0.25, y=-0.25,
        xref="paper", yref="paper",
        showarrow=False,
        font=dict(size=10, color="gray")
    )

    return fig


def create_3d_yield_surface(us_data: pd.DataFrame) -> go.Figure:
    """創建3D殖利率曲面圖"""

    us_monthly = us_data.resample('ME').last().dropna(how='all')

    # 定義天期
    maturities = ['1M', '3M', '6M', '1Y', '2Y', '3Y', '5Y', '7Y', '10Y', '20Y', '30Y']
    maturity_nums = [1, 3, 6, 12, 24, 36, 60, 84, 120, 240, 360]

    # 過濾存在的列
    available_mats = [m for m in maturities if m in us_monthly.columns]
    available_nums = [maturity_nums[maturities.index(m)] for m in available_mats]

    # 準備數據
    z_data = us_monthly[available_mats].values
    x_data = available_nums
    y_data = list(range(len(us_monthly)))

    # 創建3D曲面圖
    fig = go.Figure(data=[go.Surface(
        x=x_data,
        y=y_data,
        z=z_data,
        colorscale='RdYlBu_r',
        colorbar=dict(title='殖利率 (%)'),
        hovertemplate='天期: %{x}月<br>月份: %{y}<br>殖利率: %{z:.2f}%<extra></extra>'
    )])

    # 更新佈局
    fig.update_layout(
        title=dict(
            text='<b>美國國債殖利率曲面</b><br><sup>3D 時間-天期-殖利率視覺化</sup>',
            x=0.5,
            font=dict(size=18)
        ),
        scene=dict(
            xaxis_title='到期期限 (月)',
            yaxis_title='時間 (月份序號)',
            zaxis_title='殖利率 (%)',
            camera=dict(
                eye=dict(x=1.5, y=-1.5, z=0.8)
            )
        ),
        height=700,
        margin=dict(t=80, b=50, l=50, r=50)
    )

    return fig


def main():
    """主程式"""
    print("=" * 60)
    print("美債及德債殖利率曲線視覺化工具")
    print("=" * 60)

    print("\n正在生成模擬數據...")
    print("(基於 2022-2024 年實際殖利率走勢)")
    print("-" * 60)

    # 生成數據
    print("生成美國國債殖利率數據...")
    us_yields = generate_us_treasury_yields()
    print(f"  ✓ 美國國債數據: {len(us_yields)} 日")

    print("生成德國國債殖利率數據...")
    de_yields = generate_german_bond_yields()
    print(f"  ✓ 德國國債數據: {len(de_yields)} 日")

    print("-" * 60)

    # 顯示最新的殖利率
    print("\n" + "=" * 60)
    print("最新殖利率數據 (2024-12-31)")
    print("=" * 60)

    print("\n🇺🇸 美國國債殖利率:")
    latest_us = us_yields.iloc[-1]
    for col in us_yields.columns:
        print(f"  {col:>5}: {latest_us[col]:>6.2f}%")

    print("\n🇩🇪 德國國債殖利率:")
    latest_de = de_yields.iloc[-1]
    for col in de_yields.columns:
        print(f"  {col:>5}: {latest_de[col]:>6.2f}%")

    # 創建圖表
    print("\n" + "-" * 60)
    print("正在生成交互式圖表...")

    # 圖1：動態殖利率曲線
    fig1 = create_interactive_yield_curve(us_yields, de_yields)
    fig1.write_html('/home/user/2nd-ML100Days/homework/yield_curve_interactive.html')
    print("✓ 動態殖利率曲線圖: yield_curve_interactive.html")

    # 圖2：殖利率比較分析
    fig2 = create_yield_comparison_chart(us_yields, de_yields)
    fig2.write_html('/home/user/2nd-ML100Days/homework/yield_comparison.html')
    print("✓ 殖利率比較圖: yield_comparison.html")

    # 圖3：3D殖利率曲面
    fig3 = create_3d_yield_surface(us_yields)
    fig3.write_html('/home/user/2nd-ML100Days/homework/yield_surface_3d.html')
    print("✓ 3D殖利率曲面圖: yield_surface_3d.html")

    # 保存數據為 CSV
    us_yields.to_csv('/home/user/2nd-ML100Days/homework/us_treasury_yields.csv')
    de_yields.to_csv('/home/user/2nd-ML100Days/homework/german_bond_yields.csv')

    print("\n" + "=" * 60)
    print("完成！已生成以下檔案:")
    print("=" * 60)
    print("""
📊 交互式圖表 (HTML):
   1. yield_curve_interactive.html - 動態殖利率曲線
      • 按播放可觀看月度變化動畫
      • 使用滑動條選擇特定月份
      • 滑鼠懸停查看詳細數據

   2. yield_comparison.html - 殖利率比較分析
      • 2年期/10年期殖利率走勢
      • 美國殖利率曲線倒掛指標
      • 美德利差趨勢

   3. yield_surface_3d.html - 3D殖利率曲面
      • 可旋轉拖曳的3D視圖
      • 展示時間-天期-殖利率關係

📁 原始數據 (CSV):
   • us_treasury_yields.csv
   • german_bond_yields.csv
""")
    print("請在瀏覽器中開啟 HTML 檔案查看互動式圖表")
    print("=" * 60)


if __name__ == "__main__":
    main()
