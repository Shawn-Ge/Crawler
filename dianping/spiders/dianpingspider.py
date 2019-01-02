# -*- coding: utf-8 -*-

'''
Created on 2018年10月29日

@author: geshaowei
'''

import scrapy
import re
from lxml import etree

from ..items import DianpingItem
from .urlcode import genUrl
from ..toolkit import IdManager


class DianpingSpider(scrapy.Spider):
    # 大众点评爬虫
    name = 'dianping'
    allowed_domains = ['www.dianping.com']
#    _thread_ = 0
    def __init__(self):
        # 重写构造函数,添加self._meta_属性
        super().__init__()
        # self._meta_中会被写入shopId,shutdown
        self._meta_ = {}
        self.shutdown = False
        self._meta_['selenium'] = True
        self.conn = IdManager()
        
        
    def start_requests(self):
        # 是否爬取列名页面
        crawlList = False
        if crawlList:
            # 爬取列表页面
            URL = genUrl()
            for url in URL:
                request = scrapy.Request(url, callback=self.parseList)
                yield request
        else:
            # 爬取商铺页面
            while not self.shutdown:
                try:
                    # 从数据库中提取商铺ID
                    id_ = self.conn.lockId(
                        'stars > 0', 
#                        'n = 1',                # 相同店名及地址出现次数
                        'consumption_per_capita IS NOT NULL', 
                        'lon IS NULL', 
                        'lat IS NULL'
                        )
                    url = r'http://www.dianping.com/shop/{}'.format(id_)
                    request = scrapy.Request(url, callback=self.parseShop)
                    request.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36'
                    request.meta['shopId'] = id_        # request携带商铺ID(无需解析URL)
                    print('准备爬取商铺({})...'.format(id_))
                    yield request
                except StopIteration:
                    print('没有合适ID,爬取结束...')
                    self.shutdown = True
                    
    
    def releaseId(self, request, val=0):
        # 释放改request指定的id(传入response也行)
        id_ = request.meta.get('shopId', None)
        if id_:
            self.conn.releaseId(id_, val)
            
    
    def parseList(self, response):
        '''
        # 解析商铺列表页面,核心目的是为了获取商铺ID,顺便获取商铺的一些基本信息
        # 此解析函数是基于scrapy库的HtmlResponse实例
        '''
        # 商铺列表页面提取下一页按钮
        nextPage = response.xpath('//div[@class="page"]/a[@class="next"]').extract()
        if nextPage:
            e = etree.HTML(nextPage[0])
            nextUrl = e.xpath('//a')[0].attrib['href']
            yield scrapy.Request(nextUrl, callback=self.parseList)
        
        # 直接在商铺列表页面获取商铺信息
        SHOP = response.xpath('//div[@id="shop-all-list"]/ul/li/div[@class="txt"]')
        for shop in SHOP:
            # 获取ID
            _id_ = shop.xpath('./div[@class="tit"]/a[@data-hippo-type]').extract()[0]
            def f(html):
                e = etree.HTML(html)
                return e.xpath('//a')[0].attrib['data-shopid']
            id_ = f(_id_)
            # 获取店名
            name = shop.xpath('./div[@class="tit"]//h4/text()').extract()[0]
            # 点评数    -- 不是所有店铺都有这个元素
            _con = shop.xpath('./div[@class="comment"]/a[contains(@onclick, "shopreview")]/b/text()').extract()
            con = _con[0] if _con else None
            # 人均消费    -- 不是所有店铺都有这个元素
            _cpc = shop.xpath('./div[@class="comment"]/a[contains(text(), "人均")]/b/text()').extract()
            cpc = _cpc[0][1:] if _cpc else None       # 去人民币标志
            # 地址
            addr = shop.xpath('./div[@class="tag-addr"]//span[@class="addr"]/text()').extract()[0]
            # 商铺类型以及区域标签
            type_, tag = shop.xpath('./div[@class="tag-addr"]//span[@class="tag"]/text()').extract()[:2]
            # 星数
            _stars = shop.xpath('./div[@class="comment"]/span[contains(@class, "sml-rank-stars sml-str")]').extract()[0]
            def g(html):
                e = etree.HTML(html)
                s = e.xpath('//span')[0].attrib['class']
                if s[-2] == 'r':
                    return s[-1]
                else:
                    return s[-2:]
            stars = g(_stars)
            # 口味、环境、服务    -- 不是所有店铺都有这个元素
            _fla = shop.xpath('.//span[contains(text(), "口味")]/b/text()').extract()
            _env = shop.xpath('.//span[contains(text(), "环境")]/b/text()').extract()
            _ser = shop.xpath('.//span[contains(text(), "服务")]/b/text()').extract()
            fla = _fla[0] if _fla else None
            env = _env[0] if _env else None
            ser = _ser[0] if _ser else None
            # 记录数据
            item = DianpingItem()
            item['ID'] = id_
            item['NAME'] = name
            item['ADDRESS'] = addr
            item['TYPE'] = type_
            item['TAG'] = tag
            item['COMMENTS_N'] = con
            item['CPC'] = cpc
            item['STARS'] = stars
            item['FLA'] = fla
            item['ENV'] = env
            item['SER'] = ser
            yield item
        
    def parseShop(self, response):
        '''
        # 解析商铺页面(只有key words和坐标没有爬取)
        # 用来抓取坐标,用户评论关键词
        # 此解析函数是基于lxml的HTML类实例
        '''
        # 直接转换成lxml库的HTML对象
        html = etree.HTML(response.text)
        
        # 获取信息标签script,用来截取坐标信息
        script_ELE = html.xpath('//script[contains(text(), "shopGlat") and contains(text(), "shopGlng")]')
        if script_ELE:
            # 捕捉到了带有坐标的script标签
            # 截取字符串
            s = script_ELE[0].text
            patLon = re.compile('shopGlng: *" *(\d{3}.\d+) *"')     #考虑到字符串不规范,截取时加入空格
            patLat = re.compile('shopGlat: *" *(\d{2}.\d+) *"')
            lon = float(patLon.findall(s)[0])
            lat = float(patLat.findall(s)[0])
        
        else:
            lon = lat = None
            
        # 获取用户评论关键词
        KWS = html.xpath('//div[@id="summaryfilter-wrapper"]//div[@class="content"]/span/a/text()') 
        if KWS:
            kws = '|'.join(KWS)
        else:
            kws = None
        item = DianpingItem()
        item['ID'] = response.meta['shopId']
        item['LON'] = lon
        item['LAT'] = lat
        item['KEY_WORDS'] = kws
        yield item

        
    def parseNewShop(self, response):
        '''
        # 解析内部链接中的商铺
        # 商铺页面目前无法获取点评数等信息
        '''
        # 直接转换成lxml库的HTML对象
        html = etree.HTML(response.text)
        
        # 获取店铺名
        name = html.xpath('//div[@id="basic-info"]/h1[@class="shop-name"]')[0].text.strip()
        id_ = response.url.split(r'/')[-1]
        # 获取信息标签script,用来截取坐标信息
        script_ELE = html.xpath('//script[contains(text(), "shopGlat") and contains(text(), "shopGlng")]')
        if script_ELE:
            # 捕捉到了带有坐标的script标签
            # 截取字符串
            s = script_ELE[0].text
            patLon = re.compile('shopGlng: *" *(\d{3}.\d+) *"')     #考虑到字符串不规范,截取时加入空格
            patLat = re.compile('shopGlat: *" *(\d{2}.\d+) *"')
            lon = float(patLon.findall(s)[0])
            lat = float(patLat.findall(s)[0])
        
        else:
            lon = lat = None
        
        # 通过搜索商铺列表页面来
        url = r'https://www.dianping.com/search/keyword/1/10_{}'.format(name)
