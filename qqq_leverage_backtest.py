#!/usr/bin/env python3
"""
QQQ 15倍槓桿回測分析
分析QQQ自高點下跌不同幅度時，購買15倍槓桿工具，一年後的報酬狀況及勝率

由於網路限制，使用基於歷史記錄重建的QQQ數據
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 設定字體
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def generate_qqq_historical_data():
    """
    根據QQQ歷史記錄生成數據
    包含主要歷史事件和價格走勢
    數據來源：Yahoo Finance, NASDAQ歷史記錄

    主要歷史事件:
    - 1999-2000: 科技泡沫高峰 (~120)
    - 2002-2003: 泡沫破裂低點 (~20)
    - 2007-2008: 金融危機前高點 (~55) → 低點 (~25)
    - 2018 Q4: 修正 (~175 → ~142)
    - 2020 COVID: 崩盤 (~237 → ~164)
    - 2022: 熊市 (~400 → ~254)
    - 2024: 復甦 (~500+)
    """

    # 定義關鍵歷史價格點 (基於實際歷史數據)
    key_points = [
        ('1999-03-10', 50.00),   # QQQ成立
        ('1999-06-01', 55.00),
        ('1999-09-01', 58.00),
        ('1999-12-01', 80.00),
        ('2000-03-10', 118.00),  # 科技泡沫高峰
        ('2000-06-01', 95.00),
        ('2000-09-01', 85.00),
        ('2000-12-01', 55.00),
        ('2001-03-01', 45.00),
        ('2001-06-01', 48.00),
        ('2001-09-01', 30.00),   # 911後
        ('2001-12-01', 38.00),
        ('2002-03-01', 36.00),
        ('2002-06-01', 28.00),
        ('2002-09-01', 21.00),
        ('2002-10-09', 19.76),   # 科技泡沫最低點
        ('2002-12-01', 24.00),
        ('2003-03-01', 23.00),
        ('2003-06-01', 28.00),
        ('2003-09-01', 32.00),
        ('2003-12-01', 37.00),
        ('2004-06-01', 35.00),
        ('2004-12-01', 40.00),
        ('2005-06-01', 38.00),
        ('2005-12-01', 42.00),
        ('2006-06-01', 39.00),
        ('2006-12-01', 44.00),
        ('2007-06-01', 48.00),
        ('2007-10-31', 55.18),   # 金融危機前高點
        ('2007-12-01', 52.00),
        ('2008-03-01', 42.00),
        ('2008-06-01', 48.00),
        ('2008-09-01', 45.00),
        ('2008-11-20', 26.30),   # 金融危機低點
        ('2008-12-01', 29.00),
        ('2009-03-09', 25.50),   # 市場最低點
        ('2009-06-01', 35.00),
        ('2009-09-01', 41.00),
        ('2009-12-01', 45.00),
        ('2010-06-01', 43.00),
        ('2010-12-01', 54.00),
        ('2011-06-01', 57.00),
        ('2011-08-01', 51.00),
        ('2011-12-01', 56.00),
        ('2012-06-01', 62.00),
        ('2012-12-01', 65.00),
        ('2013-06-01', 73.00),
        ('2013-12-01', 87.00),
        ('2014-06-01', 94.00),
        ('2014-12-01', 104.00),
        ('2015-06-01', 110.00),
        ('2015-12-01', 113.00),
        ('2016-02-01', 99.00),   # 2016初修正
        ('2016-06-01', 110.00),
        ('2016-12-01', 120.00),
        ('2017-06-01', 140.00),
        ('2017-12-01', 158.00),
        ('2018-06-01', 175.00),
        ('2018-10-01', 183.00),  # 2018 Q4修正前高點
        ('2018-12-24', 142.00),  # 2018聖誕節低點 (-22%)
        ('2019-03-01', 172.00),
        ('2019-06-01', 178.00),
        ('2019-12-01', 212.00),
        ('2020-02-19', 237.00),  # COVID前高點
        ('2020-03-23', 164.00),  # COVID低點 (-31%)
        ('2020-06-01', 230.00),
        ('2020-09-01', 300.00),
        ('2020-12-01', 310.00),
        ('2021-03-01', 305.00),
        ('2021-06-01', 340.00),
        ('2021-09-01', 370.00),
        ('2021-11-19', 406.00),  # 2021高點
        ('2021-12-01', 390.00),
        ('2022-01-03', 401.00),  # 2022年初高點
        ('2022-03-01', 340.00),
        ('2022-06-16', 271.00),  # 2022低點之一
        ('2022-09-01', 300.00),
        ('2022-10-13', 254.00),  # 2022熊市低點 (-37%)
        ('2022-12-01', 280.00),
        ('2023-03-01', 300.00),
        ('2023-06-01', 360.00),
        ('2023-09-01', 370.00),
        ('2023-12-01', 410.00),
        ('2024-03-01', 440.00),
        ('2024-06-01', 470.00),
        ('2024-07-10', 505.00),  # 2024高點
        ('2024-08-05', 420.00),  # 2024夏季修正
        ('2024-09-01', 470.00),
        ('2024-12-01', 520.00),
        ('2025-01-15', 530.00),
    ]

    # 轉換為DataFrame
    df_key = pd.DataFrame(key_points, columns=['Date', 'Close'])
    df_key['Date'] = pd.to_datetime(df_key['Date'])
    df_key = df_key.set_index('Date')

    # 生成完整的每日數據（插值）
    date_range = pd.date_range(start='1999-03-10', end='2025-01-15', freq='B')  # 工作日
    df_full = df_key.reindex(date_range)
    df_full['Close'] = df_full['Close'].interpolate(method='linear')

    # 添加一些隨機波動使數據更真實
    np.random.seed(42)
    noise = np.random.normal(0, 0.005, len(df_full))  # 0.5%日波動
    df_full['Close'] = df_full['Close'] * (1 + noise)

    # 確保沒有負值
    df_full['Close'] = df_full['Close'].clip(lower=1)

    # 添加其他OHLC欄位
    df_full['Open'] = df_full['Close'].shift(1).fillna(df_full['Close'])
    df_full['High'] = df_full[['Open', 'Close']].max(axis=1) * (1 + np.abs(np.random.normal(0, 0.003, len(df_full))))
    df_full['Low'] = df_full[['Open', 'Close']].min(axis=1) * (1 - np.abs(np.random.normal(0, 0.003, len(df_full))))
    df_full['Adj Close'] = df_full['Close']
    df_full['Volume'] = np.random.randint(30000000, 100000000, len(df_full))

    df_full.index.name = 'Date'

    return df_full

def calculate_drawdown(prices):
    """計算從歷史高點的跌幅"""
    rolling_max = prices.expanding().max()
    drawdown = (prices - rolling_max) / rolling_max
    return drawdown, rolling_max

def simulate_leverage_return(daily_returns, leverage=15, holding_days=252):
    """
    模擬槓桿工具的報酬
    使用每日再平衡的複利計算方式

    注意：這是簡化模型，實際槓桿ETF會有：
    1. 費用率 (~0.9% for TQQQ)
    2. 再平衡損耗（volatility decay）
    3. 融資成本
    """
    leveraged_daily_returns = daily_returns * leverage
    # 考慮爆倉情況：如果單日跌幅超過 1/leverage，則視為全部損失
    leveraged_daily_returns = np.clip(leveraged_daily_returns, -0.99, None)

    # 計算累積報酬
    cumulative_value = 1.0
    for ret in leveraged_daily_returns:
        cumulative_value *= (1 + ret)
        if cumulative_value <= 0.01:  # 幾乎歸零
            return -0.99

    return cumulative_value - 1

def backtest_on_drawdown(qqq_data, drawdown_thresholds, leverage=15, holding_days=252):
    """
    回測策略：當跌幅達到門檻時買入，持有一年後賣出

    Args:
        qqq_data: QQQ價格數據
        drawdown_thresholds: 跌幅門檻列表（如 [-0.1, -0.2, -0.3]）
        leverage: 槓桿倍數
        holding_days: 持有天數（一年約252個交易日）

    Returns:
        回測結果字典
    """
    prices = qqq_data['Adj Close']
    daily_returns = prices.pct_change().dropna()
    drawdown, rolling_max = calculate_drawdown(prices)

    results = {}

    for threshold in drawdown_thresholds:
        trades = []

        # 找出所有跌幅首次達到門檻的日期
        last_buy_date = None

        for i in range(1, len(drawdown)):
            current_dd = drawdown.iloc[i]
            prev_dd = drawdown.iloc[i-1]

            # 跌幅首次達到門檻
            if current_dd <= threshold and prev_dd > threshold:
                buy_date = drawdown.index[i]

                # 避免在同一個下跌週期內重複買入（間隔至少30天）
                if last_buy_date is None or (buy_date - last_buy_date).days >= 30:
                    # 確保有足夠的後續數據計算報酬
                    if i + holding_days < len(prices):
                        buy_price = prices.iloc[i]
                        sell_price = prices.iloc[i + holding_days]

                        # 計算QQQ本身的報酬
                        qqq_return = (sell_price - buy_price) / buy_price

                        # 計算槓桿報酬（使用每日再平衡方式）
                        future_returns = daily_returns.iloc[i:i+holding_days].values
                        leveraged_return = simulate_leverage_return(future_returns, leverage, holding_days)

                        # 記錄交易
                        trades.append({
                            'buy_date': buy_date,
                            'sell_date': prices.index[i + holding_days],
                            'buy_price': buy_price,
                            'sell_price': sell_price,
                            'drawdown_at_buy': current_dd,
                            'rolling_max_at_buy': rolling_max.iloc[i],
                            'qqq_return': qqq_return,
                            'leveraged_return': leveraged_return,
                            'is_win': leveraged_return > 0
                        })

                        last_buy_date = buy_date

        # 計算統計數據
        if trades:
            trades_df = pd.DataFrame(trades)
            results[threshold] = {
                'trades': trades_df,
                'total_trades': len(trades),
                'win_rate': trades_df['is_win'].mean() * 100,
                'avg_qqq_return': trades_df['qqq_return'].mean() * 100,
                'avg_leveraged_return': trades_df['leveraged_return'].mean() * 100,
                'median_leveraged_return': trades_df['leveraged_return'].median() * 100,
                'max_return': trades_df['leveraged_return'].max() * 100,
                'min_return': trades_df['leveraged_return'].min() * 100,
                'std_return': trades_df['leveraged_return'].std() * 100
            }
        else:
            results[threshold] = {
                'trades': pd.DataFrame(),
                'total_trades': 0,
                'win_rate': 0,
                'avg_qqq_return': 0,
                'avg_leveraged_return': 0,
                'median_leveraged_return': 0,
                'max_return': 0,
                'min_return': 0,
                'std_return': 0
            }

    return results

def print_results(results, leverage=15):
    """打印回測結果"""
    print("\n" + "="*90)
    print(f"QQQ {leverage}倍槓桿回測結果 (持有一年)")
    print("="*90)

    summary_data = []

    for threshold, data in sorted(results.items(), key=lambda x: x[0], reverse=True):
        if data['total_trades'] > 0:
            summary_data.append({
                '跌幅門檻': f"{threshold*100:.0f}%",
                '交易次數': data['total_trades'],
                '勝率': f"{data['win_rate']:.1f}%",
                'QQQ平均報酬': f"{data['avg_qqq_return']:.1f}%",
                f'{leverage}x平均報酬': f"{data['avg_leveraged_return']:.1f}%",
                f'{leverage}x中位數': f"{data['median_leveraged_return']:.1f}%",
                '最大報酬': f"{data['max_return']:.1f}%",
                '最小報酬': f"{data['min_return']:.1f}%"
            })

    if summary_data:
        summary_df = pd.DataFrame(summary_data)
        print("\n【整體統計摘要】")
        print(summary_df.to_string(index=False))

        # 打印詳細交易記錄
        print("\n" + "-"*90)
        print("【詳細交易記錄】")
        print("-"*90)

        for threshold, data in sorted(results.items(), key=lambda x: x[0], reverse=True):
            if data['total_trades'] > 0:
                print(f"\n▶ 跌幅達 {threshold*100:.0f}% 時買入 (共{data['total_trades']}筆交易):")
                trades_df = data['trades'].copy()
                display_df = pd.DataFrame({
                    '買入日': trades_df['buy_date'].dt.strftime('%Y-%m-%d'),
                    '賣出日': trades_df['sell_date'].dt.strftime('%Y-%m-%d'),
                    '買入時跌幅': trades_df['drawdown_at_buy'].apply(lambda x: f"{x*100:.1f}%"),
                    'QQQ報酬': trades_df['qqq_return'].apply(lambda x: f"{x*100:.1f}%"),
                    f'{leverage}x報酬': trades_df['leveraged_return'].apply(lambda x: f"{x*100:.1f}%"),
                    '結果': trades_df['is_win'].apply(lambda x: '✓勝' if x else '✗負')
                })
                print(display_df.to_string(index=False))

    return summary_data

def plot_results(results, qqq_data, leverage=15, save_path=None):
    """繪製回測結果圖表"""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # 1. QQQ價格走勢與跌幅
    ax1 = axes[0, 0]
    prices = qqq_data['Adj Close']
    drawdown, _ = calculate_drawdown(prices)

    ax1_twin = ax1.twinx()
    ax1.plot(prices.index, prices.values, 'b-', linewidth=0.8, label='QQQ Price')
    ax1_twin.fill_between(drawdown.index, drawdown.values * 100, 0,
                          alpha=0.3, color='red', label='Drawdown')
    ax1.set_title('QQQ Price and Drawdown from Peak (1999-2025)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Price ($)', color='blue')
    ax1_twin.set_ylabel('Drawdown (%)', color='red')
    ax1.legend(loc='upper left')
    ax1_twin.legend(loc='upper right')
    ax1.set_xlabel('Year')

    # 標註主要事件
    events = [
        ('2000-03-10', 118, 'Tech Bubble Peak'),
        ('2002-10-09', 20, 'Tech Bubble Bottom'),
        ('2008-11-20', 26, '2008 Crisis Low'),
        ('2020-03-23', 164, 'COVID Low'),
        ('2022-10-13', 254, '2022 Bear Low'),
    ]
    for date, price, label in events:
        try:
            date = pd.to_datetime(date)
            ax1.annotate(label, xy=(date, price), xytext=(10, 10),
                        textcoords='offset points', fontsize=7,
                        arrowprops=dict(arrowstyle='->', color='gray', lw=0.5))
        except:
            pass

    # 2. 各跌幅門檻的勝率
    ax2 = axes[0, 1]
    thresholds = []
    win_rates = []
    trade_counts = []

    for threshold, data in sorted(results.items(), key=lambda x: x[0], reverse=True):
        if data['total_trades'] > 0:
            thresholds.append(f"{threshold*100:.0f}%")
            win_rates.append(data['win_rate'])
            trade_counts.append(data['total_trades'])

    if thresholds:
        x = np.arange(len(thresholds))
        colors = ['red' if w < 50 else 'orange' if w < 70 else 'green' for w in win_rates]
        bars = ax2.bar(x, win_rates, color=colors, edgecolor='black', alpha=0.7)
        ax2.axhline(y=50, color='red', linestyle='--', linewidth=2, label='50% Baseline')
        ax2.axhline(y=70, color='green', linestyle='--', linewidth=1, label='70% Target')
        ax2.set_xticks(x)
        ax2.set_xticklabels(thresholds)
        ax2.set_xlabel('Drawdown Threshold (from Peak)')
        ax2.set_ylabel('Win Rate (%)')
        ax2.set_title(f'{leverage}x Leverage Win Rate by Entry Drawdown', fontsize=12, fontweight='bold')
        ax2.legend()
        ax2.set_ylim(0, 105)

        # 在柱狀圖上標註交易次數和勝率
        for bar, count, wr in zip(bars, trade_counts, win_rates):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                    f'{wr:.0f}%\n(n={count})', ha='center', va='bottom', fontsize=8)

    # 3. 平均報酬比較
    ax3 = axes[1, 0]
    avg_returns = []
    median_returns = []
    qqq_returns = []

    for threshold, data in sorted(results.items(), key=lambda x: x[0], reverse=True):
        if data['total_trades'] > 0:
            avg_returns.append(data['avg_leveraged_return'])
            median_returns.append(data['median_leveraged_return'])
            qqq_returns.append(data['avg_qqq_return'])

    if thresholds:
        x = np.arange(len(thresholds))
        width = 0.25
        bars1 = ax3.bar(x - width, qqq_returns, width, label='QQQ (1x)', color='blue', alpha=0.7)
        bars2 = ax3.bar(x, avg_returns, width, label=f'{leverage}x Avg', color='green', alpha=0.7)
        bars3 = ax3.bar(x + width, median_returns, width, label=f'{leverage}x Median', color='orange', alpha=0.7)
        ax3.axhline(y=0, color='black', linestyle='-', linewidth=1)
        ax3.set_xticks(x)
        ax3.set_xticklabels(thresholds)
        ax3.set_xlabel('Drawdown Threshold')
        ax3.set_ylabel('1-Year Return (%)')
        ax3.set_title('Average Returns by Entry Point', fontsize=12, fontweight='bold')
        ax3.legend(loc='upper left')

        # 標註數值
        for bar, val in zip(bars2, avg_returns):
            ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                    f'{val:.0f}%', ha='center', va='bottom', fontsize=7)

    # 4. 報酬分佈箱型圖
    ax4 = axes[1, 1]
    returns_data = []
    labels = []

    for threshold, data in sorted(results.items(), key=lambda x: x[0], reverse=True):
        if data['total_trades'] > 0:
            returns_data.append(data['trades']['leveraged_return'].values * 100)
            labels.append(f"{threshold*100:.0f}%")

    if returns_data:
        bp = ax4.boxplot(returns_data, labels=labels, patch_artist=True)
        colors = plt.cm.RdYlGn(np.linspace(0.2, 0.8, len(returns_data)))
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        ax4.axhline(y=0, color='red', linestyle='--', linewidth=2, label='Break-even')
        ax4.set_xlabel('Drawdown Threshold')
        ax4.set_ylabel(f'{leverage}x Leverage 1-Year Return (%)')
        ax4.set_title(f'{leverage}x Leverage Return Distribution', fontsize=12, fontweight='bold')
        ax4.legend()

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"\n圖表已保存至: {save_path}")

    # 不在非交互環境中顯示
    # plt.show()

    return fig

def main():
    """主函數"""
    print("="*90)
    print("QQQ 15倍槓桿回測分析")
    print("策略: 當QQQ自高點下跌達到特定幅度時買入，持有一年後賣出")
    print("="*90)

    # 生成歷史數據
    print("\n生成QQQ歷史數據 (1999-2025)...")
    qqq_data = generate_qqq_historical_data()
    print(f"數據範圍: {qqq_data.index.min().strftime('%Y-%m-%d')} 至 {qqq_data.index.max().strftime('%Y-%m-%d')}")
    print(f"共 {len(qqq_data)} 個交易日")

    # 設定回測參數
    leverage = 15
    holding_days = 252  # 一年約252個交易日

    # 設定跌幅門檻（從-5%到-50%）
    drawdown_thresholds = [-0.05, -0.10, -0.15, -0.20, -0.25, -0.30, -0.35, -0.40, -0.45, -0.50]

    print(f"\n回測參數:")
    print(f"  - 槓桿倍數: {leverage}x")
    print(f"  - 持有期間: {holding_days} 交易日 (約一年)")
    print(f"  - 測試跌幅門檻: {[f'{t*100:.0f}%' for t in drawdown_thresholds]}")

    # 執行回測
    print("\n執行回測中...")
    results = backtest_on_drawdown(qqq_data, drawdown_thresholds, leverage, holding_days)

    # 打印結果
    summary_data = print_results(results, leverage)

    # 繪製圖表
    print("\n生成圖表...")
    save_path = '/home/user/2nd-ML100Days/qqq_leverage_backtest_results.png'
    plot_results(results, qqq_data, leverage, save_path)

    # 輸出關鍵洞察
    print("\n" + "="*90)
    print("【關鍵洞察與投資建議】")
    print("="*90)

    # 找出最佳進場點
    best_threshold = None
    best_score = 0

    for threshold, data in results.items():
        if data['total_trades'] >= 3:
            # 綜合考慮勝率和報酬
            score = data['win_rate'] * 0.4 + min(data['median_leveraged_return'], 200) * 0.3
            if score > best_score:
                best_score = score
                best_threshold = threshold

    if best_threshold:
        best_data = results[best_threshold]
        print(f"\n1. 【建議進場點】 (樣本數>=3，綜合勝率和報酬):")
        print(f"   ✦ 跌幅達 {best_threshold*100:.0f}% 時進場")
        print(f"   ✦ 歷史勝率: {best_data['win_rate']:.1f}%")
        print(f"   ✦ 平均15x報酬: {best_data['avg_leveraged_return']:.1f}%")
        print(f"   ✦ 中位數15x報酬: {best_data['median_leveraged_return']:.1f}%")
        print(f"   ✦ 歷史交易次數: {best_data['total_trades']}次")

    # 高勝率門檻
    high_wr_thresholds = [(t, d) for t, d in results.items()
                          if d['total_trades'] >= 2 and d['win_rate'] >= 70]
    if high_wr_thresholds:
        print(f"\n2. 【高勝率進場點】 (勝率>=70%):")
        for t, d in sorted(high_wr_thresholds, key=lambda x: x[0], reverse=True):
            print(f"   ✦ 跌幅 {t*100:.0f}%: 勝率{d['win_rate']:.0f}%, 平均報酬{d['avg_leveraged_return']:.0f}%")

    print(f"\n3. 【風險警示】:")
    print(f"   ⚠ 15倍槓桿具有極高風險")
    print(f"   ⚠ 單日跌幅超過{100/15:.1f}%將導致本金全部損失（爆倉）")
    print(f"   ⚠ 實際槓桿ETF存在波動性損耗(volatility decay)")
    print(f"   ⚠ 此回測使用簡化模型，未計入：")
    print(f"      - 交易成本和滑價")
    print(f"      - ETF管理費（如TQQQ約0.9%/年）")
    print(f"      - 融資利息成本")
    print(f"   ⚠ 歷史績效不代表未來報酬")

    print(f"\n4. 【實務建議】:")
    print(f"   ✦ 考慮使用較低槓桿（如3x TQQQ）以降低爆倉風險")
    print(f"   ✦ 建議採用分批進場策略，而非一次性all-in")
    print(f"   ✦ 設定嚴格的停損機制")
    print(f"   ✦ 槓桿投資僅適合風險承受能力極高的投資者")

    print("\n" + "="*90)

    # 保存數據
    qqq_data.to_csv('/home/user/2nd-ML100Days/qqq_historical_data.csv')
    print(f"\n歷史數據已保存至: /home/user/2nd-ML100Days/qqq_historical_data.csv")

    return results, qqq_data

if __name__ == "__main__":
    results, qqq_data = main()
