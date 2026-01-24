"""
Bloomberg BQNT - 正向展望公司違約率分析
=======================================
純BQL方案 - 修復版

發現可用欄位：
- RTG_SP_LT_LC_ISSUER_CREDIT: 有效（IBM = A-）
- RATING_OUTLOOK: 有效（返回日期）
- RTG_SP_WATCH, RTG_MOODY_WATCH, RTG_FITCH_WATCH: 有效
"""

import bql
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta

# 初始化BQL服務
bq = bql.Service()

# ============================================================================
# 參數設定
# ============================================================================
LOOKBACK_YEARS = 10
FORWARD_YEARS = 2

end_date = datetime.now()
start_date = end_date - relativedelta(years=LOOKBACK_YEARS + FORWARD_YEARS)
analysis_end_date = end_date - relativedelta(years=FORWARD_YEARS)

print(f"分析期間: {start_date.strftime('%Y-%m-%d')} 至 {analysis_end_date.strftime('%Y-%m-%d')}")
print(f"違約觀察期: 每個事件後的 {FORWARD_YEARS} 年")


# S&P 評級等級映射
SP_RATING_SCALE = {
    'AAA': 22, 'AA+': 21, 'AA': 20, 'AA-': 19,
    'A+': 18, 'A': 17, 'A-': 16,
    'BBB+': 15, 'BBB': 14, 'BBB-': 13,
    'BB+': 12, 'BB': 11, 'BB-': 10,
    'B+': 9, 'B': 8, 'B-': 7,
    'CCC+': 6, 'CCC': 5, 'CCC-': 4,
    'CC': 3, 'C': 2, 'D': 1,
    'NR': 0, None: 0, 'nan': 0
}


def rating_to_numeric(rating):
    """將評級轉換為數字"""
    if pd.isna(rating) or rating is None:
        return 0
    rating_str = str(rating).strip().upper()
    return SP_RATING_SCALE.get(rating_str, 0)


# ============================================================================
# 步驟1：深入探索展望相關欄位
# ============================================================================

def explore_outlook_fields_detailed():
    """
    深入探索展望相關欄位的所有可能名稱
    """
    print("\n" + "="*70)
    print("步驟1：深入探索展望相關BQL欄位")
    print("="*70)

    test_security = 'IBM US Equity'

    # 更完整的展望欄位列表
    outlook_fields = [
        # 標準展望欄位
        'RTG_SP_OUTLOOK',
        'RTG_MOODY_OUTLOOK',
        'RTG_FITCH_OUTLOOK',

        # 展望方向
        'RTG_SP_OUTLOOK_ACTION',
        'RTG_MOODY_OUTLOOK_ACTION',
        'RATING_OUTLOOK',
        'RATING_OUTLOOK_SP',
        'RATING_OUTLOOK_MOODY',
        'RATING_OUTLOOK_FITCH',

        # 長期展望
        'RTG_SP_LT_OUTLOOK',
        'RTG_MOODY_LT_OUTLOOK',
        'SP_LT_OUTLOOK',

        # 短期展望
        'RTG_SP_ST_OUTLOOK',
        'SP_OUTLOOK_ST',

        # 其他可能的名稱
        'OUTLOOK',
        'CREDIT_OUTLOOK',
        'ISSUER_OUTLOOK',
        'ISSUER_RATING_OUTLOOK',
        'LT_ISSUER_OUTLOOK',

        # 評級趨勢（可能與展望相關）
        'RTG_TREND',
        'RTG_SP_TREND',
        'RTG_MOODY_TREND',
        'RATING_TREND',
        'CREDIT_TREND',

        # 評級方向
        'RTG_DIRECTION',
        'RTG_SP_DIRECTION',
        'RATING_DIRECTION',

        # 評級行動日期（可能包含展望變更）
        'RTG_SP_OUTLOOK_DT',
        'RTG_MOODY_OUTLOOK_DT',
        'OUTLOOK_DATE',
        'RATING_OUTLOOK_DATE',
        'RTG_OUTLOOK_DATE',

        # 信用觀察（可能有正向觀察）
        'RTG_SP_WATCH',
        'RTG_MOODY_WATCH',
        'RTG_FITCH_WATCH',
        'CREDIT_WATCH',
        'WATCH_LIST',
        'ON_WATCH',

        # 評級穩定性
        'RATING_STABILITY',
        'CREDIT_STABILITY',
    ]

    available = {}
    print(f"\n測試證券: {test_security}")
    print("-" * 60)

    for field in outlook_fields:
        try:
            query = f'get({field}) for(["{test_security}"])'
            response = bq.execute(query)
            df = response[0].df()
            if not df.empty:
                value = df.iloc[0, 0]
                value_str = str(value) if value is not None else "(空)"
                print(f"  ✓ {field}: {value_str[:50]}")
                available[field] = value
        except:
            pass

    print(f"\n找到 {len(available)} 個展望相關可用欄位")
    return available


# ============================================================================
# 步驟2：使用正確的語法獲取評級數據
# ============================================================================

def get_ratings_with_correct_syntax():
    """
    使用正確的BQL語法獲取評級數據
    """
    print("\n" + "="*70)
    print("步驟2：獲取評級數據（修正語法）")
    print("="*70)

    # 方法1：使用 bq.data 對象
    try:
        print("\n嘗試方法1: 使用 bq.data 對象...")

        universe = bq.univ.members('SPX Index')

        request = bql.Request(
            universe,
            {
                'Name': bq.data.name(),
                'Rating': bq.data.rtg_sp_lt_lc_issuer_credit(),
                'Sector': bq.data.gics_sector_name(),
            }
        )

        response = bq.execute(request)

        all_dfs = []
        for item in response:
            df = item.df()
            if not df.empty:
                all_dfs.append(df)
                print(f"  {item.name}: {len(df)} 筆, 非空值: {df.iloc[:,0].notna().sum()}")

        if all_dfs:
            result = pd.concat(all_dfs, axis=1)
            result = result.loc[:, ~result.columns.duplicated()]

            # 檢查評級欄位
            if 'Rating' in result.columns:
                non_null = result['Rating'].notna().sum()
                print(f"\n評級數據: {non_null}/{len(result)} 筆有效")

                if non_null > 0:
                    print("\n評級分布:")
                    print(result['Rating'].value_counts().head(15))
                    return result

    except Exception as e:
        print(f"  方法1錯誤: {e}")

    # 方法2：直接使用BQL字串，每次查詢一個欄位
    try:
        print("\n嘗試方法2: 分開查詢各欄位...")

        # 先獲取公司名稱
        name_query = "get(NAME) for(members('SPX Index'))"
        name_response = bq.execute(name_query)
        name_df = name_response[0].df()
        print(f"  公司數: {len(name_df)}")

        # 獲取評級
        rating_query = "get(RTG_SP_LT_LC_ISSUER_CREDIT) for(members('SPX Index'))"
        rating_response = bq.execute(rating_query)
        rating_df = rating_response[0].df()
        non_null = rating_df.iloc[:, 0].notna().sum()
        print(f"  評級數據: {non_null}/{len(rating_df)} 筆有效")

        if non_null > 0:
            # 合併
            result = pd.concat([name_df, rating_df], axis=1)
            result.columns = ['Name', 'Rating']
            print("\n評級分布:")
            print(result['Rating'].value_counts().head(15))
            return result

    except Exception as e:
        print(f"  方法2錯誤: {e}")

    # 方法3：查詢債券發行人評級
    try:
        print("\n嘗試方法3: 查詢債券發行人...")

        # 使用企業債指數
        query = """
        get(NAME, ISSUER_BULK, RTG_SP_LT_LC_ISSUER_CREDIT)
        for(members('LUACTRUU Index'))
        """
        response = bq.execute(query)

        dfs = []
        for item in response:
            df = item.df()
            if not df.empty:
                dfs.append(df)

        if dfs:
            result = pd.concat(dfs, axis=1)
            result = result.loc[:, ~result.columns.duplicated()]
            print(f"  獲取 {len(result)} 筆債券發行人數據")
            return result

    except Exception as e:
        print(f"  方法3錯誤: {e}")

    return None


# ============================================================================
# 步驟3：查詢少量公司的詳細數據
# ============================================================================

def get_sample_company_ratings():
    """
    對樣本公司進行詳細查詢
    """
    print("\n" + "="*70)
    print("步驟3：樣本公司詳細評級數據")
    print("="*70)

    # 選擇30家代表性公司
    sample_tickers = [
        'AAPL US Equity', 'MSFT US Equity', 'GOOGL US Equity', 'AMZN US Equity',
        'META US Equity', 'NVDA US Equity', 'JPM US Equity', 'V US Equity',
        'JNJ US Equity', 'WMT US Equity', 'PG US Equity', 'MA US Equity',
        'UNH US Equity', 'HD US Equity', 'BAC US Equity', 'XOM US Equity',
        'PFE US Equity', 'KO US Equity', 'CSCO US Equity', 'CVX US Equity',
        'IBM US Equity', 'T US Equity', 'VZ US Equity', 'INTC US Equity',
        'MRK US Equity', 'ABBV US Equity', 'CMCSA US Equity', 'ORCL US Equity',
        'C US Equity', 'GS US Equity'
    ]

    results = []

    for ticker in sample_tickers:
        try:
            query = f"""
            get(
                NAME,
                RTG_SP_LT_LC_ISSUER_CREDIT,
                RTG_SP_WATCH,
                RTG_MOODY_WATCH,
                GICS_SECTOR_NAME
            )
            for(["{ticker}"])
            """

            response = bq.execute(query)

            row = {'Ticker': ticker}
            for item in response:
                df = item.df()
                if not df.empty:
                    col_name = item.name
                    value = df.iloc[0, 0]
                    row[col_name] = value

            results.append(row)

        except Exception as e:
            results.append({'Ticker': ticker, 'Error': str(e)[:30]})

    df = pd.DataFrame(results)
    df = df.set_index('Ticker')

    print(f"\n成功獲取 {len(df)} 家公司的詳細數據:")
    print(df.to_string())

    # 統計評級分布
    if 'RTG_SP_LT_LC_ISSUER_CREDIT' in df.columns:
        print("\n\nS&P 評級分布:")
        rating_dist = df['RTG_SP_LT_LC_ISSUER_CREDIT'].value_counts()
        print(rating_dist)

        # 計算評級等級
        df['Rating_Numeric'] = df['RTG_SP_LT_LC_ISSUER_CREDIT'].apply(rating_to_numeric)

        # 分類
        def categorize(n):
            if n >= 13:
                return 'Investment Grade'
            elif n >= 1:
                return 'High Yield'
            else:
                return 'Not Rated'

        df['Category'] = df['Rating_Numeric'].apply(categorize)

        print("\n評級類別:")
        print(df['Category'].value_counts())

    # 統計觀察狀態
    if 'RTG_SP_WATCH' in df.columns:
        print("\nS&P 信用觀察狀態:")
        print(df['RTG_SP_WATCH'].value_counts())

    return df


# ============================================================================
# 步驟4：獲取歷史評級時間序列
# ============================================================================

def get_historical_ratings_timeseries():
    """
    獲取歷史評級時間序列
    """
    print("\n" + "="*70)
    print("步驟4：獲取歷史評級時間序列")
    print("="*70)

    # 選擇幾家公司進行歷史分析
    sample_tickers = ['IBM US Equity', 'AAPL US Equity', 'JPM US Equity', 'XOM US Equity', 'T US Equity']

    for ticker in sample_tickers:
        print(f"\n{ticker}:")
        print("-" * 40)

        try:
            # 使用日期範圍
            query = f"""
            get(RTG_SP_LT_LC_ISSUER_CREDIT)
            for(["{ticker}"])
            with(dates=range({start_date.strftime('%Y-%m-%d')},{end_date.strftime('%Y-%m-%d')},frq=Y),fill=prev)
            """

            response = bq.execute(query)
            df = response[0].df()

            if not df.empty:
                print(df.to_string())

                # 檢測評級變化
                ratings = df.iloc[:, 0].dropna()
                if len(ratings) > 1:
                    changes = []
                    prev_rating = None
                    for idx, rating in ratings.items():
                        if prev_rating is not None and rating != prev_rating:
                            prev_num = rating_to_numeric(prev_rating)
                            curr_num = rating_to_numeric(rating)
                            if curr_num > prev_num:
                                changes.append(f"升級: {prev_rating} → {rating}")
                            else:
                                changes.append(f"降級: {prev_rating} → {rating}")
                        prev_rating = rating

                    if changes:
                        print(f"\n評級變化: {changes}")
                    else:
                        print("\n評級無變化")

        except Exception as e:
            print(f"  錯誤: {e}")


# ============================================================================
# 步驟5：分析信用觀察狀態（作為展望的替代指標）
# ============================================================================

def analyze_credit_watch():
    """
    分析信用觀察狀態
    正向觀察（Positive Watch）可以作為正向展望的替代指標
    """
    print("\n" + "="*70)
    print("步驟5：分析信用觀察狀態")
    print("="*70)

    try:
        # 查詢所有SPX成員的信用觀察狀態
        queries = [
            ("S&P Watch", "RTG_SP_WATCH"),
            ("Moody's Watch", "RTG_MOODY_WATCH"),
            ("Fitch Watch", "RTG_FITCH_WATCH"),
        ]

        for name, field in queries:
            try:
                query = f"get({field}) for(members('SPX Index'))"
                response = bq.execute(query)
                df = response[0].df()

                if not df.empty:
                    non_null = df.iloc[:, 0].notna().sum()
                    print(f"\n{name}:")
                    print(f"  有效數據: {non_null}/{len(df)}")

                    if non_null > 0:
                        dist = df.iloc[:, 0].value_counts()
                        print(f"  分布:")
                        for val, count in dist.items():
                            print(f"    {val}: {count}")

                        # 檢查是否有正向觀察
                        positive_watch = df.iloc[:, 0].astype(str).str.upper().str.contains('POS|UP', na=False).sum()
                        if positive_watch > 0:
                            print(f"  正向觀察: {positive_watch} 家")

            except Exception as e:
                print(f"\n{name}: 查詢錯誤 - {e}")

    except Exception as e:
        print(f"信用觀察分析錯誤: {e}")


# ============================================================================
# 步驟6：研究總結
# ============================================================================

def generate_summary(sample_df, outlook_fields):
    """
    生成研究總結
    """
    print("\n" + "="*70)
    print("研究總結")
    print("="*70)

    print("\n【可用的BQL欄位】")
    print("-" * 40)
    if outlook_fields:
        for field, value in outlook_fields.items():
            print(f"  {field}: {value}")

    print("\n【樣本分析結果】")
    print("-" * 40)
    if sample_df is not None and not sample_df.empty:
        if 'Category' in sample_df.columns:
            cat_dist = sample_df['Category'].value_counts()
            total = len(sample_df)
            for cat, count in cat_dist.items():
                print(f"  {cat}: {count} 家 ({count/total*100:.1f}%)")

    print("\n【研究結論】")
    print("-" * 40)
    print("""
    1. BQL環境限制：
       - 展望欄位（RTG_SP_OUTLOOK等）不可直接查詢
       - 但 RATING_OUTLOOK 欄位存在，返回日期類型
       - 信用觀察狀態欄位（RTG_SP_WATCH等）可用

    2. 替代分析方法：
       - 使用評級升級事件作為正向展望的proxy
       - 使用信用觀察狀態（Positive Watch）作為指標
       - 追蹤歷史評級變化識別升級模式

    3. 歷史參考數據（S&P/Moody's研究報告）：
       - 正向展望公司2年內違約率: < 1%
       - 正向展望後2年升級機率: 約30-40%
       - 投資級公司2年違約率: < 0.5%
       - 高收益級公司2年違約率: 約4-5%

    4. 建議後續步驟：
       - 在Terminal中使用RATC獲取完整展望歷史
       - 聯繫Bloomberg確認展望欄位的BQL訪問方式
       - 考慮使用債券宇宙獲取更完整的評級數據
    """)


# ============================================================================
# 主程式
# ============================================================================

def main():
    """
    主程式
    """
    print("\n" + "="*70)
    print("Bloomberg BQNT - 正向展望公司違約率分析（修正版）")
    print("="*70)

    # 步驟1: 探索展望欄位
    outlook_fields = explore_outlook_fields_detailed()

    # 步驟2: 獲取評級數據
    ratings_df = get_ratings_with_correct_syntax()

    # 步驟3: 樣本公司詳細數據
    sample_df = get_sample_company_ratings()

    # 步驟4: 歷史評級時間序列
    get_historical_ratings_timeseries()

    # 步驟5: 信用觀察分析
    analyze_credit_watch()

    # 步驟6: 研究總結
    generate_summary(sample_df, outlook_fields)

    print("\n" + "="*70)
    print("分析完成")
    print("="*70)

    return {
        'outlook_fields': outlook_fields,
        'ratings': ratings_df,
        'sample_ratings': sample_df
    }


# ============================================================================
# 執行
# ============================================================================

if __name__ == "__main__":
    results = main()
