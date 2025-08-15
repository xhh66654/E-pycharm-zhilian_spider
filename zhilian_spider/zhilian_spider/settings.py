# -*- coding: utf-8 -*-

BOT_NAME = "zhilian_spider"

SPIDER_MODULES = ["zhilian_spider.spiders"]
NEWSPIDER_MODULE = "zhilian_spider.spiders"

ROBOTSTXT_OBEY = False

# scrapy-redis 分布式
DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter"
SCHEDULER = "scrapy_redis.scheduler.Scheduler"
SCHEDULER_PERSIST = True

REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379

DOWNLOAD_DELAY = 1

# 使用我们自定义的 Selenium 中间件
DOWNLOADER_MIDDLEWARES = {
    "zhilian_spider.middlewares.ZhilianSeleniumMiddleware": 543,
}

# 输出管道：既写入 Redis 又落盘 JSON
ITEM_PIPELINES = {
    "scrapy_redis.pipelines.RedisPipeline": 300,
    "zhilian_spider.pipelines.SaveToJsonPipeline": 400,
}

# （可选）减少日志噪声
# LOG_LEVEL = "INFO"
