#!/usr/bin/env python3
"""
高鐵搶票機器人 - 網頁介面
THSR Ticket Booking Bot - Web Interface
"""

from flask import Flask, render_template, request, jsonify
import threading
import logging
import sys
import os

# 確保可以 import thsr_bot 模組
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from thsr_bot.config import (
    BookingConfig,
    PassengerInfo,
    TicketInfo,
    BotConfig,
    TicketType,
    CarClass,
    SeatPreference
)
from thsr_bot.booking import THSRBookingBot, BookingStatus

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 儲存執行狀態
booking_status = {
    "running": False,
    "status": "idle",
    "message": "",
    "booking_code": None,
    "logs": []
}


class WebLogHandler(logging.Handler):
    """將日誌傳送到網頁"""
    def emit(self, record):
        log_entry = self.format(record)
        booking_status["logs"].append(log_entry)
        # 只保留最近 100 條日誌
        if len(booking_status["logs"]) > 100:
            booking_status["logs"] = booking_status["logs"][-100:]


# 添加網頁日誌處理器
web_handler = WebLogHandler()
web_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logging.getLogger().addHandler(web_handler)


@app.route("/")
def index():
    """首頁"""
    return render_template("index.html")


@app.route("/api/book", methods=["POST"])
def start_booking():
    """開始訂票"""
    global booking_status

    if booking_status["running"]:
        return jsonify({"success": False, "message": "已有訂票程序正在執行中"})

    try:
        data = request.json

        # 票種轉換
        ticket_type_map = {
            "adult": TicketType.ADULT,
            "child": TicketType.CHILD,
            "senior": TicketType.SENIOR,
            "disabled": TicketType.DISABLED
        }

        # 車廂類型轉換
        car_class_map = {
            "standard": CarClass.STANDARD,
            "business": CarClass.BUSINESS
        }

        # 座位偏好轉換
        seat_pref_map = {
            "none": SeatPreference.NONE,
            "window": SeatPreference.WINDOW,
            "aisle": SeatPreference.AISLE
        }

        # 建立配置
        config = BookingConfig(
            passenger=PassengerInfo(
                id_number=data["id_number"],
                passenger_name=data["passenger_name"],
                phone=data["phone"],
                email=data.get("email") or None
            ),
            ticket=TicketInfo(
                departure_station=data["departure_station"],
                arrival_station=data["arrival_station"],
                travel_date=data["travel_date"],
                preferred_time=data["preferred_time"],
                ticket_count=int(data.get("ticket_count", 1)),
                ticket_type=ticket_type_map.get(data.get("ticket_type", "adult"), TicketType.ADULT),
                car_class=car_class_map.get(data.get("car_class", "standard"), CarClass.STANDARD),
                seat_preference=seat_pref_map.get(data.get("seat_preference", "none"), SeatPreference.NONE)
            ),
            bot_config=BotConfig(
                headless=data.get("headless", False),
                max_retries=int(data.get("max_retries", 50)),
                retry_interval=int(data.get("retry_interval", 500))
            )
        )

        # 重置狀態
        booking_status["running"] = True
        booking_status["status"] = "running"
        booking_status["message"] = "正在啟動..."
        booking_status["booking_code"] = None
        booking_status["logs"] = []

        # 在背景執行訂票
        thread = threading.Thread(target=run_booking, args=(config,))
        thread.daemon = True
        thread.start()

        return jsonify({"success": True, "message": "訂票程序已啟動"})

    except Exception as e:
        logger.error(f"啟動訂票失敗: {e}")
        return jsonify({"success": False, "message": f"錯誤: {str(e)}"})


def run_booking(config: BookingConfig):
    """執行訂票（背景執行）"""
    global booking_status

    try:
        bot = THSRBookingBot(config)
        result = bot.run()

        booking_status["status"] = result.status.value
        booking_status["message"] = result.message
        booking_status["booking_code"] = result.booking_code

    except Exception as e:
        logger.error(f"訂票過程發生錯誤: {e}")
        booking_status["status"] = "failed"
        booking_status["message"] = f"錯誤: {str(e)}"

    finally:
        booking_status["running"] = False


@app.route("/api/status")
def get_status():
    """取得訂票狀態"""
    return jsonify(booking_status)


@app.route("/api/stop", methods=["POST"])
def stop_booking():
    """停止訂票（目前僅標記停止，實際需要改進）"""
    global booking_status
    booking_status["running"] = False
    booking_status["status"] = "stopped"
    booking_status["message"] = "已手動停止"
    return jsonify({"success": True, "message": "已發送停止訊號"})


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  高鐵搶票機器人 - 網頁介面")
    print("=" * 50)
    print("\n請在瀏覽器開啟: http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
