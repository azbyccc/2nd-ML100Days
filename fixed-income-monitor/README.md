# Fixed Income Market Monitor — Non-Bloomberg Replacement

> **目標**：用完全公開、可合法取得的資料，重建 Bloomberg 固定收益市場監控畫面中的 A/B 級欄位。

---

## 專案架構

```
fixed-income-monitor/
├── main.py                      # 主程式入口
├── requirements.txt
├── pytest.ini
├── field_inventory.csv          # 所有欄位盤點（含等級）
├── source_mapping.csv           # 來源對照表
├── rebuild_feasibility.csv      # 可重建性分析
│
├── config/
│   └── sources.yaml             # 各來源設定（URL / rate limit / series ID）
│
├── src/
│   ├── schema.py                # 統一資料模型（MarketDataPoint + PerformanceSnapshot）
│   ├── storage.py               # Parquet/CSV 歷史資料儲存層
│   │
│   ├── collectors/
│   │   ├── base_collector.py    # 基底（robots.txt / rate limit / retry）
│   │   ├── fred_collector.py    # FRED API（A 級）
│   │   ├── treasury_collector.py# Treasury.gov XML（A 級）
│   │   ├── yahoo_collector.py   # Yahoo Finance via yfinance（A/B 級）
│   │   ├── ecb_collector.py     # ECB SDMX API（A 級）
│   │   └── cboe_collector.py    # CBOE VIX CSV（A 級）
│   │
│   ├── calculators/
│   │   └── performance_calculator.py  # D1/WTD/MTD/YTD/pct_rank（from history）
│   │
│   └── output/
│       └── report_builder.py    # CSV + Excel 輸出
│
├── tests/
│   ├── test_fred.py
│   ├── test_treasury.py
│   ├── test_yahoo.py
│   ├── test_ecb.py
│   ├── test_cboe.py
│   ├── test_calculator.py
│   └── fixtures/                # 靜態 JSON/XML/CSV fixture，無需 HTTP
│
├── data/
│   ├── history/                 # 歷史序列 (*.parquet 或 *.csv fallback)
│   └── processed/               # 最終輸出 CSV/XLSX
│
└── logs/                        # 執行日誌
```

---

## 快速開始

### 1. 安裝依賴

```bash
cd fixed-income-monitor
pip install -r requirements.txt
```

### 2. 設定 FRED API Key（免費）

> 到 https://fred.stlouisfed.org/docs/api/api_key.html 申請，完全免費。

```bash
export FRED_API_KEY="your_key_here"
```

### 3. 執行

```bash
# 跑所有來源（今天）
python main.py

# 只跑特定來源
python main.py --sources fred,yahoo,cboe

# 指定日期
python main.py --date 2026-04-25

# 不輸出 Excel（只有 CSV）
python main.py --no-xlsx

# 清除超過 400 天的歷史資料
python main.py --prune

# 列出可用來源
python main.py --list-sources
```

### 4. 執行測試

```bash
# 所有測試（完全離線，無需任何 API key）
pytest

# 詳細輸出
pytest -v

# 單一測試檔
pytest tests/test_fred.py -v
```

---

## 資料來源說明

| 來源 | 類型 | 認證 | 法律風險 | 覆蓋欄位 |
|------|------|------|---------|---------|
| **FRED** (St. Louis Fed) | REST JSON API | 免費 API Key | 🟢 低 | US Treasuries, TIPS, BEI, ICE BofA credit indices |
| **Treasury.gov** | XML Atom Feed | 無需 | 🟢 低 | US yield curve 1M~30Y |
| **Yahoo Finance** (yfinance) | 非官方 wrapper | 無需 | 🟡 中 | 股市指數, G10/EM FX, 大宗商品 |
| **ECB SDMX API** | REST CSV/JSON | 無需 | 🟢 低 | Euribor, ESTR, EUR yield curve |
| **CBOE** | 靜態 CSV | 無需 | 🟢 低 | VIX 每日歷史 |

### 各來源風險與備援

#### FRED API
- **風險**：API Key 可能被 revoke（免費帳號限制 120 req/min）；ICE BofA 系列有 T+1 發布延遲
- **備援**：Treasury.gov XML 提供 US 殖利率曲線的即時替代；ICE BofA 系列無免費即時替代
- **口徑注意**：OAS 欄位在 FRED 已是 basis points（非 percent）；勿重複換算

#### Treasury.gov
- **風險**：XML URL 格式若 Treasury 改版可能失效（歷史上曾發生過）
- **備援**：FRED DGS2/DGS5/DGS10/DGS30 系列（同源資料，通常 same-day）
- **建議**：每季驗證 URL 是否仍有效

#### Yahoo Finance (yfinance)
- **風險**：Yahoo 未公開官方 API；yfinance 是逆向工程 wrapper，可能無預警失效；Yahoo ToS 禁止商業使用
- **備援**：
  - 股市指數 → Stooq.com (stooq.com) 或交易所官方資料
  - FX → ECB SDMX API 涵蓋 EUR 相關對；其他貨幣無明確免費替代
  - 大宗商品 → EIA (energy.gov) 涵蓋 WTI/Brent；USDA 涵蓋農產品
- **建議**：固定 `yfinance` 版本；監控抓取失敗率

#### ECB SDMX API
- **風險**：ECB series key 不定期更新（需在 ECB data portal 驗證）；假日資料缺口
- **備援**：FRED 有月頻率的德/法/義 10Y 殖利率（IRLTLT01DEM156N 等）
- **建議**：每季到 https://data-api.ecb.europa.eu/service/dataflow 驗證 series key 仍有效

#### CBOE VIX
- **風險**：CDN URL 可能變更
- **備援**：Yahoo Finance `^VIX` ticker（同資料）

---

## 欄位等級說明

| 等級 | 定義 | 欄位數 |
|------|------|--------|
| **A** | 可直接重建，資料與 Bloomberg 口徑幾乎一致 | ~60 個 |
| **B** | 可近似重建，但指數構成或方法論不同 | ~8 個 |
| **C** | 部分取得，需人工補值或接受定義差異 | ~3 個 |
| **D** | 幾乎無法重建（JPM 專有指數），本專案不實作 | 3 個 |

### D 級欄位說明（不實作）

| 欄位 | Bloomberg 對應 | 原因 |
|------|--------------|------|
| JPM EMBI Global Spread | JPEIGLBL | JPMorgan 專有，需 Bloomberg 或 JPM 授權 |
| JPM CEMBI Broad IG OAS | JBCDGIG | 同上 |
| JPM CEMBI Broad HY OAS | JBCDGHY | 同上 |

**近似替代**：可使用 FRED 的 ICE BofA EM 系列（`EM_HY_OAS`, `EM_IG_OAS`），但覆蓋範圍（企業債 vs 主權債）和構成方法論均不同。

---

## 統一 Schema

每個資料點輸出以下欄位：

| 欄位 | 型別 | 說明 |
|------|------|------|
| `as_of_date` | date | 資料日期 |
| `field_name` | str | 標準化欄位 ID（如 `US_TREASURY_10Y`） |
| `source_name` | str | 來源名稱（如 `FRED`, `ECB`） |
| `source_url` | str | 實際抓取的 URL |
| `raw_value` | float \| None | 來源原始值（未換算） |
| `normalized_value` | float \| None | 換算後的值（None = 缺值） |
| `unit` | str | `percent` / `basis_points` / `index_level` / `fx_rate` / `usd_per_unit` |
| `frequency` | str | `daily` / `weekly` / `monthly` |
| `asset_class` | str | `rates` / `credit` / `equity` / `fx` / `commodity` |
| `region` | str | `US` / `EU` / `UK` / `JP` / `ASIA` / `EM` / ... |
| `rating_bucket` | str | `na` / `ig` / `hy` / `aaa` / `aa` / `a` / `bbb` / `bb` / `b` / `ccc` |
| `tenor_bucket` | str | `na` / `overnight` / `1m` / `3m` / `6m` / `1y` / `2y` / `5y` / `10y` / `30y` |
| `rebuild_grade` | str | `A` / `B` / `C` / `D` |
| `notes` | str | 資料品質備註 |

績效計算欄位（`PerformanceSnapshot`）：

| 欄位 | 語義 | rates/credit 計算 | equity/FX/commodity 計算 |
|------|------|-----------------|------------------------|
| `d1` | 前一個交易日 | 絕對變動（同單位） | 百分比報酬（%） |
| `wtd` | vs 上週五收盤 | 同上 | 同上 |
| `mtd` | vs 上月底 | 同上 | 同上 |
| `ytd` | vs 去年 12/31 | 同上 | 同上 |
| `chg_1w` | vs -7 個日曆日 | 同上 | 同上 |
| `chg_1m` | vs -1 個月 | 同上 | 同上 |
| `chg_1y` | vs -12 個月 | 同上 | 同上 |
| `pct_rank_1y` | 過去 252 交易日的百分位排名 | 0（最低）~ 100（最高） | 同上 |

> **重要**：所有績效欄位均從歷史序列自行計算，不依賴來源網站預計算的數值。

---

## 歷史資料儲存

資料落地於 `data/history/` 目錄，每個欄位一個 Parquet 檔（需安裝 pyarrow）：

```
data/history/
  US_TREASURY_10Y.parquet
  US_HY_OAS.parquet
  EQ_SP500.parquet
  ...
```

若 `pyarrow` 未安裝，自動降級為 CSV：
```
data/history/
  US_TREASURY_10Y.csv
  ...
```

每次執行自動 append + dedup（以 `as_of_date` 為 key）。

---

## 下一步（待確認事項）

1. **Bloomberg 截圖中的 USD CT10 Yield**：對各 EM 國家的欄位，是 local currency 10Y yield 換算成 USD 殖利率，還是以 USD 計價的主權債殖利率？請確認後可補充對應的 EMBI 或 local yield 抓取邏輯。

2. **EEMA / Asia 個別國家股市**：截圖中包含土耳其 XU100、沙烏地 TASI、印度 Sensex 等，Yahoo Finance ticker 已在 `yahoo_collector.py` 的 `FIELDS` 中列出，可直接擴充啟用。

3. **ICE BofA AAA/AA US Corp OAS**：FRED 有 `BAMLC0A1CAAA` 和 `BAMLC0A2CAA` 系列，可加入 `FIELDS`。

4. **EU 個別國家 10Y 殖利率**（義大利、西班牙）：FRED 月頻率版本可用；日頻率版本需 ECB SDMX `IRS` dataset（較複雜的 series key）。

5. **Taiwan CBC 抓取穩定性**：建議測試後確認是否需要改為手動維護 CSV。
