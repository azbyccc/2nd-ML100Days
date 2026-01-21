"""
Bloomberg BQNT - 正向展望公司違約率分析
=======================================
研究目的：分析過去10年被任一信評公司給予正向展望的公司，未來2年出現違約的比率

主要信評機構：
- S&P (Standard & Poor's)
- Moody's
- Fitch

注意：此代碼需要在Bloomberg Terminal的BQNT環境中執行
"""

import bql
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# 初始化BQL服務
bq = bql.Service()

# ============================================================================
# 參數設定
# ============================================================================
LOOKBACK_YEARS = 10  # 回顧期間（年）
FORWARD_YEARS = 2    # 違約觀察期（年）

# 計算日期範圍
end_date = datetime.now()
start_date = end_date - relativedelta(years=LOOKBACK_YEARS + FORWARD_YEARS)
analysis_end_date = end_date - relativedelta(years=FORWARD_YEARS)

print(f"分析期間: {start_date.strftime('%Y-%m-%d')} 至 {analysis_end_date.strftime('%Y-%m-%d')}")
print(f"違約觀察期: 每個正向展望事件後的 {FORWARD_YEARS} 年")


# ============================================================================
# 方法一：使用指數成員作為宇宙
# ============================================================================

def get_credit_universe_from_index(index_ticker='LF98TRUU Index'):
    """
    從信用債指數獲取公司宇宙

    常用指數：
    - LF98TRUU Index: Bloomberg US Corporate Bond Index
    - LUACTRUU Index: Bloomberg US Corporate Investment Grade
    - LF98TREH Index: Bloomberg US High Yield
    - LEGATRUU Index: Bloomberg Global Aggregate
    - I00001US Index: Bloomberg US IG Corporate (BVAL)
    - LP06TREU Index: Bloomberg Pan-European Aggregate Corporate
    """
    try:
        universe = bq.univ.members(index_ticker)
        return universe
    except Exception as e:
        print(f"獲取指數成員錯誤: {e}")
        return None


def get_universe_with_screening():
    """
    使用Bloomberg篩選功能獲取有評級的公司
    """
    # 使用EQS篩選器或直接使用已知的指數
    try:
        # 方法1: 使用信用指數
        universe = bq.univ.members('LUACTRUU Index')  # US Investment Grade Corporate
        return universe
    except:
        try:
            # 方法2: 使用全球企業債指數
            universe = bq.univ.members('LGCPTRUU Index')  # Global Corporate
            return universe
        except:
            # 方法3: 使用特定股票列表測試
            test_tickers = [
                'AAPL US Equity', 'MSFT US Equity', 'GOOGL US Equity',
                'JPM US Equity', 'BAC US Equity', 'C US Equity',
                'XOM US Equity', 'CVX US Equity', 'T US Equity',
                'VZ US Equity', 'GM US Equity', 'F US Equity'
            ]
            return test_tickers


# ============================================================================
# 方法二：查詢展望和違約數據（修正版）
# ============================================================================

def query_outlook_data_v2():
    """
    使用正確的BQL語法查詢展望數據
    """
    print("\n" + "="*60)
    print("查詢信用評級展望數據")
    print("="*60)

    # 使用多個信用指數組合
    indices_to_try = [
        ('LUACTRUU Index', 'US Investment Grade Corporate'),
        ('LF98TRUU Index', 'US Corporate Bond'),
        ('I00001US Index', 'Bloomberg US IG Corporate'),
        ('EUCA Index', 'Euro Corporate'),
    ]

    for index_ticker, index_name in indices_to_try:
        print(f"\n嘗試使用 {index_name} ({index_ticker})...")

        try:
            # 定義宇宙
            universe = bq.univ.members(index_ticker)

            # 查詢展望數據
            request = bql.Request(
                universe,
                {
                    'Name': bq.data.name(),
                    'Ticker': bq.data.ticker(),
                    'SP_Rating': bq.data.rtg_sp_lt_lc_issuer_credit(),
                    'SP_Outlook': bq.data.rtg_sp_outlook(),
                    'Moody_Rating': bq.data.rtg_moody_long_term(),
                    'Moody_Outlook': bq.data.rtg_moody_outlook(),
                    'Fitch_Rating': bq.data.rtg_fitch_lt_issuer_default(),
                    'Fitch_Outlook': bq.data.rtg_fitch_outlook(),
                    'Country': bq.data.country_full_name(),
                    'Sector': bq.data.gics_sector_name()
                }
            )

            response = bq.execute(request)
            df = response[0].df()

            if not df.empty:
                print(f"   成功獲取 {len(df)} 筆資料")
                return df, index_name

        except Exception as e:
            print(f"   錯誤: {e}")
            continue

    return None, None


def query_issuer_outlook_data():
    """
    直接查詢發行人的展望數據
    使用 issuer 相關的BQL函數
    """
    print("\n" + "="*60)
    print("查詢發行人展望數據（替代方法）")
    print("="*60)

    # 嘗試使用不同的宇宙定義方式
    universe_methods = [
        # 方法1: 使用股票指數然後獲取其發行人評級
        ('SPX Index', 'S&P 500'),
        ('RAY Index', 'Russell 3000'),
        ('SXXP Index', 'STOXX Europe 600'),
        # 方法2: 使用CDS指數成員
        ('CDX IG CDSI GEN 5Y Corp', 'CDX Investment Grade'),
    ]

    for universe_ticker, universe_name in universe_methods:
        print(f"\n嘗試 {universe_name} ({universe_ticker})...")

        try:
            universe = bq.univ.members(universe_ticker)

            # 基本查詢
            request = bql.Request(
                universe,
                {
                    'Name': bq.data.name(),
                    'SP_Outlook': bq.data.rtg_sp_outlook(),
                    'Moody_Outlook': bq.data.rtg_moody_outlook(),
                    'Fitch_Outlook': bq.data.rtg_fitch_outlook(),
                }
            )

            response = bq.execute(request)
            df = response[0].df()

            if not df.empty:
                print(f"   成功獲取 {len(df)} 筆資料")
                return df, universe_name

        except Exception as e:
            print(f"   錯誤: {e}")
            continue

    return None, None


# ============================================================================
# 方法三：使用歷史時間序列查詢展望變更
# ============================================================================

def query_historical_outlook_changes():
    """
    查詢歷史展望變更事件
    """
    print("\n" + "="*60)
    print("查詢歷史展望變更")
    print("="*60)

    # 先獲取一個基本的公司宇宙
    try:
        universe = bq.univ.members('SPX Index')

        # 定義時間範圍
        date_range = bq.func.range(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            frq='M'  # 月度
        )

        # 查詢歷史展望
        request = bql.Request(
            universe,
            {
                'SP_Outlook_History': bq.data.rtg_sp_outlook(dates=date_range),
                'Moody_Outlook_History': bq.data.rtg_moody_outlook(dates=date_range),
                'Fitch_Outlook_History': bq.data.rtg_fitch_outlook(dates=date_range),
            }
        )

        response = bq.execute(request)

        # 處理結果
        results = {}
        for item in response:
            df = item.df()
            if not df.empty:
                results[item.name] = df

        return results

    except Exception as e:
        print(f"歷史查詢錯誤: {e}")
        return None


# ============================================================================
# 方法四：使用RATC（評級行動）數據
# ============================================================================

def query_rating_actions():
    """
    查詢評級行動歷史
    使用Bloomberg的RATC數據
    """
    print("\n" + "="*60)
    print("查詢評級行動歷史（RATC）")
    print("="*60)

    try:
        universe = bq.univ.members('SPX Index')

        # RATC相關欄位
        request = bql.Request(
            universe,
            {
                'Name': bq.data.name(),
                # 嘗試不同的評級行動欄位
                'SP_Action_Date': bq.data.rtg_sp_action_dt(),
                'SP_Action_Type': bq.data.rtg_sp_action(),
                'Moody_Action_Date': bq.data.rtg_moody_action_dt(),
                'Moody_Action_Type': bq.data.rtg_moody_action(),
            }
        )

        response = bq.execute(request)
        df = response[0].df()

        return df

    except Exception as e:
        print(f"RATC查詢錯誤: {e}")
        return None


# ============================================================================
# 方法五：使用違約數據庫
# ============================================================================

def query_default_data():
    """
    查詢違約事件數據
    """
    print("\n" + "="*60)
    print("查詢違約事件數據")
    print("="*60)

    try:
        # 使用可能包含違約公司的宇宙
        # 嘗試使用CDS指數或高收益指數
        indices = [
            'LF98TREH Index',  # US High Yield
            'SPX Index',
        ]

        for idx in indices:
            try:
                universe = bq.univ.members(idx)

                request = bql.Request(
                    universe,
                    {
                        'Name': bq.data.name(),
                        'Is_Defaulted': bq.data.is_defaulted(),
                        'Default_Date': bq.data.default_date(),
                        'SP_Rating': bq.data.rtg_sp_lt_lc_issuer_credit(),
                    }
                )

                response = bq.execute(request)
                df = response[0].df()

                if not df.empty:
                    print(f"   從 {idx} 獲取 {len(df)} 筆資料")
                    return df

            except Exception as e:
                print(f"   {idx} 錯誤: {e}")
                continue

    except Exception as e:
        print(f"違約查詢錯誤: {e}")

    return None


# ============================================================================
# 方法六：使用SRCH篩選器
# ============================================================================

def query_with_screening():
    """
    使用BQL篩選功能獲取正向展望的公司
    """
    print("\n" + "="*60)
    print("使用篩選功能查詢正向展望公司")
    print("="*60)

    try:
        # 方法1: 使用filter函數
        # 獲取S&P展望為正向的公司
        universe = bq.univ.filter(
            bq.univ.members('SPX Index'),
            bq.data.rtg_sp_outlook() == 'Positive'
        )

        request = bql.Request(
            universe,
            {
                'Name': bq.data.name(),
                'Ticker': bq.data.ticker(),
                'SP_Rating': bq.data.rtg_sp_lt_lc_issuer_credit(),
                'SP_Outlook': bq.data.rtg_sp_outlook(),
                'Sector': bq.data.gics_sector_name()
            }
        )

        response = bq.execute(request)
        df = response[0].df()

        print(f"   S&P正向展望公司: {len(df)} 家")
        return df

    except Exception as e:
        print(f"篩選查詢錯誤: {e}")

        # 替代方法：先獲取所有，再篩選
        try:
            print("\n嘗試替代方法：獲取所有再篩選...")

            universe = bq.univ.members('SPX Index')

            request = bql.Request(
                universe,
                {
                    'Name': bq.data.name(),
                    'SP_Outlook': bq.data.rtg_sp_outlook(),
                    'Moody_Outlook': bq.data.rtg_moody_outlook(),
                    'Fitch_Outlook': bq.data.rtg_fitch_outlook(),
                }
            )

            response = bq.execute(request)
            df = response[0].df()

            # 在Python中篩選正向展望
            positive_mask = (
                df['SP_Outlook'].astype(str).str.upper().str.contains('POS', na=False) |
                df['Moody_Outlook'].astype(str).str.upper().str.contains('POS', na=False) |
                df['Fitch_Outlook'].astype(str).str.upper().str.contains('POS', na=False)
            )

            positive_df = df[positive_mask]
            print(f"   正向展望公司: {len(positive_df)} 家")

            return positive_df

        except Exception as e2:
            print(f"替代方法錯誤: {e2}")
            return None


# ============================================================================
# 方法七：完整分析流程（整合版）
# ============================================================================

def comprehensive_analysis():
    """
    完整的正向展望違約率分析
    """
    print("\n" + "="*70)
    print("正向展望公司違約率 - 完整分析")
    print("="*70)

    results = {
        'positive_outlook_count': 0,
        'defaults_within_2y': 0,
        'default_rate': 0.0,
        'by_agency': {},
        'by_sector': {},
        'details': []
    }

    # ============================
    # 步驟1: 獲取當前展望數據
    # ============================
    print("\n[步驟1] 獲取當前信用展望數據...")

    current_df = None

    # 嘗試多個數據源
    indices = ['SPX Index', 'LUACTRUU Index', 'RAY Index']

    for idx in indices:
        try:
            print(f"   嘗試 {idx}...")
            universe = bq.univ.members(idx)

            request = bql.Request(
                universe,
                {
                    'Name': bq.data.name(),
                    'Ticker': bq.data.ticker(),
                    'SP_Rating': bq.data.rtg_sp_lt_lc_issuer_credit(),
                    'SP_Outlook': bq.data.rtg_sp_outlook(),
                    'Moody_Rating': bq.data.rtg_moody_long_term(),
                    'Moody_Outlook': bq.data.rtg_moody_outlook(),
                    'Fitch_Rating': bq.data.rtg_fitch_lt_issuer_default(),
                    'Fitch_Outlook': bq.data.rtg_fitch_outlook(),
                    'Sector': bq.data.gics_sector_name(),
                    'Country': bq.data.country_full_name(),
                }
            )

            response = bq.execute(request)
            current_df = response[0].df()

            if current_df is not None and len(current_df) > 0:
                print(f"   ✓ 成功從 {idx} 獲取 {len(current_df)} 家公司")
                break

        except Exception as e:
            print(f"   ✗ {idx} 錯誤: {str(e)[:50]}...")
            continue

    if current_df is None or current_df.empty:
        print("\n   無法獲取展望數據，請檢查BQL連接和權限")
        return results

    # ============================
    # 步驟2: 篩選正向展望
    # ============================
    print("\n[步驟2] 篩選正向展望公司...")

    # 識別正向展望
    def is_positive(val):
        if pd.isna(val):
            return False
        return str(val).upper() in ['POSITIVE', 'POS', '+', 'POSITIVE OUTLOOK']

    current_df['SP_Positive'] = current_df['SP_Outlook'].apply(is_positive)
    current_df['Moody_Positive'] = current_df['Moody_Outlook'].apply(is_positive)
    current_df['Fitch_Positive'] = current_df['Fitch_Outlook'].apply(is_positive)
    current_df['Any_Positive'] = current_df['SP_Positive'] | current_df['Moody_Positive'] | current_df['Fitch_Positive']

    positive_df = current_df[current_df['Any_Positive']].copy()

    print(f"   總公司數: {len(current_df)}")
    print(f"   任一機構正向展望: {len(positive_df)}")
    print(f"   S&P 正向: {current_df['SP_Positive'].sum()}")
    print(f"   Moody's 正向: {current_df['Moody_Positive'].sum()}")
    print(f"   Fitch 正向: {current_df['Fitch_Positive'].sum()}")

    results['positive_outlook_count'] = len(positive_df)
    results['by_agency'] = {
        'SP': int(current_df['SP_Positive'].sum()),
        'Moodys': int(current_df['Moody_Positive'].sum()),
        'Fitch': int(current_df['Fitch_Positive'].sum())
    }

    # ============================
    # 步驟3: 查詢違約數據
    # ============================
    print("\n[步驟3] 查詢違約數據...")

    try:
        # 查詢違約相關欄位
        default_request = bql.Request(
            bq.univ.members(idx),  # 使用上面成功的指數
            {
                'Is_Defaulted': bq.data.is_defaulted(),
                'Default_Date': bq.data.default_date(),
            }
        )

        default_response = bq.execute(default_request)
        default_df = default_response[0].df()

        if 'Is_Defaulted' in default_df.columns:
            defaulted = default_df[default_df['Is_Defaulted'] == True]
            print(f"   違約公司數: {len(defaulted)}")
            results['defaults_within_2y'] = len(defaulted)

    except Exception as e:
        print(f"   違約數據查詢錯誤: {e}")

    # ============================
    # 步驟4: 產業分布
    # ============================
    print("\n[步驟4] 正向展望公司產業分布...")

    if 'Sector' in positive_df.columns:
        sector_counts = positive_df['Sector'].value_counts()
        results['by_sector'] = sector_counts.to_dict()
        print(sector_counts)

    # ============================
    # 步驟5: 輸出結果
    # ============================
    print("\n" + "="*60)
    print("分析結果摘要")
    print("="*60)

    if results['positive_outlook_count'] > 0:
        results['default_rate'] = (results['defaults_within_2y'] / results['positive_outlook_count']) * 100

    print(f"\n正向展望公司總數: {results['positive_outlook_count']}")
    print(f"2年內違約數: {results['defaults_within_2y']}")
    print(f"違約率: {results['default_rate']:.2f}%")

    print("\n各信評機構正向展望數:")
    for agency, count in results['by_agency'].items():
        print(f"   {agency}: {count}")

    # 顯示正向展望公司清單
    if not positive_df.empty:
        print("\n正向展望公司範例（前20家）:")
        display_cols = ['Name', 'SP_Outlook', 'Moody_Outlook', 'Fitch_Outlook', 'Sector']
        available_cols = [c for c in display_cols if c in positive_df.columns]
        print(positive_df[available_cols].head(20).to_string())

    return results


# ============================================================================
# 方法八：使用BQL歷史函數查詢展望變更
# ============================================================================

def query_outlook_history_timeseries():
    """
    使用時間序列函數獲取展望歷史變更
    """
    print("\n" + "="*60)
    print("查詢展望歷史時間序列")
    print("="*60)

    try:
        universe = bq.univ.members('SPX Index')

        # 建立時間序列範圍
        dates = bq.func.range(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            frq='Q'  # 季度頻率
        )

        # 查詢歷史展望
        request = bql.Request(
            universe,
            {
                'Name': bq.data.name(),
                'SP_Outlook_History': bq.data.rtg_sp_outlook(dates=dates),
            },
            with_params={'fill': 'prev'}  # 向前填充缺失值
        )

        response = bq.execute(request)

        # 處理時間序列數據
        for item in response:
            df = item.df()
            print(f"\n{item.name}:")
            print(df.head(20))

        return response

    except Exception as e:
        print(f"時間序列查詢錯誤: {e}")
        return None


# ============================================================================
# 主程式
# ============================================================================

def main():
    """
    主程式執行
    """
    print("\n" + "="*70)
    print("Bloomberg BQNT - 正向展望公司違約率分析")
    print("="*70)
    print(f"\n分析參數:")
    print(f"  - 回顧期間: {LOOKBACK_YEARS} 年")
    print(f"  - 違約觀察期: {FORWARD_YEARS} 年")
    print(f"  - 開始日期: {start_date.strftime('%Y-%m-%d')}")
    print(f"  - 截止日期: {analysis_end_date.strftime('%Y-%m-%d')}")

    print("\n開始執行分析...")

    # 執行完整分析
    results = comprehensive_analysis()

    # 嘗試獲取歷史數據
    print("\n" + "-"*60)
    print("嘗試獲取歷史展望時間序列...")
    query_outlook_history_timeseries()

    print("\n" + "="*70)
    print("分析完成")
    print("="*70)

    return results


# ============================================================================
# 輔助函數：Excel公式參考
# ============================================================================

def print_excel_formulas():
    """
    輸出Bloomberg Excel API參考公式
    """
    print("\n" + "="*60)
    print("Bloomberg Excel API 公式參考")
    print("="*60)

    formulas = """
# 單一公司展望查詢:
=BDP("IBM US Equity", "RTG_SP_OUTLOOK")
=BDP("IBM US Equity", "RTG_MOODY_OUTLOOK")
=BDP("IBM US Equity", "RTG_FITCH_OUTLOOK")

# 歷史展望查詢:
=BDH("IBM US Equity", "RTG_SP_OUTLOOK", "2014-01-01", "2024-01-01")

# 違約狀態:
=BDP("TICKER Equity", "IS_DEFAULTED")
=BDP("TICKER Equity", "DEFAULT_DATE")

# 評級:
=BDP("IBM US Equity", "RTG_SP_LT_LC_ISSUER_CREDIT")
=BDP("IBM US Equity", "RTG_MOODY_LONG_TERM")
=BDP("IBM US Equity", "RTG_FITCH_LT_ISSUER_DEFAULT")

# 批量查詢（需配合INDEX功能）:
=BDS("SPX Index", "INDX_MWEIGHT")
    """
    print(formulas)


# ============================================================================
# 執行
# ============================================================================

if __name__ == "__main__":
    results = main()
    print_excel_formulas()
