# -*- coding: utf-8 -*-
import redis
from urllib.parse import quote

if __name__ == "__main__":
    r = redis.Redis(host="127.0.0.1", port=6379, db=0, decode_responses=True)
    # 单条示例
    url = f"https://sou.zhaopin.com/?jl=530&kw={quote('python')}&kt=3&p=1"
    r.lpush("zhilian:start_urls", url)
    print("已推送任务到 Redis 队列:", url)
