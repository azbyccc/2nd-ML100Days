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
# 方法一：使用 fld() 函數調用原始Bloomberg欄位
# ============================================================================

def query_with_fld():
    """
    使用 bq.data.fld() 調用原始Bloomberg欄位名稱
    """
    print("\n" + "="*60)
    print("使用 fld() 函數查詢展望數據")
    print("="*60)

    try:
        universe = bq.univ.members('SPX Index')

        # 使用 fld() 函數指定原始Bloomberg欄位
        request = bql.Request(
            universe,
            {
                'Name': bq.data.name(),
                'Ticker': bq.data.ticker(),
                'SP_Rating': bq.data.fld('RTG_SP_LT_LC_ISSUER_CREDIT'),
                'SP_Outlook': bq.data.fld('RTG_SP_OUTLOOK'),
                'Moody_Rating': bq.data.fld('RTG_MOODY_LONG_TERM'),
                'Moody_Outlook': bq.data.fld('RTG_MOODY_OUTLOOK'),
                'Fitch_Rating': bq.data.fld('RTG_FITCH_LT_ISSUER_DEFAULT'),
                'Fitch_Outlook': bq.data.fld('RTG_FITCH_OUTLOOK'),
                'Sector': bq.data.gics_sector_name(),
            }
        )

        response = bq.execute(request)
        df = response[0].df()

        print(f"成功獲取 {len(df)} 筆資料")
        return df

    except Exception as e:
        print(f"fld() 方法錯誤: {e}")
        return None


# ============================================================================
# 方法二：使用 ID() 函數
# ============================================================================

def query_with_id():
    """
    使用 bq.data.id() 獲取欄位
    """
    print("\n" + "="*60)
    print("使用 ID 函數查詢")
    print("="*60)

    try:
        universe = bq.univ.members('SPX Index')

        request = bql.Request(
            universe,
            {
                'Name': bq.data.name(),
                'SP_Outlook': bq.data.id('RTG_SP_OUTLOOK'),
                'Moody_Outlook': bq.data.id('RTG_MOODY_OUTLOOK'),
                'Fitch_Outlook': bq.data.id('RTG_FITCH_OUTLOOK'),
            }
        )

        response = bq.execute(request)
        df = response[0].df()

        print(f"成功獲取 {len(df)} 筆資料")
        return df

    except Exception as e:
        print(f"ID 方法錯誤: {e}")
        return None


# ============================================================================
# 方法三：使用原生BQL語法字串
# ============================================================================

def query_with_bql_string():
    """
    使用原生BQL查詢字串
    """
    print("\n" + "="*60)
    print("使用BQL字串查詢")
    print("="*60)

    # BQL查詢字串
    bql_query = """
    get(
        NAME,
        ID_BB_SEC_NUM_DES,
        RTG_SP_LT_LC_ISSUER_CREDIT,
        RTG_SP_OUTLOOK,
        RTG_MOODY_LONG_TERM,
        RTG_MOODY_OUTLOOK,
        RTG_FITCH_LT_ISSUER_DEFAULT,
        RTG_FITCH_OUTLOOK,
        GICS_SECTOR_NAME
    )
    for(
        members('SPX Index')
    )
    """

    try:
        response = bq.execute(bql_query)
        df = response[0].df()
        print(f"成功獲取 {len(df)} 筆資料")
        return df

    except Exception as e:
        print(f"BQL字串查詢錯誤: {e}")
        return None


# ============================================================================
# 方法四：使用 get() 語法
# ============================================================================

def query_with_get_syntax():
    """
    使用BQL get語法
    """
    print("\n" + "="*60)
    print("使用 get() 語法查詢")
    print("="*60)

    try:
        # 直接使用BQL字串
        query = """
        get(NAME, RTG_SP_OUTLOOK, RTG_MOODY_OUTLOOK, RTG_FITCH_OUTLOOK)
        for(members('SPX Index'))
        """

        response = bq.execute(query)

        # 合併所有結果
        all_data = []
        for item in response:
            df = item.df()
            if not df.empty:
                all_data.append(df)
                print(f"  {item.name}: {len(df)} 筆")

        if all_data:
            result_df = pd.concat(all_data, axis=1)
            return result_df

    except Exception as e:
        print(f"get() 語法錯誤: {e}")
        return None


# ============================================================================
# 方法五：測試可用的欄位名稱
# ============================================================================

def test_available_fields():
    """
    測試各種可能的BQL欄位名稱
    """
    print("\n" + "="*60)
    print("測試可用的BQL欄位名稱")
    print("="*60)

    universe = bq.univ.members('SPX Index')

    # 可能的欄位名稱列表
    test_fields = [
        # 原始欄位名（大寫）
        ('RTG_SP_OUTLOOK', 'bq.data.fld("RTG_SP_OUTLOOK")'),
        ('RTG_SP_LT_LC_ISSUER_CREDIT', 'bq.data.fld("RTG_SP_LT_LC_ISSUER_CREDIT")'),

        # BQL native 名稱（小寫）
        ('sp_outlook', 'bq.data.sp_outlook()'),
        ('credit_rating', 'bq.data.credit_rating()'),
        ('rating_sp', 'bq.data.rating_sp()'),
        ('bb_composite', 'bq.data.bb_composite()'),
    ]

    available_fields = []

    for field_name, field_desc in test_fields:
        try:
            # 嘗試使用fld()
            request = bql.Request(
                ['AAPL US Equity'],  # 單一股票測試
                {'Test': bq.data.fld(field_name)}
            )
            response = bq.execute(request)
            df = response[0].df()
            if not df.empty:
                print(f"  ✓ {field_name} - 可用")
                available_fields.append(field_name)
        except Exception as e:
            print(f"  ✗ {field_name} - {str(e)[:40]}")

    return available_fields


# ============================================================================
# 方法六：使用 CRDT 信用評級數據
# ============================================================================

def query_credit_ratings():
    """
    查詢信用評級相關數據
    使用Bloomberg的CRDT (Credit Ratings) 功能
    """
    print("\n" + "="*60)
    print("查詢信用評級數據")
    print("="*60)

    # 嘗試不同的BQL查詢方式
    queries_to_try = [
        # 方法1: 直接BQL字串
        """
        get(NAME, BB_COMPOSITE, RTG_SP, RTG_MOODY, RTG_FITCH)
        for(members('SPX Index'))
        """,

        # 方法2: 使用不同欄位名
        """
        get(NAME, RATING_SP, RATING_MOODY, RATING_FITCH)
        for(members('SPX Index'))
        """,

        # 方法3: 長期評級
        """
        get(NAME, RTG_SP_LT_LC_ISSUER_CREDIT, RTG_MOODY_LONG_TERM)
        for(members('SPX Index'))
        """,
    ]

    for i, query in enumerate(queries_to_try, 1):
        print(f"\n嘗試查詢方法 {i}...")
        try:
            response = bq.execute(query)
            dfs = []
            for item in response:
                df = item.df()
                if not df.empty:
                    dfs.append(df)

            if dfs:
                result = pd.concat(dfs, axis=1) if len(dfs) > 1 else dfs[0]
                print(f"  ✓ 成功獲取 {len(result)} 筆資料")
                print(f"  欄位: {list(result.columns)}")
                return result

        except Exception as e:
            print(f"  ✗ 錯誤: {str(e)[:60]}")

    return None


# ============================================================================
# 方法七：使用Bloomberg欄位探索
# ============================================================================

def explore_rating_fields():
    """
    探索可用的評級相關欄位
    """
    print("\n" + "="*60)
    print("探索Bloomberg評級相關欄位")
    print("="*60)

    # 測試單一股票的各種評級欄位
    test_security = 'IBM US Equity'

    rating_fields = [
        'BB_COMPOSITE',
        'RTG_SP',
        'RTG_MOODY',
        'RTG_FITCH',
        'RTG_SP_LT_LC_ISSUER_CREDIT',
        'RTG_MOODY_LONG_TERM',
        'RTG_FITCH_LT_ISSUER_DEFAULT',
        'RTG_SP_OUTLOOK',
        'RTG_MOODY_OUTLOOK',
        'RTG_FITCH_OUTLOOK',
        'CREDIT_RATING',
        'COMPOSITE_RATING',
        'BB_COMPOSITE_RATING',
    ]

    print(f"\n測試證券: {test_security}")
    print("-" * 40)

    available = []

    for field in rating_fields:
        try:
            query = f'get({field}) for(["{test_security}"])'
            response = bq.execute(query)
            df = response[0].df()
            value = df.iloc[0, 0] if not df.empty else 'N/A'
            print(f"  ✓ {field}: {value}")
            available.append(field)
        except Exception as e:
            print(f"  ✗ {field}: 不可用")

    return available


# ============================================================================
# 方法八：完整分析（使用正確的語法）
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
    }

    # ============================
    # 步驟1: 探索可用欄位
    # ============================
    print("\n[步驟1] 探索可用的評級欄位...")
    available_fields = explore_rating_fields()

    if not available_fields:
        print("\n無法找到可用的評級欄位")
        return results

    # ============================
    # 步驟2: 構建查詢
    # ============================
    print("\n[步驟2] 構建並執行查詢...")

    # 根據可用欄位構建查詢
    outlook_fields = [f for f in available_fields if 'OUTLOOK' in f]
    rating_fields = [f for f in available_fields if 'OUTLOOK' not in f]

    if outlook_fields:
        fields_str = ', '.join(['NAME'] + outlook_fields[:3])  # 最多3個展望欄位
        query = f"""
        get({fields_str})
        for(members('SPX Index'))
        """

        try:
            print(f"\n執行查詢: {fields_str}")
            response = bq.execute(query)

            dfs = []
            for item in response:
                df = item.df()
                if not df.empty:
                    dfs.append(df)

            if dfs:
                result_df = pd.concat(dfs, axis=1)

                # 識別正向展望
                for col in result_df.columns:
                    if 'OUTLOOK' in str(col).upper():
                        mask = result_df[col].astype(str).str.upper().str.contains('POS', na=False)
                        count = mask.sum()
                        print(f"  {col} 正向展望: {count} 家")
                        results['by_agency'][col] = int(count)

                # 計算總數
                any_positive = pd.Series([False] * len(result_df))
                for col in result_df.columns:
                    if 'OUTLOOK' in str(col).upper():
                        any_positive |= result_df[col].astype(str).str.upper().str.contains('POS', na=False)

                results['positive_outlook_count'] = int(any_positive.sum())
                print(f"\n任一機構正向展望總數: {results['positive_outlook_count']}")

                # 顯示正向展望公司
                positive_df = result_df[any_positive]
                if not positive_df.empty:
                    print("\n正向展望公司範例（前20家）:")
                    print(positive_df.head(20).to_string())

        except Exception as e:
            print(f"查詢錯誤: {e}")

    # ============================
    # 步驟3: 輸出結果
    # ============================
    print("\n" + "="*60)
    print("分析結果摘要")
    print("="*60)

    print(f"\n正向展望公司總數: {results['positive_outlook_count']}")
    print("\n各信評機構正向展望數:")
    for agency, count in results['by_agency'].items():
        print(f"   {agency}: {count}")

    return results


# ============================================================================
# 方法九：使用簡化的BQL語法
# ============================================================================

def simple_outlook_query():
    """
    使用最簡化的BQL語法查詢展望
    """
    print("\n" + "="*60)
    print("簡化BQL查詢")
    print("="*60)

    # 最基本的查詢
    queries = [
        "get(NAME) for(members('SPX Index'))",
        "get(NAME, GICS_SECTOR_NAME) for(members('SPX Index'))",
    ]

    for query in queries:
        print(f"\n執行: {query[:50]}...")
        try:
            response = bq.execute(query)
            for item in response:
                df = item.df()
                if not df.empty:
                    print(f"  ✓ 成功: {len(df)} 筆, 欄位: {list(df.columns)}")
                    return df
        except Exception as e:
            print(f"  ✗ 錯誤: {str(e)[:50]}")

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

    print("\n" + "="*70)
    print("開始測試各種BQL查詢方法...")
    print("="*70)

    # 方法1: 測試基本連接
    print("\n--- 測試1: 基本查詢 ---")
    simple_outlook_query()

    # 方法2: 探索可用欄位
    print("\n--- 測試2: 探索評級欄位 ---")
    explore_rating_fields()

    # 方法3: 使用fld()
    print("\n--- 測試3: 使用fld()函數 ---")
    query_with_fld()

    # 方法4: 使用BQL字串
    print("\n--- 測試4: 使用BQL字串 ---")
    query_with_bql_string()

    # 方法5: 完整分析
    print("\n--- 測試5: 完整分析 ---")
    results = comprehensive_analysis()

    print("\n" + "="*70)
    print("測試完成")
    print("="*70)

    return results


# ============================================================================
# 輔助：列出BQL可用的數據項
# ============================================================================

def list_bql_data_items():
    """
    列出BQL可用的數據項（需要在BQNT環境中執行）
    """
    print("\n" + "="*60)
    print("BQL 數據項探索")
    print("="*60)

    print("""
    在BQNT環境中，您可以使用以下方式探索可用的數據項：

    1. 使用 tab 補全:
       >>> bq.data.<TAB>

    2. 查看 bq.data 的所有屬性:
       >>> dir(bq.data)

    3. 使用 help:
       >>> help(bq.data)

    4. 在Bloomberg Terminal中使用 FLDS 功能:
       - 輸入 FLDS <GO> 搜索欄位
       - 搜索 "outlook" 或 "rating"

    5. 使用 BQL Help:
       - 在Terminal輸入 BQL <GO>
       - 查看可用的數據項文檔
    """)


# ============================================================================
# Excel API 參考
# ============================================================================

def print_excel_formulas():
    """
    輸出Bloomberg Excel API參考公式
    """
    print("\n" + "="*60)
    print("Bloomberg Excel API 公式參考")
    print("="*60)

    print("""
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

# 在BQNT中使用 fld() 調用這些欄位:
bq.data.fld('RTG_SP_OUTLOOK')
bq.data.fld('RTG_MOODY_OUTLOOK')
    """)


# ============================================================================
# 執行
# ============================================================================

if __name__ == "__main__":
    results = main()
    list_bql_data_items()
    print_excel_formulas()
