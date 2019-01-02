# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class DianpingItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    ID = scrapy.Field()         # 商铺ID
    NAME = scrapy.Field()       # 商铺名
    ADDRESS = scrapy.Field()    # 商铺地址
    TYPE = scrapy.Field()       # 商铺类型
    TAG = scrapy.Field()        # 区域标签
    COMMENTS_N = scrapy.Field() # 点评数
    CPC = scrapy.Field()        # 人均消费
    STARS = scrapy.Field()      # 星数
    FLA = scrapy.Field()        # 口味评分
    ENV = scrapy.Field()        # 环境评分
    SER = scrapy.Field()        # 服务评分
    LON = scrapy.Field()        # 经度
    LAT = scrapy.Field()        # 纬度
    KEY_WORDS = scrapy.Field()  # 用户评论关键词
    pass
