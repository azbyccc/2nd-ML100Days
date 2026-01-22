"""
Bloomberg BQNT - 正向展望公司違約率分析
=======================================
研究目的：分析過去10年被任一信評公司給予正向展望的公司，未來2年出現違約的比率

注意：
- BQL不支持展望欄位（RTG_SP_OUTLOOK等）
- 本腳本提供多種替代方案：
  1. 使用 xbbg 庫（推薦）
  2. 使用 blpapi 直接調用
  3. 使用評級變化作為替代指標
"""

import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta

# ============================================================================
# 參數設定
# ============================================================================
LOOKBACK_YEARS = 10
FORWARD_YEARS = 2

end_date = datetime.now()
start_date = end_date - relativedelta(years=LOOKBACK_YEARS + FORWARD_YEARS)
analysis_end_date = end_date - relativedelta(years=FORWARD_YEARS)

print(f"分析期間: {start_date.strftime('%Y-%m-%d')} 至 {analysis_end_date.strftime('%Y-%m-%d')}")
print(f"違約觀察期: 每個正向展望事件後的 {FORWARD_YEARS} 年")


# ============================================================================
# 方法一：使用 xbbg 庫（推薦）
# ============================================================================

def method_xbbg():
    """
    使用 xbbg 庫獲取展望數據
    xbbg 是 Bloomberg API 的 Python wrapper，支援更多欄位

    安裝方式: pip install xbbg
    """
    print("\n" + "="*70)
    print("方法一：使用 xbbg 庫")
    print("="*70)

    try:
        from xbbg import blp

        # 定義要查詢的股票列表（S&P 500 主要成分股）
        tickers = [
            'AAPL US Equity', 'MSFT US Equity', 'GOOGL US Equity', 'AMZN US Equity',
            'META US Equity', 'NVDA US Equity', 'JPM US Equity', 'V US Equity',
            'JNJ US Equity', 'WMT US Equity', 'PG US Equity', 'MA US Equity',
            'UNH US Equity', 'HD US Equity', 'BAC US Equity', 'XOM US Equity',
            'PFE US Equity', 'KO US Equity', 'CSCO US Equity', 'CVX US Equity',
            'IBM US Equity', 'T US Equity', 'VZ US Equity', 'INTC US Equity',
            'MRK US Equity', 'ABBV US Equity', 'CMCSA US Equity', 'ORCL US Equity',
            'ADBE US Equity', 'CRM US Equity', 'NFLX US Equity', 'AMD US Equity',
        ]

        # 查詢展望數據
        fields = [
            'RTG_SP_OUTLOOK',
            'RTG_MOODY_OUTLOOK',
            'RTG_FITCH_OUTLOOK',
            'RTG_SP_LT_LC_ISSUER_CREDIT',
            'RTG_MOODY_LONG_TERM',
            'RTG_FITCH_LT_ISSUER_DEFAULT',
            'NAME',
        ]

        print("\n查詢當前展望數據...")
        df = blp.bdp(tickers, fields)

        if not df.empty:
            print(f"成功獲取 {len(df)} 家公司的數據")
            print("\n數據預覽:")
            print(df.head(20).to_string())

            # 篩選正向展望
            positive_mask = (
                df['RTG_SP_OUTLOOK'].astype(str).str.upper().str.contains('POS', na=False) |
                df['RTG_MOODY_OUTLOOK'].astype(str).str.upper().str.contains('POS', na=False) |
                df['RTG_FITCH_OUTLOOK'].astype(str).str.upper().str.contains('POS', na=False)
            )

            positive_df = df[positive_mask]
            print(f"\n正向展望公司數: {len(positive_df)}")

            if not positive_df.empty:
                print("\n正向展望公司:")
                print(positive_df.to_string())

            return df

    except ImportError:
        print("\nxbbg 未安裝。請執行: pip install xbbg")
    except Exception as e:
        print(f"\nxbbg 錯誤: {e}")

    return None


def method_xbbg_historical():
    """
    使用 xbbg 獲取歷史展望數據
    """
    print("\n" + "="*70)
    print("方法一B：使用 xbbg 獲取歷史展望")
    print("="*70)

    try:
        from xbbg import blp

        tickers = ['IBM US Equity', 'AAPL US Equity', 'MSFT US Equity']

        # 獲取歷史展望數據
        print("\n查詢歷史展望數據...")
        df = blp.bdh(
            tickers,
            ['RTG_SP_OUTLOOK', 'RTG_MOODY_OUTLOOK'],
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
        )

        if not df.empty:
            print(f"獲取 {len(df)} 筆歷史數據")
            print(df.tail(20))
            return df

    except ImportError:
        print("\nxbbg 未安裝")
    except Exception as e:
        print(f"\nxbbg 歷史查詢錯誤: {e}")

    return None


# ============================================================================
# 方法二：使用 blpapi 直接調用
# ============================================================================

def method_blpapi():
    """
    使用 Bloomberg blpapi 直接調用
    這是最底層的 Bloomberg Python API
    """
    print("\n" + "="*70)
    print("方法二：使用 blpapi 直接調用")
    print("="*70)

    try:
        import blpapi

        # 建立 Session
        sessionOptions = blpapi.SessionOptions()
        sessionOptions.setServerHost("localhost")
        sessionOptions.setServerPort(8194)

        session = blpapi.Session(sessionOptions)

        if not session.start():
            print("無法啟動 Bloomberg session")
            return None

        if not session.openService("//blp/refdata"):
            print("無法開啟 refdata service")
            return None

        refDataService = session.getService("//blp/refdata")

        # 建立請求
        request = refDataService.createRequest("ReferenceDataRequest")

        # 添加證券
        securities = ["IBM US Equity", "AAPL US Equity", "MSFT US Equity"]
        for sec in securities:
            request.getElement("securities").appendValue(sec)

        # 添加欄位
        fields = ["RTG_SP_OUTLOOK", "RTG_MOODY_OUTLOOK", "RTG_FITCH_OUTLOOK",
                  "RTG_SP_LT_LC_ISSUER_CREDIT", "NAME"]
        for field in fields:
            request.getElement("fields").appendValue(field)

        # 發送請求
        session.sendRequest(request)

        # 處理回應
        results = []
        while True:
            event = session.nextEvent(500)
            if event.eventType() == blpapi.Event.RESPONSE:
                for msg in event:
                    securityData = msg.getElement("securityData")
                    for i in range(securityData.numValues()):
                        security = securityData.getValueAsElement(i)
                        ticker = security.getElementAsString("security")
                        fieldData = security.getElement("fieldData")

                        row = {'Ticker': ticker}
                        for field in fields:
                            try:
                                row[field] = fieldData.getElementAsString(field)
                            except:
                                row[field] = None
                        results.append(row)
                break

        session.stop()

        if results:
            df = pd.DataFrame(results)
            print("\n查詢結果:")
            print(df.to_string())
            return df

    except ImportError:
        print("\nblpapi 未安裝。請從 Bloomberg 安裝")
    except Exception as e:
        print(f"\nblpapi 錯誤: {e}")

    return None


# ============================================================================
# 方法三：使用 BQL 可用欄位進行替代分析
# ============================================================================

def method_bql_alternative():
    """
    使用 BQL 可用欄位進行替代分析
    由於展望欄位不可用，使用評級變化作為替代指標
    """
    print("\n" + "="*70)
    print("方法三：使用 BQL 替代分析（評級變化）")
    print("="*70)

    try:
        import bql
        bq = bql.Service()

        # 使用可用的欄位
        query = """
        get(
            NAME,
            RTG_SP_LT_LC_ISSUER_CREDIT,
            RTG_SP,
            RTG_MOODY,
            RTG_FITCH,
            GICS_SECTOR_NAME,
            CUR_MKT_CAP
        )
        for(members('SPX Index'))
        """

        print("\n執行BQL查詢...")
        response = bq.execute(query)

        dfs = []
        for item in response:
            df = item.df()
            if not df.empty:
                dfs.append(df)
                print(f"  {item.name}: {len(df)} 筆")

        if dfs:
            result_df = pd.concat(dfs, axis=1)

            # 移除重複的欄位
            result_df = result_df.loc[:, ~result_df.columns.duplicated()]

            print(f"\n成功獲取 {len(result_df)} 家公司")
            print("\n評級分布:")

            if 'RTG_SP_LT_LC_ISSUER_CREDIT' in result_df.columns:
                rating_dist = result_df['RTG_SP_LT_LC_ISSUER_CREDIT'].value_counts()
                print(rating_dist)

            print("\n數據預覽（前20家）:")
            print(result_df.head(20).to_string())

            return result_df

    except Exception as e:
        print(f"\nBQL替代分析錯誤: {e}")

    return None


# ============================================================================
# 方法四：使用 BQNT DataFrame API
# ============================================================================

def method_bqnt_dataframe():
    """
    使用 BQNT 的 DataFrame API 嘗試獲取更多數據
    """
    print("\n" + "="*70)
    print("方法四：使用 BQNT DataFrame API")
    print("="*70)

    try:
        import bql
        bq = bql.Service()

        # 嘗試使用不同的查詢方式
        universe = bq.univ.members('SPX Index')

        # 測試信用相關的 BQL 原生函數
        test_items = [
            ('credit_risk', 'bq.data.credit_risk()'),
            ('cds_spread', 'bq.data.cds_spread()'),
            ('probability_of_default', 'bq.data.probability_of_default()'),
        ]

        print("\n測試 BQL 原生信用函數...")
        for name, _ in test_items:
            try:
                if hasattr(bq.data, name):
                    func = getattr(bq.data, name)
                    request = bql.Request(['IBM US Equity'], {'Test': func()})
                    response = bq.execute(request)
                    df = response[0].df()
                    if not df.empty:
                        print(f"  ✓ {name}: {df.iloc[0, 0]}")
                else:
                    print(f"  ✗ {name}: 函數不存在")
            except Exception as e:
                print(f"  ✗ {name}: {str(e)[:40]}")

    except Exception as e:
        print(f"\nBQNT DataFrame API 錯誤: {e}")

    return None


# ============================================================================
# 方法五：使用 pdblp（另一個 Bloomberg wrapper）
# ============================================================================

def method_pdblp():
    """
    使用 pdblp 庫
    安裝方式: pip install pdblp
    """
    print("\n" + "="*70)
    print("方法五：使用 pdblp 庫")
    print("="*70)

    try:
        import pdblp
        con = pdblp.BCon(debug=False)
        con.start()

        tickers = ['IBM US Equity', 'AAPL US Equity', 'MSFT US Equity',
                   'JPM US Equity', 'BAC US Equity', 'C US Equity']

        fields = ['RTG_SP_OUTLOOK', 'RTG_MOODY_OUTLOOK', 'RTG_FITCH_OUTLOOK',
                  'RTG_SP_LT_LC_ISSUER_CREDIT', 'NAME']

        print("\n查詢展望數據...")
        df = con.ref(tickers, fields)

        if not df.empty:
            print(f"成功獲取 {len(df)} 筆數據")
            print(df.to_string())
            return df

        con.stop()

    except ImportError:
        print("\npdblp 未安裝。請執行: pip install pdblp")
    except Exception as e:
        print(f"\npdblp 錯誤: {e}")

    return None


# ============================================================================
# 方法六：完整研究框架（使用可用方法）
# ============================================================================

def comprehensive_research():
    """
    完整研究框架
    根據可用的 API 執行分析
    """
    print("\n" + "="*70)
    print("正向展望公司違約率 - 完整研究框架")
    print("="*70)

    results = {
        'method_used': None,
        'total_companies': 0,
        'positive_outlook_count': 0,
        'by_agency': {},
        'data': None
    }

    # 嘗試各種方法
    print("\n嘗試獲取展望數據...")

    # 嘗試 xbbg
    df = method_xbbg()
    if df is not None and not df.empty:
        results['method_used'] = 'xbbg'
        results['data'] = df
        results['total_companies'] = len(df)

        # 計算正向展望
        for col in ['RTG_SP_OUTLOOK', 'RTG_MOODY_OUTLOOK', 'RTG_FITCH_OUTLOOK']:
            if col in df.columns:
                count = df[col].astype(str).str.upper().str.contains('POS', na=False).sum()
                results['by_agency'][col] = count

        results['positive_outlook_count'] = sum(results['by_agency'].values())

    # 如果 xbbg 失敗，嘗試 pdblp
    if results['data'] is None:
        df = method_pdblp()
        if df is not None:
            results['method_used'] = 'pdblp'
            results['data'] = df

    # 如果都失敗，使用 BQL 替代方案
    if results['data'] is None:
        df = method_bql_alternative()
        if df is not None:
            results['method_used'] = 'bql_alternative'
            results['data'] = df
            results['total_companies'] = len(df)

    # 輸出結果
    print("\n" + "="*60)
    print("研究結果摘要")
    print("="*60)

    print(f"\n使用方法: {results['method_used']}")
    print(f"總公司數: {results['total_companies']}")
    print(f"正向展望公司數: {results['positive_outlook_count']}")

    if results['by_agency']:
        print("\n各信評機構正向展望:")
        for agency, count in results['by_agency'].items():
            print(f"  {agency}: {count}")

    return results


# ============================================================================
# 主程式
# ============================================================================

def main():
    """
    主程式
    """
    print("\n" + "="*70)
    print("Bloomberg BQNT - 正向展望公司違約率分析")
    print("="*70)

    print("""
    注意事項：
    =========
    由於您的 BQL 環境不支持展望欄位（RTG_SP_OUTLOOK 等），
    本腳本提供多種替代方案：

    1. xbbg 庫（推薦）- pip install xbbg
    2. pdblp 庫 - pip install pdblp
    3. blpapi 直接調用
    4. BQL 替代分析（使用評級欄位）

    請確認您有安裝以上任一套件。
    """)

    # 執行完整研究
    results = comprehensive_research()

    # 提供手動查詢指引
    print("\n" + "="*70)
    print("手動查詢指引")
    print("="*70)

    print("""
    如果自動方法都失敗，您可以在 Bloomberg Terminal 中手動查詢：

    1. 使用 RATC（Rating Actions）功能：
       - 輸入 RATC <GO>
       - 篩選 "Outlook" 類型的評級行動
       - 匯出數據到 Excel

    2. 使用 SRCH（Equity Screening）功能：
       - 輸入 SRCH <GO>
       - 添加條件: RTG_SP_OUTLOOK = "Positive"
       - 或: RTG_MOODY_OUTLOOK = "Positive"
       - 匯出結果

    3. 使用 CACS（Corporate Actions）功能：
       - 查詢信用評級相關的公司行動

    4. 在 Excel 中使用 BDP/BDH：
       =BDP("IBM US Equity", "RTG_SP_OUTLOOK")
       =BDH("IBM US Equity", "RTG_SP_OUTLOOK", "2014-01-01", "2024-01-01")
    """)

    return results


# ============================================================================
# 執行
# ============================================================================

if __name__ == "__main__":
    results = main()
