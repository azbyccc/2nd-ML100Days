"""
配置管理模組
Configuration Management Module
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List
from enum import Enum

from .stations import validate_stations, STATION_LIST


class TicketType(Enum):
    """票種"""
    ADULT = "adult"           # 成人
    CHILD = "child"           # 孩童
    SENIOR = "senior"         # 敬老
    DISABLED = "disabled"     # 愛心


class CarClass(Enum):
    """車廂類型"""
    STANDARD = "standard"     # 標準車廂
    BUSINESS = "business"     # 商務車廂


class SeatPreference(Enum):
    """座位偏好"""
    NONE = "none"             # 無偏好
    WINDOW = "window"         # 靠窗
    AISLE = "aisle"           # 靠走道


@dataclass
class PassengerInfo:
    """乘客資訊"""
    id_number: str            # 身分證字號
    passenger_name: str       # 乘客姓名
    phone: str                # 聯絡電話
    email: Optional[str] = None  # 電子郵件

    def __post_init__(self):
        self._validate()

    def _validate(self):
        """驗證乘客資料"""
        if not self.id_number or len(self.id_number) != 10:
            raise ValueError("身分證字號格式不正確")
        if not self.passenger_name:
            raise ValueError("乘客姓名不能為空")
        if not self.phone or len(self.phone) < 9:
            raise ValueError("聯絡電話格式不正確")


@dataclass
class TicketInfo:
    """車票資訊"""
    departure_station: str    # 出發站
    arrival_station: str      # 到達站
    travel_date: str          # 乘車日期 (YYYY-MM-DD)
    preferred_time: str       # 偏好出發時間 (HH:MM)
    ticket_count: int = 1     # 購票張數
    ticket_type: TicketType = TicketType.ADULT  # 票種
    time_range: int = 60      # 可接受時間範圍（分鐘）
    train_no: Optional[str] = None  # 指定車次
    car_class: CarClass = CarClass.STANDARD  # 車廂類型
    seat_preference: SeatPreference = SeatPreference.NONE  # 座位偏好

    def __post_init__(self):
        self._validate()

    def _validate(self):
        """驗證車票資料"""
        validate_stations(self.departure_station, self.arrival_station)

        # 驗證日期格式
        try:
            travel = datetime.strptime(self.travel_date, "%Y-%m-%d").date()
            if travel < date.today():
                raise ValueError("乘車日期不能早於今天")
        except ValueError as e:
            if "乘車日期" in str(e):
                raise
            raise ValueError(f"日期格式錯誤，請使用 YYYY-MM-DD 格式: {self.travel_date}")

        # 驗證時間格式
        try:
            datetime.strptime(self.preferred_time, "%H:%M")
        except ValueError:
            raise ValueError(f"時間格式錯誤，請使用 HH:MM 格式: {self.preferred_time}")

        # 驗證票數
        if not 1 <= self.ticket_count <= 6:
            raise ValueError("購票張數必須在 1-6 張之間")

    def get_time_hour(self) -> str:
        """取得小時部分"""
        return self.preferred_time.split(":")[0]

    def get_time_minute(self) -> str:
        """取得分鐘部分"""
        return self.preferred_time.split(":")[1]


@dataclass
class BotConfig:
    """機器人設定"""
    start_time: Optional[str] = None  # 開始搶票時間
    retry_interval: int = 500         # 重試間隔（毫秒）
    max_retries: int = 100            # 最大重試次數
    accept_alternative: bool = True   # 是否接受替代班次
    alternative_count: int = 3        # 搜尋替代班次數量
    auto_pay: bool = False            # 是否自動付款
    notification_url: Optional[str] = None  # Webhook 通知網址
    headless: bool = False            # 是否使用無頭模式
    debug: bool = False               # 除錯模式

    def get_retry_interval_seconds(self) -> float:
        """取得重試間隔（秒）"""
        return self.retry_interval / 1000


@dataclass
class BookingConfig:
    """完整訂票設定"""
    passenger: PassengerInfo
    ticket: TicketInfo
    bot_config: BotConfig = field(default_factory=BotConfig)

    @classmethod
    def from_json(cls, json_path: str) -> "BookingConfig":
        """從 JSON 檔案載入設定"""
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        passenger_data = data.get("passenger", {})
        ticket_data = data.get("ticket", {})
        bot_data = data.get("bot_config", {})

        # 處理票種 enum
        if "ticket_type" in ticket_data:
            ticket_data["ticket_type"] = TicketType(ticket_data["ticket_type"])
        if "car_class" in ticket_data:
            ticket_data["car_class"] = CarClass(ticket_data["car_class"])
        if "seat_preference" in ticket_data:
            ticket_data["seat_preference"] = SeatPreference(ticket_data["seat_preference"])

        return cls(
            passenger=PassengerInfo(**passenger_data),
            ticket=TicketInfo(**ticket_data),
            bot_config=BotConfig(**bot_data)
        )

    @classmethod
    def from_dict(cls, data: dict) -> "BookingConfig":
        """從字典載入設定"""
        passenger_data = data.get("passenger", {})
        ticket_data = data.get("ticket", {})
        bot_data = data.get("bot_config", {})

        # 處理票種 enum
        if "ticket_type" in ticket_data and isinstance(ticket_data["ticket_type"], str):
            ticket_data["ticket_type"] = TicketType(ticket_data["ticket_type"])
        if "car_class" in ticket_data and isinstance(ticket_data["car_class"], str):
            ticket_data["car_class"] = CarClass(ticket_data["car_class"])
        if "seat_preference" in ticket_data and isinstance(ticket_data["seat_preference"], str):
            ticket_data["seat_preference"] = SeatPreference(ticket_data["seat_preference"])

        return cls(
            passenger=PassengerInfo(**passenger_data),
            ticket=TicketInfo(**ticket_data),
            bot_config=BotConfig(**bot_data)
        )

    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            "passenger": {
                "id_number": self.passenger.id_number,
                "passenger_name": self.passenger.passenger_name,
                "phone": self.passenger.phone,
                "email": self.passenger.email
            },
            "ticket": {
                "departure_station": self.ticket.departure_station,
                "arrival_station": self.ticket.arrival_station,
                "travel_date": self.ticket.travel_date,
                "preferred_time": self.ticket.preferred_time,
                "time_range": self.ticket.time_range,
                "train_no": self.ticket.train_no,
                "ticket_count": self.ticket.ticket_count,
                "ticket_type": self.ticket.ticket_type.value,
                "car_class": self.ticket.car_class.value,
                "seat_preference": self.ticket.seat_preference.value
            },
            "bot_config": {
                "start_time": self.bot_config.start_time,
                "retry_interval": self.bot_config.retry_interval,
                "max_retries": self.bot_config.max_retries,
                "accept_alternative": self.bot_config.accept_alternative,
                "alternative_count": self.bot_config.alternative_count,
                "auto_pay": self.bot_config.auto_pay,
                "notification_url": self.bot_config.notification_url,
                "headless": self.bot_config.headless,
                "debug": self.bot_config.debug
            }
        }
