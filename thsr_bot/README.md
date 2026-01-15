# THSR 高鐵搶票機器人

台灣高鐵自動訂票機器人，支援自動填表、驗證碼辨識、定時搶票等功能。

## 功能特色

- 自動填寫訂票表單
- 支援驗證碼自動辨識 (ddddocr) 或手動輸入
- 定時搶票（精確到毫秒）
- 自動重試機制
- Webhook 通知支援
- 支援互動模式和配置檔模式

## 安裝

```bash
# 安裝依賴
pip install -r thsr_bot/requirements.txt

# 可選：安裝驗證碼自動辨識
pip install ddddocr
```

## 使用方式

### 互動模式

```bash
python -m thsr_bot.main --interactive
```

### 配置檔模式

1. 複製範例配置檔：
```bash
cp thsr_bot/config.example.json config.json
```

2. 編輯 `config.json` 填入您的資訊

3. 執行：
```bash
python -m thsr_bot.main --config config.json
```

### 定時搶票

```bash
# 設定開賣時間自動搶票
python -m thsr_bot.main --config config.json --start-time "2026-01-25T00:00:00"
```

### 無頭模式

```bash
# 不顯示瀏覽器視窗
python -m thsr_bot.main --config config.json --headless
```

## 配置參數說明

| 參數 | 說明 |
|------|------|
| `passenger.id_number` | 身分證字號 |
| `passenger.passenger_name` | 乘客姓名 |
| `passenger.phone` | 聯絡電話 |
| `ticket.departure_station` | 出發站（南港/台北/板橋/桃園/新竹/苗栗/台中/彰化/雲林/嘉義/台南/左營） |
| `ticket.arrival_station` | 到達站 |
| `ticket.travel_date` | 乘車日期 (YYYY-MM-DD) |
| `ticket.preferred_time` | 偏好時間 (HH:MM) |
| `ticket.ticket_count` | 票數 (1-6) |
| `ticket.ticket_type` | 票種 (adult/child/senior/disabled) |
| `bot_config.start_time` | 開始搶票時間 |
| `bot_config.max_retries` | 最大重試次數 |

## 注意事項

- 請遵守台灣高鐵網站使用條款
- 本程式僅供學習研究使用
- 訂票成功後請於 30 分鐘內完成付款
