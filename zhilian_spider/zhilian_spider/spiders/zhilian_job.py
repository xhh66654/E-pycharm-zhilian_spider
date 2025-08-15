# -*- coding: utf-8 -*-
import scrapy
from scrapy.http import HtmlResponse
from urllib.parse import urlparse, parse_qs


class ZhilianJobSpider(scrapy.Spider):
    """
    说明：
    - 该爬虫默认由 scrapy-redis 驱动，从 Redis 队列 zhilian:start_urls 取 URL。
    - 同时保留 start_urls，便于你本地单机调试（直接 scrapy crawl zhilian_job 也能跑）。
    - 页面实际由 Selenium 中间件渲染，parse 里拿到的是完整 HTML。
    """
    name = "zhilian_job"
    allowed_domains = ["zhaopin.com", "sou.zhaopin.com"]

    # 本地单机调试备用（分布式时会被 scrapy-redis 的调度覆盖）
    start_urls = [
        "https://www.zhaopin.com/sou/jl530/kw01O00U80EG06G03F01N0/p1?kt=3"
    ]

    custom_settings = {
        # 保证使用我们自定义的中间件（也可以统一放到 settings.py）
        "DOWNLOADER_MIDDLEWARES": {
            "zhilian_spider.middlewares.ZhilianSeleniumMiddleware": 543,
        }
    }

    def parse(self, response: HtmlResponse):
        # 保存调试源码（每页会覆盖，可按需改写文件名加上时间戳）
        try:
            with open("debug.html", "w", encoding="utf-8") as f:
                f.write(response.text)
        except Exception as e:
            self.logger.debug(f"写入 debug.html 失败: {e}")

        # 解析（尽量宽松，兼容 PC/M 端样式）
        # 1) 新版列表容器
        job_cards = response.css('div[class*="joblist"] article, div.joblist-box__item')
        if not job_cards:
            # 2) 备用：常见结构
            job_cards = response.css('article, div.joblist-item, li.job-item')

        if not job_cards:
            self.logger.warning("未找到职位列表，请检查选择器或等待 Selenium 完整渲染。")

        for job in job_cards:
            title = (
                job.css('a.joblist-box__title::text').get()
                or job.css('a span::text').get()
                or job.css('a::attr(title)').get()
            )

            company = (
                job.css('a.joblist-box__cname::text').get()
                or job.css('div.company span::text').get()
                or job.css('a[class*="company"]::text').get()
            )

            salary = (
                job.css('p.joblist-box__salary::text').get()
                or job.css('div.job-salary::text').get()
                or job.css('span[class*="salary"]::text').get()
            )

            location = (
                job.css('span.joblist-box__location::text').get()
                or job.css('div.job-location::text').get()
                or job.css('span[class*="city"]::text').get()
            )

            yield {
                "title": (title or "").strip() or None,
                "company": (company or "").strip() or None,
                "salary": (salary or "").strip() or None,
                "location": (location or "").strip() or None,
                "source_url": response.url,
            }

        # 翻页（如果页面存在“下一页”按钮）
        next_btn = response.css('a.btn-next, a[aria-label="下一页"], a.next::attr(href)')
        if next_btn:
            href = next_btn.attrib.get("href") if hasattr(next_btn, "attrib") else next_btn.get()
            if href:
                yield response.follow(href, callback=self.parse)
        else:
            # 兜底：通过 URL 参数自增 p=页码
            try:
                parsed = urlparse(response.url)
                qs = parse_qs(parsed.query)
                p = int((qs.get("p") or ["1"])[0])
                new_p = p + 1
                if "sou.zhaopin.com" in parsed.netloc:
                    base = response.url.split("?")[0]
                    new_q = []
                    for k, v in qs.items():
                        if k == "p":
                            v = [str(new_p)]
                        new_q.append(f"{k}={v[0]}")
                    next_url = f"{base}?{'&'.join(new_q)}"
                    yield response.follow(next_url, callback=self.parse)
            except Exception:
                pass
