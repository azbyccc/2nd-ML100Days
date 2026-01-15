#!/usr/bin/env python3
"""
高鐵搶票機器人主程式
THSR Ticket Booking Bot Main Entry Point

Usage:
    python -m thsr_bot.main --config config.json
    python -m thsr_bot.main --interactive
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta

from .config import (
    BookingConfig,
    PassengerInfo,
    TicketInfo,
    BotConfig,
    TicketType,
    CarClass,
    SeatPreference
)
from .booking import THSRBookingBot, BookingStatus
from .stations import STATION_LIST

# 設定日誌格式
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def interactive_mode() -> BookingConfig:
    """
    互動模式：引導使用者輸入訂票資訊

    Returns:
        訂票配置
    """
    print("\n" + "=" * 50)
    print("  高鐵搶票機器人 - 互動模式")
    print("=" * 50 + "\n")

    # 乘客資訊
    print("【乘客資訊】")
    id_number = input("身分證字號: ").strip()
    passenger_name = input("乘客姓名: ").strip()
    phone = input("聯絡電話: ").strip()
    email = input("電子郵件（可選，按 Enter 跳過）: ").strip() or None

    # 車票資訊
    print("\n【車票資訊】")
    print(f"可用車站: {', '.join(STATION_LIST)}")
    departure_station = input("出發站: ").strip()
    arrival_station = input("到達站: ").strip()

    # 日期
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    travel_date = input(f"乘車日期 (YYYY-MM-DD，預設 {tomorrow}): ").strip()
    if not travel_date:
        travel_date = tomorrow

    # 時間
    preferred_time = input("偏好出發時間 (HH:MM，如 08:00): ").strip()

    # 票數
    ticket_count_str = input("購票張數 (1-6，預設 1): ").strip()
    ticket_count = int(ticket_count_str) if ticket_count_str else 1

    # 票種
    print("\n票種選項:")
    print("  1. 成人 (adult)")
    print("  2. 孩童 (child)")
    print("  3. 敬老 (senior)")
    print("  4. 愛心 (disabled)")
    ticket_type_choice = input("選擇票種 (1-4，預設 1): ").strip()
    ticket_type_map = {"1": TicketType.ADULT, "2": TicketType.CHILD,
                       "3": TicketType.SENIOR, "4": TicketType.DISABLED}
    ticket_type = ticket_type_map.get(ticket_type_choice, TicketType.ADULT)

    # 車廂類型
    print("\n車廂類型:")
    print("  1. 標準車廂 (standard)")
    print("  2. 商務車廂 (business)")
    car_class_choice = input("選擇車廂 (1-2，預設 1): ").strip()
    car_class = CarClass.BUSINESS if car_class_choice == "2" else CarClass.STANDARD

    # 座位偏好
    print("\n座位偏好:")
    print("  1. 無偏好 (none)")
    print("  2. 靠窗 (window)")
    print("  3. 靠走道 (aisle)")
    seat_choice = input("選擇座位偏好 (1-3，預設 1): ").strip()
    seat_pref_map = {"1": SeatPreference.NONE, "2": SeatPreference.WINDOW,
                     "3": SeatPreference.AISLE}
    seat_preference = seat_pref_map.get(seat_choice, SeatPreference.NONE)

    # 機器人設定
    print("\n【機器人設定】")
    headless_choice = input("是否使用無頭模式 (y/N): ").strip().lower()
    headless = headless_choice == "y"

    max_retries_str = input("最大重試次數 (預設 100): ").strip()
    max_retries = int(max_retries_str) if max_retries_str else 100

    # 建立配置
    config = BookingConfig(
        passenger=PassengerInfo(
            id_number=id_number,
            passenger_name=passenger_name,
            phone=phone,
            email=email
        ),
        ticket=TicketInfo(
            departure_station=departure_station,
            arrival_station=arrival_station,
            travel_date=travel_date,
            preferred_time=preferred_time,
            ticket_count=ticket_count,
            ticket_type=ticket_type,
            car_class=car_class,
            seat_preference=seat_preference
        ),
        bot_config=BotConfig(
            headless=headless,
            max_retries=max_retries
        )
    )

    # 顯示確認資訊
    print("\n" + "=" * 50)
    print("  訂票資訊確認")
    print("=" * 50)
    print(f"乘客: {passenger_name} ({id_number})")
    print(f"路線: {departure_station} → {arrival_station}")
    print(f"日期: {travel_date} {preferred_time}")
    print(f"票數: {ticket_count} 張 ({ticket_type.value})")
    print(f"車廂: {car_class.value}")
    print(f"座位: {seat_preference.value}")
    print("=" * 50)

    confirm = input("\n確認開始訂票? (Y/n): ").strip().lower()
    if confirm == "n":
        print("取消訂票")
        sys.exit(0)

    return config


def main():
    """主程式入口"""
    parser = argparse.ArgumentParser(
        description="高鐵搶票機器人 (THSR Ticket Booking Bot)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  使用配置檔:
    python -m thsr_bot.main --config config.json

  互動模式:
    python -m thsr_bot.main --interactive

  指定開始時間:
    python -m thsr_bot.main --config config.json --start-time "2026-01-20T00:00:00"
        """
    )

    parser.add_argument(
        "-c", "--config",
        type=str,
        help="配置檔路徑 (JSON 格式)"
    )

    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="使用互動模式輸入訂票資訊"
    )

    parser.add_argument(
        "--start-time",
        type=str,
        help="搶票開始時間 (ISO 格式: YYYY-MM-DDTHH:MM:SS)"
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="使用無頭模式（不顯示瀏覽器視窗）"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="啟用除錯模式"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="乾跑模式：只驗證配置，不實際訂票"
    )

    args = parser.parse_args()

    # 設定日誌等級
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # 取得配置
    if args.interactive:
        config = interactive_mode()
    elif args.config:
        try:
            config = BookingConfig.from_json(args.config)
            logger.info(f"已載入配置檔: {args.config}")
        except FileNotFoundError:
            logger.error(f"找不到配置檔: {args.config}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"載入配置檔失敗: {e}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    # 覆寫命令行參數
    if args.start_time:
        config.bot_config.start_time = args.start_time
    if args.headless:
        config.bot_config.headless = True
    if args.debug:
        config.bot_config.debug = True

    # 乾跑模式
    if args.dry_run:
        print("\n【乾跑模式】配置驗證成功！")
        print(json.dumps(config.to_dict(), ensure_ascii=False, indent=2))
        sys.exit(0)

    # 執行訂票
    bot = THSRBookingBot(config)
    result = bot.run()

    # 輸出結果
    print("\n" + "=" * 50)
    print("  訂票結果")
    print("=" * 50)
    print(f"狀態: {result.status.value}")
    print(f"訊息: {result.message}")

    if result.booking_code:
        print(f"訂票代碼: {result.booking_code}")
        print("\n請在 30 分鐘內完成付款！")

    if result.error:
        print(f"錯誤: {result.error}")

    print("=" * 50)

    # 回傳狀態碼
    sys.exit(0 if result.status == BookingStatus.SUCCESS else 1)


if __name__ == "__main__":
    main()
