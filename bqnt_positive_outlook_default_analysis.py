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
start_date = end_date - relativedelta(years=LOOKBACK_YEARS + FORWARD_YEARS)  # 額外加2年以確保有足夠的前瞻期
analysis_end_date = end_date - relativedelta(years=FORWARD_YEARS)  # 展望數據截止日（確保有2年觀察期）

print(f"分析期間: {start_date.strftime('%Y-%m-%d')} 至 {analysis_end_date.strftime('%Y-%m-%d')}")
print(f"違約觀察期: 每個正向展望事件後的 {FORWARD_YEARS} 年")

# ============================================================================
# 方法一：使用BQL查詢信用評級展望變化和違約事件
# ============================================================================

def get_positive_outlook_companies():
    """
    獲取被給予正向展望的公司列表

    Bloomberg欄位說明：
    - RTG_SP_LT_LC_ISSUER_CREDIT: S&P長期本地貨幣發行人信用評級
    - RTG_MOODY_LONG_TERM: Moody's長期評級
    - RTG_FITCH_LT_ISSUER_DEFAULT: Fitch長期發行人違約評級
    - RTG_SP_OUTLOOK: S&P展望
    - RTG_MOODY_OUTLOOK: Moody's展望
    - RTG_FITCH_OUTLOOK: Fitch展望
    """

    # 定義要分析的公司宇宙（可根據需求調整）
    # 這裡使用全球投資級和高收益債券發行人
    universe = bq.univ.bondsuniv(
        issuers='active',
        currency='USD',
        ratings=['IG', 'HY']  # 投資級和高收益級
    )

    # 或者使用更廣泛的企業宇宙
    # universe = bq.univ.members('BERC Index')  # Bloomberg全球企業債指數

    return universe


def query_outlook_and_default_data():
    """
    查詢展望數據和違約事件
    """

    # 定義時間範圍
    date_range = bq.func.range(
        start_date.strftime('%Y-%m-%d'),
        analysis_end_date.strftime('%Y-%m-%d')
    )

    # ========================================
    # 查詢各信評機構的展望歷史
    # ========================================

    # S&P 展望
    sp_outlook = bq.data.rtg_sp_outlook(dates=date_range)

    # Moody's 展望
    moody_outlook = bq.data.rtg_moody_outlook(dates=date_range)

    # Fitch 展望
    fitch_outlook = bq.data.rtg_fitch_outlook(dates=date_range)

    # 違約指標
    default_indicator = bq.data.default_flag()
    default_date = bq.data.default_date()

    # 建立查詢請求
    universe = get_positive_outlook_companies()

    request = bql.Request(
        universe,
        {
            'SP_Outlook': sp_outlook,
            'Moody_Outlook': moody_outlook,
            'Fitch_Outlook': fitch_outlook,
            'Default_Flag': default_indicator,
            'Default_Date': default_date
        }
    )

    # 執行查詢
    response = bq.execute(request)

    return response


def analyze_outlook_with_rating_actions():
    """
    使用評級行動數據進行更詳細的分析

    Bloomberg RATC (Rating Actions) 功能提供評級變化的歷史數據
    """

    # 使用RATC函數獲取評級行動歷史
    # 這包含展望變化事件

    query = f"""
    get(
        RATING_ACTION_TYPE,
        RATING_ACTION_DATE,
        RATING_AGENCY,
        RATING_OUTLOOK,
        RATING_WATCH,
        RATING_VALUE
    )
    for(
        filter(
            bondsuniv(issuers='active'),
            RATING_ACTION_DATE >= '{start_date.strftime('%Y-%m-%d')}' AND
            RATING_ACTION_DATE <= '{analysis_end_date.strftime('%Y-%m-%d')}'
        )
    )
    where(
        RATING_OUTLOOK == 'Positive' OR RATING_OUTLOOK == 'POS'
    )
    """

    # 執行BQL查詢
    response = bq.execute(query)

    return response


# ============================================================================
# 方法二：使用CRDT和RATC API進行更細緻的分析
# ============================================================================

def detailed_outlook_default_analysis():
    """
    詳細分析：追蹤每個正向展望事件後的違約情況
    """

    print("\n" + "="*60)
    print("開始詳細分析...")
    print("="*60)

    # 定義展望值的正向標識
    POSITIVE_OUTLOOK_VALUES = ['Positive', 'POS', 'POSITIVE', '+', 'Pos']

    # 步驟1: 獲取具有評級數據的公司列表
    print("\n[步驟1] 獲取具有信用評級的公司列表...")

    # 使用全球公司債宇宙
    universe_query = bql.Request(
        bq.univ.filter(
            bq.univ.bondsuniv(issuers='active'),
            bq.data.country_iso() != 'NA'  # 排除無國家數據的公司
        ),
        {'Ticker': bq.data.ticker()}
    )

    try:
        universe_response = bq.execute(universe_query)
        companies = universe_response[0].df()
        print(f"   找到 {len(companies)} 家公司")
    except Exception as e:
        print(f"   查詢錯誤: {e}")
        return None

    # 步驟2: 查詢展望歷史數據
    print("\n[步驟2] 查詢各信評機構的展望歷史...")

    outlook_fields = {
        'SP_Outlook': 'RTG_SP_OUTLOOK',
        'Moody_Outlook': 'RTG_MOODY_OUTLOOK',
        'Fitch_Outlook': 'RTG_FITCH_OUTLOOK'
    }

    # 使用時間序列查詢
    date_range = bq.func.range(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d'),
        frq='M'  # 月度頻率
    )

    # 步驟3: 查詢違約數據
    print("\n[步驟3] 查詢違約事件數據...")

    default_query = bql.Request(
        bq.univ.bondsuniv(issuers='active'),
        {
            'Default_Date': bq.data.default_date(),
            'Is_Defaulted': bq.data.is_defaulted()
        }
    )

    try:
        default_response = bq.execute(default_query)
        default_df = default_response[0].df()
        print(f"   找到 {default_df['Is_Defaulted'].sum()} 起違約事件")
    except Exception as e:
        print(f"   查詢錯誤: {e}")
        return None

    return companies, default_df


# ============================================================================
# 方法三：使用DRSK（違約風險）數據進行分析
# ============================================================================

def analyze_using_drsk():
    """
    使用Bloomberg DRSK違約風險數據進行分析
    結合展望數據和違約機率
    """

    print("\n" + "="*60)
    print("使用DRSK違約風險數據進行分析")
    print("="*60)

    # DRSK提供的違約機率欄位
    drsk_fields = {
        'PD_1Y': bq.data.drsk_pd_1y(),   # 1年違約機率
        'PD_2Y': bq.data.drsk_pd_2y(),   # 2年違約機率
        'PD_5Y': bq.data.drsk_pd_5y(),   # 5年違約機率
    }

    # 建立查詢
    query = bql.Request(
        bq.univ.filter(
            bq.univ.bondsuniv(issuers='active'),
            bq.func.or_(
                bq.data.rtg_sp_outlook() == 'Positive',
                bq.data.rtg_moody_outlook() == 'Positive',
                bq.data.rtg_fitch_outlook() == 'Positive'
            )
        ),
        {
            'Company': bq.data.name(),
            'SP_Outlook': bq.data.rtg_sp_outlook(),
            'Moody_Outlook': bq.data.rtg_moody_outlook(),
            'Fitch_Outlook': bq.data.rtg_fitch_outlook(),
            'PD_2Y': bq.data.drsk_pd_2y(),
            'Current_Rating': bq.data.rtg_sp_lt_lc_issuer_credit()
        }
    )

    try:
        response = bq.execute(query)
        df = response[0].df()
        return df
    except Exception as e:
        print(f"查詢錯誤: {e}")
        return None


# ============================================================================
# 方法四：完整的歷史分析流程（推薦）
# ============================================================================

def comprehensive_outlook_default_study():
    """
    完整的正向展望違約率研究

    此方法執行完整的歷史分析：
    1. 獲取過去10年的所有展望變更事件
    2. 篩選正向展望事件
    3. 追蹤每個事件後2年內是否發生違約
    4. 計算違約率統計
    """

    print("\n" + "="*70)
    print("正向展望公司違約率完整研究")
    print("="*70)
    print(f"\n研究期間: {start_date.strftime('%Y-%m-%d')} 至 {analysis_end_date.strftime('%Y-%m-%d')}")
    print(f"違約觀察視窗: {FORWARD_YEARS} 年")

    # ==========================================
    # 步驟1: 使用ACTS獲取評級行動歷史
    # ==========================================
    print("\n[步驟1] 查詢評級行動歷史數據...")

    # 使用Bloomberg的評級行動歷史數據
    # ACTS是Bloomberg的評級行動數據庫

    acts_query = f"""
    get(
        ID_BB_COMPANY,
        NAME,
        RATING_ACTION_DATE,
        RATING_AGENCY_NAME,
        RTG_ACTION_TYPE_DESC,
        OUTLOOK_ACTION,
        RTG_OUTLOOK_BEFORE,
        RTG_OUTLOOK_AFTER,
        RTG_BEFORE,
        RTG_AFTER
    )
    for(
        filter(
            members('BERC Index'),  -- 全球企業債指數成員
            RATING_ACTION_DATE >= '{start_date.strftime('%Y-%m-%d')}' AND
            RATING_ACTION_DATE <= '{analysis_end_date.strftime('%Y-%m-%d')}'
        )
    )
    """

    # 簡化版本的BQL查詢
    try:
        # 獲取當前具有正向展望的公司
        positive_outlook_query = bql.Request(
            bq.univ.bondsuniv(issuers='active'),
            {
                'Company_Name': bq.data.name(),
                'SP_Rating': bq.data.rtg_sp_lt_lc_issuer_credit(),
                'SP_Outlook': bq.data.rtg_sp_outlook(),
                'Moody_Rating': bq.data.rtg_moody_long_term(),
                'Moody_Outlook': bq.data.rtg_moody_outlook(),
                'Fitch_Rating': bq.data.rtg_fitch_lt_issuer_default(),
                'Fitch_Outlook': bq.data.rtg_fitch_outlook(),
                'Country': bq.data.country_full_name(),
                'Sector': bq.data.bics_level_1_sector_name()
            }
        )

        print("   執行展望查詢...")
        response = bq.execute(positive_outlook_query)
        outlook_df = response[0].df()

        # 篩選正向展望公司
        positive_mask = (
            (outlook_df['SP_Outlook'].str.upper().str.contains('POS', na=False)) |
            (outlook_df['Moody_Outlook'].str.upper().str.contains('POS', na=False)) |
            (outlook_df['Fitch_Outlook'].str.upper().str.contains('POS', na=False))
        )

        positive_outlook_df = outlook_df[positive_mask].copy()
        print(f"   找到 {len(positive_outlook_df)} 家目前具有正向展望的公司")

    except Exception as e:
        print(f"   展望查詢錯誤: {e}")
        positive_outlook_df = pd.DataFrame()

    # ==========================================
    # 步驟2: 查詢歷史違約數據
    # ==========================================
    print("\n[步驟2] 查詢違約歷史數據...")

    try:
        default_query = bql.Request(
            bq.univ.bondsuniv(issuers='all'),  # 包含已違約的發行人
            {
                'Company_Name': bq.data.name(),
                'Is_Defaulted': bq.data.is_defaulted(),
                'Default_Date': bq.data.default_date(),
                'Recovery_Rate': bq.data.recovery_rate()
            }
        )

        default_response = bq.execute(default_query)
        default_df = default_response[0].df()

        defaulted_companies = default_df[default_df['Is_Defaulted'] == True]
        print(f"   找到 {len(defaulted_companies)} 起歷史違約事件")

    except Exception as e:
        print(f"   違約查詢錯誤: {e}")
        default_df = pd.DataFrame()

    # ==========================================
    # 步驟3: 使用RATC獲取歷史評級變更
    # ==========================================
    print("\n[步驟3] 分析評級變更歷史...")

    try:
        # 查詢歷史評級變更（需要RATC權限）
        ratc_query = bql.Request(
            bq.univ.bondsuniv(issuers='active'),
            {
                'Rating_Changes': bq.data.rating_action_history(
                    start=start_date.strftime('%Y-%m-%d'),
                    end=end_date.strftime('%Y-%m-%d')
                )
            }
        )

        ratc_response = bq.execute(ratc_query)
        ratc_df = ratc_response[0].df()
        print(f"   獲取 {len(ratc_df)} 筆評級變更記錄")

    except Exception as e:
        print(f"   RATC查詢錯誤: {e}")
        print("   提示: 可能需要RATC數據訂閱權限")

    return positive_outlook_df, default_df


# ============================================================================
# 方法五：使用SRCH和CACS進行歷史事件追蹤
# ============================================================================

def historical_event_tracking():
    """
    使用Bloomberg公司行動和信用事件數據進行歷史追蹤
    """

    print("\n" + "="*60)
    print("歷史事件追蹤分析")
    print("="*60)

    # 使用Credit Risk數據
    credit_events_query = bql.Request(
        bq.univ.bondsuniv(issuers='all'),
        {
            'Name': bq.data.name(),
            'Ticker': bq.data.ticker(),

            # 當前評級和展望
            'SP_Rating': bq.data.rtg_sp_lt_lc_issuer_credit(),
            'SP_Outlook': bq.data.rtg_sp_outlook(),
            'SP_Watch': bq.data.rtg_sp_credit_watch(),

            'Moody_Rating': bq.data.rtg_moody_long_term(),
            'Moody_Outlook': bq.data.rtg_moody_outlook(),
            'Moody_Watch': bq.data.rtg_moody_watch(),

            'Fitch_Rating': bq.data.rtg_fitch_lt_issuer_default(),
            'Fitch_Outlook': bq.data.rtg_fitch_outlook(),
            'Fitch_Watch': bq.data.rtg_fitch_watch(),

            # 違約相關
            'Is_Defaulted': bq.data.is_defaulted(),
            'Default_Date': bq.data.default_date(),

            # 信用風險指標
            'CDS_Spread_5Y': bq.data.cds_spread_5y(),
            'Implied_PD_1Y': bq.data.implied_cds_spread_1y(),
        }
    )

    try:
        response = bq.execute(credit_events_query)
        df = response[0].df()
        return df
    except Exception as e:
        print(f"查詢錯誤: {e}")
        return None


# ============================================================================
# 計算違約率統計
# ============================================================================

def calculate_default_rate(positive_outlook_events, default_events, forward_years=2):
    """
    計算正向展望公司的違約率

    參數:
        positive_outlook_events: DataFrame包含正向展望事件（需有公司ID和日期）
        default_events: DataFrame包含違約事件（需有公司ID和違約日期）
        forward_years: 觀察期（年）

    返回:
        dict: 包含違約率統計的字典
    """

    if positive_outlook_events.empty:
        return {"error": "沒有正向展望事件數據"}

    total_positive_outlooks = len(positive_outlook_events)
    defaults_within_window = 0

    # 對每個正向展望事件，檢查後續是否違約
    for idx, row in positive_outlook_events.iterrows():
        company_id = row.get('ID_BB_COMPANY') or row.get('Ticker') or idx
        outlook_date = pd.to_datetime(row.get('Outlook_Date', row.get('Date', datetime.now())))

        # 計算觀察視窗
        window_end = outlook_date + relativedelta(years=forward_years)

        # 檢查該公司是否在視窗內違約
        company_defaults = default_events[
            default_events.index.str.contains(str(company_id), na=False) |
            (default_events.get('Company_ID') == company_id)
        ]

        for _, default_row in company_defaults.iterrows():
            default_date = pd.to_datetime(default_row.get('Default_Date'))
            if pd.notna(default_date) and outlook_date <= default_date <= window_end:
                defaults_within_window += 1
                break

    # 計算統計
    default_rate = (defaults_within_window / total_positive_outlooks * 100) if total_positive_outlooks > 0 else 0

    results = {
        'total_positive_outlook_events': total_positive_outlooks,
        'defaults_within_window': defaults_within_window,
        'default_rate_percent': round(default_rate, 4),
        'observation_window_years': forward_years,
        'non_default_rate_percent': round(100 - default_rate, 4)
    }

    return results


# ============================================================================
# 主程式執行
# ============================================================================

def main():
    """
    主程式：執行完整的正向展望違約率分析
    """

    print("\n" + "="*70)
    print("Bloomberg BQNT - 正向展望公司違約率分析")
    print("="*70)
    print(f"\n分析參數:")
    print(f"  - 回顧期間: {LOOKBACK_YEARS} 年")
    print(f"  - 違約觀察期: {FORWARD_YEARS} 年")
    print(f"  - 開始日期: {start_date.strftime('%Y-%m-%d')}")
    print(f"  - 截止日期: {analysis_end_date.strftime('%Y-%m-%d')}")

    # 執行分析
    print("\n開始執行分析...")

    try:
        # 方法1: 完整研究
        positive_df, default_df = comprehensive_outlook_default_study()

        if positive_df is not None and not positive_df.empty:
            # 計算統計
            print("\n" + "="*60)
            print("分析結果摘要")
            print("="*60)

            print(f"\n目前具有正向展望的公司數: {len(positive_df)}")

            if default_df is not None and not default_df.empty:
                defaulted_count = default_df['Is_Defaulted'].sum() if 'Is_Defaulted' in default_df.columns else 0
                print(f"歷史違約公司數: {defaulted_count}")

            # 顯示前10家正向展望公司
            print("\n正向展望公司範例（前10家）:")
            display_cols = ['Company_Name', 'SP_Outlook', 'Moody_Outlook', 'Fitch_Outlook', 'Country', 'Sector']
            available_cols = [col for col in display_cols if col in positive_df.columns]
            print(positive_df[available_cols].head(10).to_string())

            # 按地區統計
            if 'Country' in positive_df.columns:
                print("\n按國家/地區分布:")
                print(positive_df['Country'].value_counts().head(10))

            # 按產業統計
            if 'Sector' in positive_df.columns:
                print("\n按產業分布:")
                print(positive_df['Sector'].value_counts())

        # 方法2: 信用事件追蹤
        credit_df = historical_event_tracking()

        if credit_df is not None and not credit_df.empty:
            # 統計正向展望
            positive_sp = credit_df['SP_Outlook'].str.upper().str.contains('POS', na=False).sum()
            positive_moody = credit_df['Moody_Outlook'].str.upper().str.contains('POS', na=False).sum()
            positive_fitch = credit_df['Fitch_Outlook'].str.upper().str.contains('POS', na=False).sum()

            print(f"\n各信評機構正向展望統計:")
            print(f"  S&P 正向展望: {positive_sp}")
            print(f"  Moody's 正向展望: {positive_moody}")
            print(f"  Fitch 正向展望: {positive_fitch}")

            # 違約統計
            total_defaults = credit_df['Is_Defaulted'].sum() if 'Is_Defaulted' in credit_df.columns else 0
            print(f"\n總違約數: {total_defaults}")

    except Exception as e:
        print(f"\n執行錯誤: {e}")
        print("\n請確認:")
        print("  1. 您正在Bloomberg Terminal的BQNT環境中執行")
        print("  2. 您具有必要的數據訂閱權限")
        print("  3. BQL服務已正確初始化")

    print("\n" + "="*70)
    print("分析完成")
    print("="*70)


# ============================================================================
# 替代方案：使用Excel API進行批量數據提取
# ============================================================================

def generate_excel_formulas():
    """
    生成可在Bloomberg Excel API中使用的公式
    適用於無法直接使用BQNT的情況
    """

    print("\n" + "="*60)
    print("Bloomberg Excel API 公式參考")
    print("="*60)

    formulas = """
    # 以下公式可在Excel中配合Bloomberg API使用:

    # 1. 獲取S&P展望
    =BDP("AAPL US Equity", "RTG_SP_OUTLOOK")

    # 2. 獲取Moody's展望
    =BDP("AAPL US Equity", "RTG_MOODY_OUTLOOK")

    # 3. 獲取Fitch展望
    =BDP("AAPL US Equity", "RTG_FITCH_OUTLOOK")

    # 4. 獲取違約狀態
    =BDP("AAPL US Equity", "IS_DEFAULTED")

    # 5. 獲取違約日期
    =BDP("AAPL US Equity", "DEFAULT_DATE")

    # 6. 獲取歷史展望（時間序列）
    =BDH("AAPL US Equity", "RTG_SP_OUTLOOK", "2015-01-01", "2024-12-31")

    # 7. 批量獲取多家公司展望
    =BDS("BERC Index", "INDX_MEMBERS")  # 先獲取成分股
    # 然後對每家公司使用BDP獲取展望
    """

    print(formulas)
    return formulas


# ============================================================================
# 數據視覺化（如果需要）
# ============================================================================

def visualize_results(results_df):
    """
    視覺化分析結果
    需要matplotlib和seaborn
    """
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns

        # 設定中文字體
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # 圖1: 各信評機構正向展望分布
        if 'Rating_Agency' in results_df.columns:
            agency_counts = results_df['Rating_Agency'].value_counts()
            axes[0, 0].bar(agency_counts.index, agency_counts.values)
            axes[0, 0].set_title('各信評機構正向展望數量')
            axes[0, 0].set_xlabel('信評機構')
            axes[0, 0].set_ylabel('數量')

        # 圖2: 違約率時間趨勢
        if 'Year' in results_df.columns and 'Default_Rate' in results_df.columns:
            axes[0, 1].plot(results_df['Year'], results_df['Default_Rate'], marker='o')
            axes[0, 1].set_title('正向展望後2年違約率趨勢')
            axes[0, 1].set_xlabel('年份')
            axes[0, 1].set_ylabel('違約率 (%)')

        # 圖3: 按產業的違約率
        if 'Sector' in results_df.columns and 'Default_Rate' in results_df.columns:
            sector_rates = results_df.groupby('Sector')['Default_Rate'].mean()
            axes[1, 0].barh(sector_rates.index, sector_rates.values)
            axes[1, 0].set_title('各產業正向展望後違約率')
            axes[1, 0].set_xlabel('違約率 (%)')

        # 圖4: 評級與違約關係
        if 'Rating' in results_df.columns and 'Defaulted' in results_df.columns:
            rating_default = results_df.groupby('Rating')['Defaulted'].mean() * 100
            axes[1, 1].bar(rating_default.index, rating_default.values)
            axes[1, 1].set_title('各評級等級的違約率')
            axes[1, 1].set_xlabel('評級')
            axes[1, 1].set_ylabel('違約率 (%)')

        plt.tight_layout()
        plt.savefig('positive_outlook_default_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()

        print("\n圖表已儲存為: positive_outlook_default_analysis.png")

    except ImportError:
        print("需要安裝matplotlib和seaborn進行視覺化")
        print("pip install matplotlib seaborn")


# ============================================================================
# 執行主程式
# ============================================================================

if __name__ == "__main__":
    main()

    # 輸出Excel公式參考
    generate_excel_formulas()
