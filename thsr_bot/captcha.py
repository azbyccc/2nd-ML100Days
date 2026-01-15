"""
驗證碼處理模組
Captcha Handler Module
"""

import base64
import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class CaptchaSolver(ABC):
    """驗證碼解析器基類"""

    @abstractmethod
    def solve(self, image_data: bytes) -> str:
        """
        解析驗證碼

        Args:
            image_data: 驗證碼圖片的 bytes 資料

        Returns:
            辨識出的驗證碼文字
        """
        pass


class ManualCaptchaSolver(CaptchaSolver):
    """手動輸入驗證碼"""

    def solve(self, image_data: bytes) -> str:
        """
        提示使用者手動輸入驗證碼

        Args:
            image_data: 驗證碼圖片資料（未使用）

        Returns:
            使用者輸入的驗證碼
        """
        return input("請輸入驗證碼: ").strip()


class DdddocrSolver(CaptchaSolver):
    """使用 ddddocr 自動辨識驗證碼"""

    def __init__(self):
        try:
            import ddddocr
            self.ocr = ddddocr.DdddOcr(show_ad=False)
            logger.info("ddddocr 初始化成功")
        except ImportError:
            raise ImportError(
                "需要安裝 ddddocr: pip install ddddocr"
            )

    def solve(self, image_data: bytes) -> str:
        """
        使用 ddddocr 辨識驗證碼

        Args:
            image_data: 驗證碼圖片資料

        Returns:
            辨識出的驗證碼
        """
        result = self.ocr.classification(image_data)
        logger.info(f"ddddocr 辨識結果: {result}")
        return result


class TwoCaptchaSolver(CaptchaSolver):
    """使用 2Captcha 服務解析驗證碼"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        try:
            from twocaptcha import TwoCaptcha
            self.solver = TwoCaptcha(api_key)
        except ImportError:
            raise ImportError(
                "需要安裝 2captcha-python: pip install 2captcha-python"
            )

    def solve(self, image_data: bytes) -> str:
        """
        使用 2Captcha 服務解析驗證碼

        Args:
            image_data: 驗證碼圖片資料

        Returns:
            解析出的驗證碼
        """
        # 將圖片轉為 base64
        image_base64 = base64.b64encode(image_data).decode()

        result = self.solver.normal(image_base64)
        logger.info(f"2Captcha 解析結果: {result}")
        return result.get("code", "")


class CaptchaManager:
    """驗證碼管理器"""

    def __init__(
        self,
        use_auto: bool = True,
        two_captcha_key: Optional[str] = None
    ):
        """
        初始化驗證碼管理器

        Args:
            use_auto: 是否嘗試自動辨識
            two_captcha_key: 2Captcha API 金鑰（可選）
        """
        self.solvers: list[CaptchaSolver] = []

        # 優先使用 2Captcha（如果有設定）
        if two_captcha_key:
            try:
                self.solvers.append(TwoCaptchaSolver(two_captcha_key))
                logger.info("已啟用 2Captcha 服務")
            except ImportError as e:
                logger.warning(f"無法啟用 2Captcha: {e}")

        # 嘗試使用 ddddocr
        if use_auto:
            try:
                self.solvers.append(DdddocrSolver())
                logger.info("已啟用 ddddocr 自動辨識")
            except ImportError as e:
                logger.warning(f"無法啟用 ddddocr: {e}")

        # 最後使用手動輸入作為備案
        self.solvers.append(ManualCaptchaSolver())
        logger.info("已啟用手動輸入作為備案")

    def solve(self, image_data: bytes, max_attempts: int = 3) -> str:
        """
        解析驗證碼

        Args:
            image_data: 驗證碼圖片資料
            max_attempts: 最大嘗試次數

        Returns:
            驗證碼文字
        """
        for solver in self.solvers:
            solver_name = solver.__class__.__name__
            logger.info(f"嘗試使用 {solver_name} 解析驗證碼")

            for attempt in range(max_attempts):
                try:
                    result = solver.solve(image_data)
                    if result:
                        logger.info(f"{solver_name} 成功解析: {result}")
                        return result
                except Exception as e:
                    logger.warning(
                        f"{solver_name} 第 {attempt + 1} 次嘗試失敗: {e}"
                    )

            logger.warning(f"{solver_name} 無法解析，嘗試下一個解析器")

        # 所有解析器都失敗
        raise RuntimeError("所有驗證碼解析器都失敗了")
