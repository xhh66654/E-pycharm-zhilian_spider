# -*- coding: utf-8 -*-
import subprocess
import time
import redis
from urllib.parse import quote
import os


def start_redis():
    """
    启动 Windows Redis（带配置更稳），如果你已手动开着可以不调用。
    """
    redis_path = r"E:\Redis\redis-server.exe"
    conf_path = r"E:\Redis\redis.windows.conf"
    if not os.path.exists(redis_path):
        print(f"[警告] 未找到 Redis 可执行文件：{redis_path}，将尝试直接连接本地 6379。")
        return None

    print("[启动] Redis 服务...")
    args = [redis_path]
    if os.path.exists(conf_path):
        args.append(conf_path)
    return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def add_start_urls():
    """
    向 scrapy-redis 队列推入起始 URL
    """
    print("[添加] 初始 URL 到 Redis...")
    r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

    keywords = ["python", "java", "数据分析"]
    city_codes = {"北京": "530", "上海": "538", "广州": "763", "深圳": "765"}

    for kw in keywords:
        for city_name, city_code in city_codes.items():
            url = f"https://sou.zhaopin.com/?jl={city_code}&kw={quote(kw)}&kt=3&p=1"
            r.lpush("zhilian:start_urls", url)
            print(f"  已添加: {city_name} - {kw} -> {url}")


def start_spider():
    """
    启动爬虫（名称必须与 Spider.name 一致：zhilian_job）
    """
    print("[启动] Scrapy 爬虫...")
    subprocess.call(["scrapy", "crawl", "zhilian_job"])


if __name__ == "__main__":
    redis_process = start_redis()
    time.sleep(2)  # 等 Redis 就绪

    add_start_urls()
    time.sleep(1)

    start_spider()

    # 如你手动启动的 Redis，这里可以注释
    if redis_process:
        redis_process.terminate()
