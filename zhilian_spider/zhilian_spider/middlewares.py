# -*- coding: utf-8 -*-
import os
import time
import base64
import random
from io import BytesIO
from PIL import Image

from scrapy.http import HtmlResponse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class ZhilianSeleniumMiddleware:
    """
    - 负责用 Selenium 打开页面并返回完整 HTML 给 Scrapy。
    - 内置滑块验证码自动识别/拖动（兼容易盾/极验/阿里常见样式）。
    - 支持通过环境变量 CHROME_BINARY 指定 Chrome 可执行文件路径（若你的机器没装 Chrome）。
    """

    def __init__(self):
        chrome_options = Options()

        # 如你需要可视化调试，注释掉下一行
        chrome_options.add_argument("--headless=new")

        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--start-maximized")

        # 模拟手机 UA（保留你最初设置）
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36 Edg/139.0.0.0"
        )
        chrome_options.add_argument(
            "accept=text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
        )
        chrome_options.add_argument("accept-language=zh-CN,zh;q=0.9,en;q=0.8")

        # 如果你的系统没有安装 Chrome，可在系统环境变量里设置 CHROME_BINARY 指向 chrome.exe
        chrome_binary = os.environ.get("CHROME_BINARY")
        if chrome_binary and os.path.exists(chrome_binary):
            chrome_options.binary_location = chrome_binary

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 12)

        # 先打开首页后再加必要 Cookie（保留你的最初思路）
        try:
            self.driver.get("https://www.zhaopin.com")
            time.sleep(1.5)
            for ck in [
                {"name": "_uab_collina", "value": "175524994865435943478859"},
                {"name": "x-zp-client-id", "value": "b52578f2-8e37-4914-9a18-579451bbe449"},
            ]:
                try:
                    self.driver.add_cookie(ck)
                except Exception:
                    pass
        except Exception:
            pass

    def process_request(self, request, spider):
        spider.logger.info(f"[Selenium] 打开: {request.url}")
        self.driver.get(request.url)

        # 如遇到滑块验证码，先处理
        self.try_solve_any_slider(spider)

        # 等待列表元素出现（最多等 10 秒）
        try:
            self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[class*="joblist"] article, div.joblist-box__item'))
            )
        except Exception:
            spider.logger.warning("等待职位元素超时，但仍返回当前源码以便调试。")

        html = self.driver.page_source

        # 同时在项目根目录写一个 debug.html 便于核对
        try:
            with open("debug.html", "w", encoding="utf-8") as f:
                f.write(html)
        except Exception:
            pass

        return HtmlResponse(
            url=self.driver.current_url, body=html, encoding="utf-8", request=request
        )

    # ===== 滑块验证码相关 =====
    def try_solve_any_slider(self, spider):
        """
        尝试识别常见三类滑块：
        - 网易易盾（class 含 yidun）
        - 极验（class 含 geetest）
        - 阿里 noCaptcha（class 含 nc_ / btn_slide）
        """
        solved = False
        try:
            # 阿里 noCaptcha 常见滑块按钮
            if self._exists((By.CSS_SELECTOR, ".nc_iconfont.btn_slide, .nc_slider, #nc_1_n1z")):
                spider.logger.info("检测到滑块（AliYun noCaptcha），开始拖动...")
                self.drag_slider_by_distance_css(
                    button_selector=".nc_iconfont.btn_slide, .nc_slider, #nc_1_n1z",
                    distance= self._guess_distance()
                )
                solved = True
        except Exception:
            pass

        if not solved:
            try:
                # 网易易盾
                if self._exists((By.CSS_SELECTOR, ".yidun_bg-img, .yidun_jigsaw")):
                    spider.logger.info("检测到滑块（Yidun），开始识别缺口并拖动...")
                    distance = self._calc_gap_distance_by_images(
                        bg_selector=".yidun_bg-img", piece_selector=".yidun_jigsaw"
                    )
                    self.drag_slider_by_distance_css(
                        button_selector=".yidun_slider, .yidun_control, .yidun_slider__bar, .yidun_slider__button",
                        distance=distance
                    )
                    solved = True
            except Exception:
                pass

        if not solved:
            try:
                # 极验（新版大多是 canvas，这里做一个估算拖动）
                if self._exists((By.CSS_SELECTOR, ".geetest_canvas_bg, .geetest_slider_button")):
                    spider.logger.info("检测到滑块（Geetest），按经验距离拖动...")
                    self.drag_slider_by_distance_css(
                        button_selector=".geetest_slider_button",
                        distance=self._guess_distance()
                    )
                    solved = True
            except Exception:
                pass

        if solved:
            time.sleep(1.5)

    def _exists(self, locator):
        try:
            self.driver.find_element(*locator)
            return True
        except Exception:
            return False

    def drag_slider_by_distance_css(self, button_selector: str, distance: int):
        btn = self.driver.find_element(By.CSS_SELECTOR, button_selector)
        self._human_drag(btn, distance)

    def _human_drag(self, element, distance):
        """拟人化拖动轨迹"""
        ActionChains(self.driver).click_and_hold(element).perform()
        time.sleep(0.25)

        track = self._build_track(distance)
        for step in track:
            ActionChains(self.driver).move_by_offset(xoffset=step, yoffset=random.randint(-1, 1)).perform()
            time.sleep(random.uniform(0.01, 0.03))

        time.sleep(0.12)
        ActionChains(self.driver).release().perform()

    def _build_track(self, distance):
        """前期加速、中期匀速、后期减速，最后略微回拉"""
        track = []
        current = 0
        mid1 = distance * 0.6
        mid2 = distance * 0.9
        while current < distance:
            if current < mid1:
                move = random.randint(6, 10)
            elif current < mid2:
                move = random.randint(3, 6)
            else:
                move = random.randint(1, 3)
            current += move
            if current > distance:
                move -= (current - distance)
                current = distance
            track.append(move)

        # 轻微回拉，模拟人手误差修正
        track += [-1, 1]
        return track

    # ===== 通过图片计算缺口位置（以易盾类为例）=====
    def _calc_gap_distance_by_images(self, bg_selector, piece_selector) -> int:
        bg_el = self.driver.find_element(By.CSS_SELECTOR, bg_selector)
        piece_el = self.driver.find_element(By.CSS_SELECTOR, piece_selector)

        bg_src = bg_el.get_attribute("src")
        piece_src = piece_el.get_attribute("src")

        bg_img = self._to_pil(bg_src)
        piece_img = self._to_pil(piece_src)

        return self._simple_gap_offset(bg_img, piece_img)

    def _to_pil(self, src: str) -> Image.Image:
        if not src:
            raise ValueError("图片 src 为空")
        if "base64," in src:
            src = src.split("base64,")[1]
        raw = base64.b64decode(src)
        return Image.open(BytesIO(raw)).convert("L")

    def _simple_gap_offset(self, bg: Image.Image, piece: Image.Image) -> int:
        """非常简化的像素差法：返回缺口大致 x 坐标"""
        bg_w, bg_h = bg.size
        piece = piece.resize(bg.size)  # 粗暴对齐尺寸，足够估算
        threshold = 50

        for x in range(5, bg_w - 5):
            diff_cnt = 0
            for y in range(5, bg_h - 5):
                if abs(bg.getpixel((x, y)) - piece.getpixel((x, y))) > threshold:
                    diff_cnt += 1
            if diff_cnt > bg_h * 0.25:
                return max(30, x - 10)  # 留一点冗余
        return self._guess_distance()

    def _guess_distance(self) -> int:
        """猜一个通用距离，很多滑块在 120~200 之间"""
        return random.randint(130, 180)

    def __del__(self):
        try:
            self.driver.quit()
        except Exception:
            pass
