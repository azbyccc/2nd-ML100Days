"""
高鐵訂票核心邏輯
THSR Booking Core Logic
"""

import logging
import time
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException
)

from .config import BookingConfig, TicketType, CarClass, SeatPreference
from .stations import get_station_code
from .captcha import CaptchaManager

logger = logging.getLogger(__name__)


class BookingStatus(Enum):
    """訂票狀態"""
    INIT = "init"
    SEARCHING = "searching"
    SELECTING = "selecting"
    CONFIRMING = "confirming"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class BookingResult:
    """訂票結果"""
    status: BookingStatus
    message: str
    booking_code: Optional[str] = None
    train_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class THSRBookingBot:
    """高鐵訂票機器人"""

    # 高鐵訂票網站 URL
    BASE_URL = "https://irs.thsrc.com.tw"
    BOOKING_URL = f"{BASE_URL}/IMINT/"

    # 頁面元素定位器
    LOCATORS = {
        # 訂票首頁
        "start_station": (By.NAME, "selectStartStation"),
        "end_station": (By.NAME, "selectDestinationStation"),
        "booking_method": (By.NAME, "bookingMethod"),
        "travel_date": (By.ID, "toTimeInputField"),
        "travel_time": (By.NAME, "toTimeTable"),
        "adult_ticket": (By.NAME, "ticketPanel:rows:0:ticketAmount"),
        "child_ticket": (By.NAME, "ticketPanel:rows:1:ticketAmount"),
        "senior_ticket": (By.NAME, "ticketPanel:rows:2:ticketAmount"),
        "disabled_ticket": (By.NAME, "ticketPanel:rows:3:ticketAmount"),
        "car_class_standard": (By.ID, "BookingS1Form_tripCon_typesoftrip_0"),
        "car_class_business": (By.ID, "BookingS1Form_tripCon_typesoftrip_1"),
        "seat_prefer_none": (By.ID, "BookingS1Form_tripCon_seatCon_0"),
        "seat_prefer_window": (By.ID, "BookingS1Form_tripCon_seatCon_1"),
        "seat_prefer_aisle": (By.ID, "BookingS1Form_tripCon_seatCon_2"),
        "captcha_image": (By.ID, "BookingS1Form_homeCaptcha_pass498"),
        "captcha_input": (By.ID, "securityCode"),
        "submit_btn": (By.ID, "SubmitButton"),

        # 車次選擇頁
        "train_radios": (By.NAME, "TrainQueryDataViewPanel:TrainGroup"),
        "confirm_train_btn": (By.ID, "SubmitButton"),
        "error_message": (By.CLASS_NAME, "feedbackPanelERROR"),

        # 確認頁面
        "id_input": (By.ID, "idNumber"),
        "phone_input": (By.ID, "mobilePhone"),
        "email_input": (By.ID, "email"),
        "agree_checkbox": (By.ID, "agree"),
        "confirm_submit": (By.ID, "isSubmit"),

        # 結果頁面
        "booking_code": (By.CSS_SELECTOR, ".pnr-code"),
        "ticket_info": (By.CSS_SELECTOR, ".ticket-info"),
    }

    # 時間選項對應表
    TIME_OPTIONS = {
        "00": "1201A", "01": "1230A", "02": "100A", "03": "130A",
        "04": "200A", "05": "230A", "06": "300A", "07": "330A",
        "08": "400A", "09": "430A", "10": "500A", "11": "530A",
        "12": "600A", "13": "630A", "14": "700A", "15": "730A",
        "16": "800A", "17": "830A", "18": "900A", "19": "930A",
        "20": "1000A", "21": "1030A", "22": "1100A", "23": "1130A",
    }

    def __init__(self, config: BookingConfig):
        """
        初始化訂票機器人

        Args:
            config: 訂票配置
        """
        self.config = config
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.captcha_manager = CaptchaManager(use_auto=True)
        self.status = BookingStatus.INIT
        self.retry_count = 0

    def _setup_driver(self):
        """設定 WebDriver"""
        options = Options()

        if self.config.bot_config.headless:
            options.add_argument("--headless")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # 設定 User-Agent
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
        )
        self.wait = WebDriverWait(self.driver, 10)

        logger.info("WebDriver 初始化完成")

    def _wait_for_start_time(self):
        """等待搶票開始時間"""
        start_time_str = self.config.bot_config.start_time
        if not start_time_str:
            return

        start_time = datetime.fromisoformat(start_time_str)
        now = datetime.now()

        if now >= start_time:
            logger.info("已過開始時間，立即開始搶票")
            return

        wait_seconds = (start_time - now).total_seconds()
        logger.info(f"等待 {wait_seconds:.1f} 秒後開始搶票...")

        # 提前 2 秒開始準備
        if wait_seconds > 2:
            time.sleep(wait_seconds - 2)

        # 精確等待
        while datetime.now() < start_time:
            time.sleep(0.01)

        logger.info("開始搶票！")

    def _navigate_to_booking_page(self):
        """前往訂票頁面"""
        logger.info(f"前往訂票頁面: {self.BOOKING_URL}")
        self.driver.get(self.BOOKING_URL)
        time.sleep(2)

        # 處理「個人資料使用說明」同意彈窗
        self._handle_privacy_dialog()

    def _handle_privacy_dialog(self):
        """處理個人資料使用說明同意彈窗"""
        try:
            # 嘗試多種方式找到「我同意」按鈕
            agree_button = None

            # 方法1: 使用 XPath 找包含「我同意」文字的按鈕
            try:
                agree_button = self.wait.until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//button[contains(text(), '我同意')] | //a[contains(text(), '我同意')] | //input[@value='我同意']"
                    ))
                )
            except TimeoutException:
                pass

            # 方法2: 使用 CSS 選擇器找按鈕
            if not agree_button:
                try:
                    agree_button = self.driver.find_element(
                        By.CSS_SELECTOR,
                        ".btn-confirm, .btn-primary, button.confirm, .swal2-confirm"
                    )
                except NoSuchElementException:
                    pass

            # 方法3: 找所有按鈕，檢查文字
            if not agree_button:
                try:
                    buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    for btn in buttons:
                        if "同意" in btn.text:
                            agree_button = btn
                            break
                except Exception:
                    pass

            # 點擊按鈕
            if agree_button:
                agree_button.click()
                logger.info("已點擊「我同意」按鈕")
                time.sleep(1)
            else:
                logger.info("未發現同意彈窗，繼續執行")

        except Exception as e:
            logger.warning(f"處理同意彈窗時發生錯誤: {e}")

    def _fill_booking_form(self) -> bool:
        """
        填寫訂票表單

        Returns:
            是否填寫成功
        """
        try:
            ticket = self.config.ticket

            # 選擇出發站
            start_select = Select(
                self.wait.until(EC.presence_of_element_located(
                    self.LOCATORS["start_station"]
                ))
            )
            start_select.select_by_value(get_station_code(ticket.departure_station))
            logger.info(f"已選擇出發站: {ticket.departure_station}")

            # 選擇到達站
            end_select = Select(
                self.driver.find_element(*self.LOCATORS["end_station"])
            )
            end_select.select_by_value(get_station_code(ticket.arrival_station))
            logger.info(f"已選擇到達站: {ticket.arrival_station}")

            # 填寫日期
            date_input = self.driver.find_element(*self.LOCATORS["travel_date"])
            date_input.clear()
            # 格式化日期為 YYYY/MM/DD
            formatted_date = ticket.travel_date.replace("-", "/")
            date_input.send_keys(formatted_date)
            logger.info(f"已填寫日期: {formatted_date}")

            # 選擇時間
            time_select = Select(
                self.driver.find_element(*self.LOCATORS["travel_time"])
            )
            time_hour = ticket.get_time_hour()
            time_value = self.TIME_OPTIONS.get(time_hour, "1201A")
            time_select.select_by_value(time_value)
            logger.info(f"已選擇時間: {ticket.preferred_time}")

            # 選擇票種和數量
            self._select_ticket_count()

            # 選擇車廂類型
            self._select_car_class()

            # 選擇座位偏好
            self._select_seat_preference()

            return True

        except Exception as e:
            logger.error(f"填寫表單失敗: {e}")
            return False

    def _select_ticket_count(self):
        """選擇票種和數量"""
        ticket = self.config.ticket
        count = str(ticket.ticket_count)

        # 根據票種選擇對應的下拉選單
        ticket_type_map = {
            TicketType.ADULT: "adult_ticket",
            TicketType.CHILD: "child_ticket",
            TicketType.SENIOR: "senior_ticket",
            TicketType.DISABLED: "disabled_ticket",
        }

        locator_key = ticket_type_map.get(ticket.ticket_type, "adult_ticket")
        ticket_select = Select(
            self.driver.find_element(*self.LOCATORS[locator_key])
        )
        ticket_select.select_by_value(count)
        logger.info(f"已選擇票種: {ticket.ticket_type.value}, 數量: {count}")

    def _select_car_class(self):
        """選擇車廂類型"""
        car_class = self.config.ticket.car_class

        if car_class == CarClass.BUSINESS:
            element = self.driver.find_element(*self.LOCATORS["car_class_business"])
        else:
            element = self.driver.find_element(*self.LOCATORS["car_class_standard"])

        element.click()
        logger.info(f"已選擇車廂: {car_class.value}")

    def _select_seat_preference(self):
        """選擇座位偏好"""
        seat_pref = self.config.ticket.seat_preference

        locator_map = {
            SeatPreference.NONE: "seat_prefer_none",
            SeatPreference.WINDOW: "seat_prefer_window",
            SeatPreference.AISLE: "seat_prefer_aisle",
        }

        locator_key = locator_map.get(seat_pref, "seat_prefer_none")
        element = self.driver.find_element(*self.LOCATORS[locator_key])
        element.click()
        logger.info(f"已選擇座位偏好: {seat_pref.value}")

    def _solve_captcha(self) -> bool:
        """
        解析並輸入驗證碼

        Returns:
            是否成功
        """
        try:
            # 取得驗證碼圖片
            captcha_img = self.wait.until(
                EC.presence_of_element_located(self.LOCATORS["captcha_image"])
            )

            # 截取驗證碼圖片
            captcha_data = captcha_img.screenshot_as_png

            # 解析驗證碼
            captcha_text = self.captcha_manager.solve(captcha_data)
            logger.info(f"驗證碼: {captcha_text}")

            # 輸入驗證碼
            captcha_input = self.driver.find_element(*self.LOCATORS["captcha_input"])
            captcha_input.clear()
            captcha_input.send_keys(captcha_text)

            return True

        except Exception as e:
            logger.error(f"驗證碼處理失敗: {e}")
            return False

    def _submit_booking_form(self) -> bool:
        """
        提交訂票表單

        Returns:
            是否成功（進入車次選擇頁面）
        """
        try:
            submit_btn = self.driver.find_element(*self.LOCATORS["submit_btn"])
            submit_btn.click()
            logger.info("已提交訂票表單")

            # 等待頁面載入
            time.sleep(2)

            # 檢查是否有錯誤訊息
            try:
                error_elem = self.driver.find_element(*self.LOCATORS["error_message"])
                error_text = error_elem.text
                logger.warning(f"訂票表單錯誤: {error_text}")
                return False
            except NoSuchElementException:
                pass

            # 檢查是否進入車次選擇頁面
            try:
                self.wait.until(
                    EC.presence_of_element_located(self.LOCATORS["train_radios"])
                )
                logger.info("成功進入車次選擇頁面")
                return True
            except TimeoutException:
                logger.warning("未能進入車次選擇頁面")
                return False

        except Exception as e:
            logger.error(f"提交表單失敗: {e}")
            return False

    def _select_train(self) -> Optional[Dict[str, Any]]:
        """
        選擇車次

        Returns:
            選擇的車次資訊
        """
        try:
            # 取得所有車次選項
            train_radios = self.driver.find_elements(*self.LOCATORS["train_radios"])

            if not train_radios:
                logger.warning("沒有找到可用車次")
                return None

            # 選擇第一個可用車次
            train_radios[0].click()
            logger.info("已選擇車次")

            # 取得車次資訊（從頁面解析）
            train_info = self._parse_train_info()

            # 點擊確認按鈕
            confirm_btn = self.driver.find_element(*self.LOCATORS["confirm_train_btn"])
            confirm_btn.click()
            logger.info("已確認車次選擇")

            time.sleep(2)
            return train_info

        except Exception as e:
            logger.error(f"選擇車次失敗: {e}")
            return None

    def _parse_train_info(self) -> Dict[str, Any]:
        """解析車次資訊"""
        # 簡化版本，實際需要從頁面解析
        return {
            "departure_station": self.config.ticket.departure_station,
            "arrival_station": self.config.ticket.arrival_station,
            "travel_date": self.config.ticket.travel_date,
        }

    def _fill_passenger_info(self) -> bool:
        """
        填寫乘客資訊

        Returns:
            是否成功
        """
        try:
            passenger = self.config.passenger

            # 填寫身分證字號
            id_input = self.wait.until(
                EC.presence_of_element_located(self.LOCATORS["id_input"])
            )
            id_input.clear()
            id_input.send_keys(passenger.id_number)
            logger.info("已填寫身分證字號")

            # 填寫手機號碼
            phone_input = self.driver.find_element(*self.LOCATORS["phone_input"])
            phone_input.clear()
            phone_input.send_keys(passenger.phone)
            logger.info("已填寫手機號碼")

            # 填寫 Email（如果有）
            if passenger.email:
                try:
                    email_input = self.driver.find_element(*self.LOCATORS["email_input"])
                    email_input.clear()
                    email_input.send_keys(passenger.email)
                    logger.info("已填寫 Email")
                except NoSuchElementException:
                    pass

            return True

        except Exception as e:
            logger.error(f"填寫乘客資訊失敗: {e}")
            return False

    def _confirm_booking(self) -> Optional[str]:
        """
        確認訂票

        Returns:
            訂票代碼
        """
        try:
            # 勾選同意條款
            try:
                agree_checkbox = self.driver.find_element(*self.LOCATORS["agree_checkbox"])
                if not agree_checkbox.is_selected():
                    agree_checkbox.click()
                    logger.info("已勾選同意條款")
            except NoSuchElementException:
                pass

            # 點擊確認按鈕
            confirm_btn = self.driver.find_element(*self.LOCATORS["confirm_submit"])
            confirm_btn.click()
            logger.info("已提交訂票確認")

            # 等待結果頁面
            time.sleep(3)

            # 取得訂票代碼
            try:
                booking_code_elem = self.wait.until(
                    EC.presence_of_element_located(self.LOCATORS["booking_code"])
                )
                booking_code = booking_code_elem.text.strip()
                logger.info(f"訂票成功！訂票代碼: {booking_code}")
                return booking_code
            except TimeoutException:
                logger.error("無法取得訂票代碼")
                return None

        except Exception as e:
            logger.error(f"確認訂票失敗: {e}")
            return None

    def _send_notification(self, result: BookingResult):
        """發送通知"""
        webhook_url = self.config.bot_config.notification_url
        if not webhook_url:
            return

        try:
            payload = {
                "status": result.status.value,
                "message": result.message,
                "booking_code": result.booking_code,
                "train_info": result.train_info,
                "timestamp": datetime.now().isoformat()
            }
            response = requests.post(webhook_url, json=payload, timeout=10)
            logger.info(f"通知發送成功: {response.status_code}")
        except Exception as e:
            logger.error(f"通知發送失敗: {e}")

    def run(self) -> BookingResult:
        """
        執行訂票流程

        Returns:
            訂票結果
        """
        try:
            logger.info("=" * 50)
            logger.info("高鐵搶票機器人啟動")
            logger.info("=" * 50)

            # 初始化 WebDriver
            self._setup_driver()

            # 等待開始時間
            self._wait_for_start_time()

            max_retries = self.config.bot_config.max_retries
            retry_interval = self.config.bot_config.get_retry_interval_seconds()

            while self.retry_count < max_retries:
                self.retry_count += 1
                logger.info(f"第 {self.retry_count} 次嘗試")

                # 前往訂票頁面
                self._navigate_to_booking_page()
                self.status = BookingStatus.SEARCHING

                # 填寫表單
                if not self._fill_booking_form():
                    logger.warning("填寫表單失敗，重試中...")
                    time.sleep(retry_interval)
                    continue

                # 處理驗證碼
                if not self._solve_captcha():
                    logger.warning("驗證碼處理失敗，重試中...")
                    time.sleep(retry_interval)
                    continue

                # 提交表單
                if not self._submit_booking_form():
                    logger.warning("提交表單失敗，重試中...")
                    time.sleep(retry_interval)
                    continue

                self.status = BookingStatus.SELECTING

                # 選擇車次
                train_info = self._select_train()
                if not train_info:
                    logger.warning("選擇車次失敗，重試中...")
                    time.sleep(retry_interval)
                    continue

                self.status = BookingStatus.CONFIRMING

                # 填寫乘客資訊
                if not self._fill_passenger_info():
                    logger.warning("填寫乘客資訊失敗，重試中...")
                    time.sleep(retry_interval)
                    continue

                # 確認訂票
                booking_code = self._confirm_booking()
                if booking_code:
                    self.status = BookingStatus.SUCCESS
                    result = BookingResult(
                        status=BookingStatus.SUCCESS,
                        message="訂票成功！",
                        booking_code=booking_code,
                        train_info=train_info
                    )
                    self._send_notification(result)
                    return result

                time.sleep(retry_interval)

            # 超過最大重試次數
            self.status = BookingStatus.FAILED
            result = BookingResult(
                status=BookingStatus.FAILED,
                message=f"訂票失敗：已重試 {max_retries} 次",
                error="Max retries exceeded"
            )
            self._send_notification(result)
            return result

        except Exception as e:
            logger.error(f"訂票過程發生錯誤: {e}")
            self.status = BookingStatus.FAILED
            result = BookingResult(
                status=BookingStatus.FAILED,
                message=f"訂票失敗：{str(e)}",
                error=str(e)
            )
            self._send_notification(result)
            return result

        finally:
            self.close()

    def close(self):
        """關閉瀏覽器"""
        if self.driver:
            self.driver.quit()
            logger.info("瀏覽器已關閉")
