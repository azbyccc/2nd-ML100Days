"""
高鐵訂票核心邏輯 (新版網站)
THSR Booking Core Logic (New Website Version)
"""

import logging
import time
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException
)

from .config import BookingConfig, TicketType, CarClass, SeatPreference
from .stations import get_station_code, STATIONS
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
    """高鐵訂票機器人 (適配新版網站)"""

    # 高鐵訂票網站 URL
    BASE_URL = "https://irs.thsrc.com.tw"
    BOOKING_URL = f"{BASE_URL}/IMINT/"

    # 車站名稱對應（用於點擊選擇）
    STATION_NAMES = [
        "南港", "台北", "板橋", "桃園", "新竹",
        "苗栗", "台中", "彰化", "雲林", "嘉義",
        "台南", "左營"
    ]

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
            options.add_argument("--headless=new")

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
        self.wait = WebDriverWait(self.driver, 15)

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
        time.sleep(3)

        # 處理「個人資料使用說明」同意彈窗
        self._handle_privacy_dialog()

    def _handle_privacy_dialog(self):
        """處理個人資料使用說明同意彈窗"""
        try:
            # 等待彈窗出現
            time.sleep(1)

            # 嘗試多種方式找到「我同意」按鈕
            agree_selectors = [
                "//button[contains(text(), '我同意')]",
                "//button[contains(@class, 'confirm')]",
                "//button[contains(@class, 'primary')]",
                "//div[contains(@class, 'modal')]//button",
                "//button[contains(@class, 'swal2-confirm')]",
            ]

            for selector in agree_selectors:
                try:
                    agree_button = self.driver.find_element(By.XPATH, selector)
                    if agree_button.is_displayed():
                        agree_button.click()
                        logger.info("已點擊「我同意」按鈕")
                        time.sleep(1)
                        return
                except NoSuchElementException:
                    continue

            # 嘗試找所有按鈕
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                try:
                    if "同意" in btn.text and btn.is_displayed():
                        btn.click()
                        logger.info("已點擊同意按鈕")
                        time.sleep(1)
                        return
                except:
                    continue

            logger.info("未發現同意彈窗或已自動關閉")

        except Exception as e:
            logger.warning(f"處理同意彈窗時發生錯誤: {e}")

    def _click_element_by_text(self, text: str, tag: str = "*") -> bool:
        """透過文字內容點擊元素"""
        try:
            element = self.driver.find_element(
                By.XPATH, f"//{tag}[contains(text(), '{text}')]"
            )
            element.click()
            return True
        except NoSuchElementException:
            return False

    def _select_station(self, station_type: str, station_name: str) -> bool:
        """
        選擇車站（新版網站使用下拉選單）

        Args:
            station_type: "departure" 或 "arrival"
            station_name: 車站名稱
        """
        try:
            # 找到對應的選擇器
            if station_type == "departure":
                # 點擊出發站選擇器
                selectors = [
                    "//div[contains(text(), '出發站')]/..//div[contains(text(), '請選擇')]",
                    "//div[contains(text(), '出發站')]/following-sibling::div",
                    "(//div[contains(@class, 'station-selector')])[1]",
                    "//input[@placeholder='出發站']",
                    "(//div[contains(@class, 'select')])[1]",
                ]
            else:
                # 點擊到達站選擇器
                selectors = [
                    "//div[contains(text(), '到達站')]/..//div[contains(text(), '請選擇')]",
                    "//div[contains(text(), '到達站')]/following-sibling::div",
                    "(//div[contains(@class, 'station-selector')])[2]",
                    "//input[@placeholder='到達站']",
                    "(//div[contains(@class, 'select')])[2]",
                ]

            # 嘗試點擊選擇器
            clicked = False
            for selector in selectors:
                try:
                    element = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    element.click()
                    clicked = True
                    logger.info(f"已點擊{station_type}站選擇器")
                    time.sleep(0.5)
                    break
                except:
                    continue

            if not clicked:
                # 嘗試用更通用的方式
                all_divs = self.driver.find_elements(By.TAG_NAME, "div")
                for div in all_divs:
                    try:
                        if "請選擇" in div.text and div.is_displayed():
                            div.click()
                            clicked = True
                            time.sleep(0.5)
                            break
                    except:
                        continue

            if not clicked:
                logger.error(f"無法點擊{station_type}站選擇器")
                return False

            # 等待下拉選單出現並選擇車站
            time.sleep(0.5)

            # 嘗試點擊車站選項
            station_selectors = [
                f"//li[contains(text(), '{station_name}')]",
                f"//div[contains(text(), '{station_name}')]",
                f"//span[contains(text(), '{station_name}')]",
                f"//button[contains(text(), '{station_name}')]",
                f"//*[text()='{station_name}']",
            ]

            for selector in station_selectors:
                try:
                    station_element = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    station_element.click()
                    logger.info(f"已選擇{station_type}站: {station_name}")
                    time.sleep(0.5)
                    return True
                except:
                    continue

            logger.error(f"無法選擇{station_type}站: {station_name}")
            return False

        except Exception as e:
            logger.error(f"選擇車站失敗: {e}")
            return False

    def _select_date(self) -> bool:
        """選擇乘車日期"""
        try:
            travel_date = self.config.ticket.travel_date

            # 嘗試找到日期選擇器
            date_selectors = [
                "//div[contains(text(), '出發日期')]/following-sibling::div",
                "//input[@type='date']",
                "//div[contains(@class, 'date')]//input",
                "//div[contains(text(), '出發日期')]/..//input",
            ]

            for selector in date_selectors:
                try:
                    date_element = self.driver.find_element(By.XPATH, selector)
                    date_element.click()
                    time.sleep(0.5)

                    # 清除並輸入日期
                    date_element.send_keys(Keys.CONTROL + "a")
                    date_element.send_keys(travel_date.replace("-", "/"))
                    logger.info(f"已選擇日期: {travel_date}")
                    return True
                except:
                    continue

            # 如果找不到輸入框，可能需要用日曆選擇器
            logger.warning("使用預設日期")
            return True

        except Exception as e:
            logger.error(f"選擇日期失敗: {e}")
            return False

    def _select_time(self) -> bool:
        """選擇出發時間"""
        try:
            preferred_time = self.config.ticket.preferred_time

            # 嘗試找到時間選擇器
            time_selectors = [
                "//div[contains(text(), '出發時間')]/..//div[contains(text(), '請選擇')]",
                "//div[contains(text(), '出發時間')]/following-sibling::div",
                "(//div[contains(@class, 'time-selector')])",
            ]

            clicked = False
            for selector in time_selectors:
                try:
                    time_element = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    time_element.click()
                    clicked = True
                    time.sleep(0.5)
                    break
                except:
                    continue

            if clicked:
                # 選擇對應的時間
                hour = int(preferred_time.split(":")[0])
                # 轉換為高鐵時間選項格式
                time_options = [
                    f"{hour:02d}:00", f"{hour}:00",
                    f"{hour:02d}:30", f"{hour}:30"
                ]

                for time_opt in time_options:
                    try:
                        time_option = self.driver.find_element(
                            By.XPATH, f"//*[contains(text(), '{time_opt}')]"
                        )
                        time_option.click()
                        logger.info(f"已選擇時間: {time_opt}")
                        return True
                    except:
                        continue

            logger.warning("使用預設時間")
            return True

        except Exception as e:
            logger.error(f"選擇時間失敗: {e}")
            return True  # 時間選擇失敗不影響繼續

    def _select_ticket_count(self) -> bool:
        """選擇票數"""
        try:
            ticket_count = self.config.ticket.ticket_count
            ticket_type = self.config.ticket.ticket_type

            # 票種對應的標籤文字
            type_labels = {
                TicketType.ADULT: "全票",
                TicketType.CHILD: "孩童票",
                TicketType.SENIOR: "敬老票",
                TicketType.DISABLED: "愛心票",
            }

            label = type_labels.get(ticket_type, "全票")

            # 找到對應的數量選擇器
            # 新版網站可能使用 +/- 按鈕或下拉選單
            try:
                # 嘗試找到數量輸入框或選擇器
                count_element = self.driver.find_element(
                    By.XPATH, f"//div[contains(text(), '{label}')]/..//input"
                )
                count_element.clear()
                count_element.send_keys(str(ticket_count))
                logger.info(f"已選擇票數: {label} x {ticket_count}")
                return True
            except:
                pass

            # 嘗試使用 + 按鈕增加數量
            try:
                for _ in range(ticket_count - 1):  # 預設已經是 1
                    plus_btn = self.driver.find_element(
                        By.XPATH, f"//div[contains(text(), '{label}')]/..//button[contains(text(), '+')]"
                    )
                    plus_btn.click()
                    time.sleep(0.2)
                logger.info(f"已選擇票數: {label} x {ticket_count}")
                return True
            except:
                pass

            logger.warning("使用預設票數")
            return True

        except Exception as e:
            logger.error(f"選擇票數失敗: {e}")
            return True

    def _input_captcha(self) -> bool:
        """輸入驗證碼"""
        try:
            # 找到驗證碼圖片
            captcha_img_selectors = [
                "//img[contains(@src, 'captcha')]",
                "//img[contains(@alt, '驗證碼')]",
                "//div[contains(@class, 'captcha')]//img",
                "//img[contains(@class, 'captcha')]",
            ]

            captcha_img = None
            for selector in captcha_img_selectors:
                try:
                    captcha_img = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    break
                except:
                    continue

            if not captcha_img:
                # 嘗試找所有圖片
                images = self.driver.find_elements(By.TAG_NAME, "img")
                for img in images:
                    src = img.get_attribute("src") or ""
                    if "captcha" in src.lower() or "security" in src.lower():
                        captcha_img = img
                        break

            if not captcha_img:
                logger.error("找不到驗證碼圖片")
                return False

            # 截取驗證碼圖片
            captcha_data = captcha_img.screenshot_as_png

            # 解析驗證碼
            captcha_text = self.captcha_manager.solve(captcha_data)
            logger.info(f"驗證碼: {captcha_text}")

            # 找到驗證碼輸入框
            captcha_input_selectors = [
                "//input[contains(@placeholder, '驗證碼')]",
                "//input[contains(@name, 'captcha')]",
                "//input[contains(@id, 'captcha')]",
                "//input[contains(@id, 'security')]",
                "//div[contains(@class, 'captcha')]//input",
            ]

            captcha_input = None
            for selector in captcha_input_selectors:
                try:
                    captcha_input = self.driver.find_element(By.XPATH, selector)
                    break
                except:
                    continue

            if not captcha_input:
                # 找圖片旁邊的輸入框
                inputs = self.driver.find_elements(By.TAG_NAME, "input")
                for inp in inputs:
                    input_type = inp.get_attribute("type") or ""
                    if input_type == "text" and inp.is_displayed():
                        placeholder = inp.get_attribute("placeholder") or ""
                        if "驗證" in placeholder or "輸入" in placeholder:
                            captcha_input = inp
                            break

            if captcha_input:
                captcha_input.clear()
                captcha_input.send_keys(captcha_text)
                logger.info("已輸入驗證碼")
                return True
            else:
                logger.error("找不到驗證碼輸入框")
                return False

        except Exception as e:
            logger.error(f"驗證碼處理失敗: {e}")
            return False

    def _fill_booking_form(self) -> bool:
        """填寫訂票表單（新版網站）"""
        try:
            ticket = self.config.ticket

            # 1. 選擇出發站
            logger.info("正在選擇出發站...")
            if not self._select_station("departure", ticket.departure_station):
                return False
            time.sleep(0.5)

            # 2. 選擇到達站
            logger.info("正在選擇到達站...")
            if not self._select_station("arrival", ticket.arrival_station):
                return False
            time.sleep(0.5)

            # 3. 選擇日期
            logger.info("正在選擇日期...")
            self._select_date()
            time.sleep(0.5)

            # 4. 選擇時間
            logger.info("正在選擇時間...")
            self._select_time()
            time.sleep(0.5)

            # 5. 選擇票數
            logger.info("正在選擇票數...")
            self._select_ticket_count()
            time.sleep(0.5)

            # 6. 輸入驗證碼
            logger.info("正在處理驗證碼...")
            if not self._input_captcha():
                return False

            return True

        except Exception as e:
            logger.error(f"填寫表單失敗: {e}")
            return False

    def _submit_booking_form(self) -> bool:
        """提交訂票表單"""
        try:
            # 找到「開始查詢」按鈕
            submit_selectors = [
                "//button[contains(text(), '開始查詢')]",
                "//button[contains(text(), '查詢')]",
                "//button[contains(@class, 'submit')]",
                "//button[contains(@class, 'primary')]",
                "//input[@type='submit']",
            ]

            for selector in submit_selectors:
                try:
                    submit_btn = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    submit_btn.click()
                    logger.info("已點擊「開始查詢」按鈕")
                    time.sleep(3)
                    return True
                except:
                    continue

            # 嘗試找所有按鈕
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                if "查詢" in btn.text and btn.is_displayed():
                    btn.click()
                    logger.info("已點擊查詢按鈕")
                    time.sleep(3)
                    return True

            logger.error("找不到提交按鈕")
            return False

        except Exception as e:
            logger.error(f"提交表單失敗: {e}")
            return False

    def _select_train(self) -> Optional[Dict[str, Any]]:
        """選擇車次"""
        try:
            time.sleep(2)

            # 找到車次列表
            train_selectors = [
                "//input[@type='radio']",
                "//div[contains(@class, 'train-item')]",
                "//tr[contains(@class, 'train')]//input",
            ]

            for selector in train_selectors:
                try:
                    trains = self.driver.find_elements(By.XPATH, selector)
                    if trains:
                        trains[0].click()
                        logger.info("已選擇第一個可用車次")
                        time.sleep(1)
                        break
                except:
                    continue

            # 點擊確認按鈕
            confirm_selectors = [
                "//button[contains(text(), '確認')]",
                "//button[contains(text(), '下一步')]",
                "//input[@type='submit']",
            ]

            for selector in confirm_selectors:
                try:
                    confirm_btn = self.driver.find_element(By.XPATH, selector)
                    if confirm_btn.is_displayed():
                        confirm_btn.click()
                        logger.info("已確認車次選擇")
                        time.sleep(2)
                        break
                except:
                    continue

            return {
                "departure_station": self.config.ticket.departure_station,
                "arrival_station": self.config.ticket.arrival_station,
                "travel_date": self.config.ticket.travel_date,
            }

        except Exception as e:
            logger.error(f"選擇車次失敗: {e}")
            return None

    def _fill_passenger_info(self) -> bool:
        """填寫乘客資訊"""
        try:
            passenger = self.config.passenger

            # 填寫身分證字號
            id_selectors = [
                "//input[contains(@placeholder, '身分證')]",
                "//input[contains(@name, 'id')]",
                "//input[contains(@id, 'id')]",
            ]

            for selector in id_selectors:
                try:
                    id_input = self.driver.find_element(By.XPATH, selector)
                    id_input.clear()
                    id_input.send_keys(passenger.id_number)
                    logger.info("已填寫身分證字號")
                    break
                except:
                    continue

            # 填寫手機號碼
            phone_selectors = [
                "//input[contains(@placeholder, '手機')]",
                "//input[contains(@name, 'phone')]",
                "//input[contains(@name, 'mobile')]",
            ]

            for selector in phone_selectors:
                try:
                    phone_input = self.driver.find_element(By.XPATH, selector)
                    phone_input.clear()
                    phone_input.send_keys(passenger.phone)
                    logger.info("已填寫手機號碼")
                    break
                except:
                    continue

            # 填寫 Email（如果有）
            if passenger.email:
                email_selectors = [
                    "//input[contains(@placeholder, 'email')]",
                    "//input[contains(@type, 'email')]",
                    "//input[contains(@name, 'email')]",
                ]

                for selector in email_selectors:
                    try:
                        email_input = self.driver.find_element(By.XPATH, selector)
                        email_input.clear()
                        email_input.send_keys(passenger.email)
                        logger.info("已填寫 Email")
                        break
                    except:
                        continue

            return True

        except Exception as e:
            logger.error(f"填寫乘客資訊失敗: {e}")
            return False

    def _confirm_booking(self) -> Optional[str]:
        """確認訂票"""
        try:
            # 勾選同意條款
            checkbox_selectors = [
                "//input[@type='checkbox']",
                "//input[contains(@name, 'agree')]",
            ]

            for selector in checkbox_selectors:
                try:
                    checkbox = self.driver.find_element(By.XPATH, selector)
                    if not checkbox.is_selected():
                        checkbox.click()
                        logger.info("已勾選同意條款")
                    break
                except:
                    continue

            # 點擊確認按鈕
            confirm_selectors = [
                "//button[contains(text(), '確認')]",
                "//button[contains(text(), '完成訂票')]",
                "//button[contains(text(), '送出')]",
                "//input[@type='submit']",
            ]

            for selector in confirm_selectors:
                try:
                    confirm_btn = self.driver.find_element(By.XPATH, selector)
                    if confirm_btn.is_displayed():
                        confirm_btn.click()
                        logger.info("已點擊確認按鈕")
                        time.sleep(3)
                        break
                except:
                    continue

            # 嘗試取得訂票代碼
            code_selectors = [
                "//div[contains(@class, 'pnr')]",
                "//span[contains(@class, 'code')]",
                "//*[contains(text(), '訂位代號')]",
            ]

            for selector in code_selectors:
                try:
                    code_element = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    booking_code = code_element.text.strip()
                    if booking_code:
                        logger.info(f"訂票成功！訂票代碼: {booking_code}")
                        return booking_code
                except:
                    continue

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
        """執行訂票流程"""
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
