# -*- coding: utf-8 -*-

# Define here the models for your spider middleware
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/spider-middleware.html



from scrapy import signals
from scrapy.exceptions import IgnoreRequest

from .webdriver import Chrome
from .toolkit import ProxyManager, httpStatus



class SeleniumMiddleware:
    # Selenium下载器中间件,主要作用是启用Selenium的浏览器驱动,同时还能随机设置代理(无论是否使用浏览器驱动)
    @classmethod
    def from_crawler(cls, crawler):
        # 获取数据库内维持存活代理的数量
        n = crawler.settings.get('PROXY_N', 1)
        # 创建实例
        s = cls(n)
        return s
    
    def __init__(self, n):
        # 记录默认代理池存活代理数量(为0时表示允许不用代理)
        self.proxyN = n
        # 创建MySQL数据库ippool表连接通道
        self.proxyManager = ProxyManager(n)
        # 检查数据库代理表
        self.proxyManager.refleshProxy()

        
    def process_request(self, request, spider):
        '''
        # Selenium下载器中间件
        # 主要功能有:1.启动无头Chrome浏览器, 2.检查代理是否存活并设置代理, 3.
        '''
        # 从MySQL数据库中获取代理IP
        proxy = self.proxyManager.getProxy()
        # 对request对象进行代理变更
        request.meta['proxy'] = proxy
        if not spider._meta_.get('selenium', False):
            # spider没有指定需要使用selenium,必须返回None
            return None
        
        if proxy is None and self.proxyN > 0:
            # 如果代理池空了,但是却又指定需要使用代理(settings.PROXY_N > 0),则关闭爬虫
            # 释放ID编辑锁(lock_=0)
            spider.releaseId(request, 0)
            # 给spider传入关闭指令
            spider.shutdown = True
            # 忽略这个request
            raise IgnoreRequest
        
        else:
            # 包括成功获取代理或者允许不用代理
            browser = request.meta.get('browser', Chrome(request, proxy))
            browser.get(r'http://www.dianping.com/')    # 先打开点评首页(降低被BAN的概率)
            
            # 把浏览器下载到的数据转换成scrapy.HtmlResponse实例
            response = browser.download(request, httpStatus)
            # 默认必须关闭浏览器,如果指定了浏览器不需要关闭,需要重写borwser.quit()方法
            browser.quit()
                
            # 检查这个url是否有效
            if response.status==200:
                # 当HTTP状态码为200时,才正常返回response
                return response
            
            else:
                # 该代理出现可能被查封的情况
                # 释放使用计数
                self.proxyManager.flushProxyInUsing(proxy, -1)
                # 代理扣分(ban_by_dianping+1)
                self.proxyManager.flushProxyScore(proxy, -1)
                # 检查数据库代理表
                self.proxyManager.refleshProxy()
                # 释放ID编辑锁(lock_=0)
                spider.releaseId(request, 0)       # 到这一步一般IP已经挂了
                # 重新返回request
                return request

    
    def process_response(self, request, response, spider):
        '# 在成功获取一个Response之后,给该代理加分,并且释放该代理的使用计数'
        proxy = request.meta['proxy']
        if proxy:
            # 释放使用计数
            self.proxyManager.flushProxyInUsing(proxy, -1)
            # 代理加分(score+1)
            self.proxyManager.flushProxyScore(proxy, 1)
        # 释放ID编辑锁(lock_=20)
        spider.releaseId(request, 20)       # 到这一步一般都已经成功获取数据了
        if not spider._meta_.get('selenium', False):
            if response.status != 200:
                print('***已被大众点评禁封({})***'.format(proxy))
                return request
        return response



class DianpingSpiderMiddleware(object):
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, dict or Item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Response, dict
        # or Item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class DianpingDownloaderMiddleware(object):
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)
