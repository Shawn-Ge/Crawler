# -*- coding: utf-8 -*-

'''

'''

import random

from selenium import webdriver
#from selenium.common.exceptions import NoSuchElementException

from scrapy.http import HtmlResponse
from .settings import IMPLY_WAIT_TIME, USER_AGENTS



class Chrome:
    # Chrome浏览器驱动,针对每个Request对象都初始化一个浏览器。
    def __init__(self, request, proxy=None):
        '# 初始化方法,主要用来创建浏览器实例,以及设置代理'
        self.request = request
        # 设置谷歌浏览器
        ua = random.choice(USER_AGENTS)
        options = webdriver.ChromeOptions()
        options.add_argument('log-level=3')         # 禁止日志
        options.add_argument('lang=zh_CN.UTF-8')    # 设置中文
        options.add_argument('--disable-gpu')       # 谷歌文档提到需要加上这个属性来规避bug
        options.add_argument('blink-settings=imagesEnabled=false')  # 禁止图片加载
#        options.add_argument('user-agent={}'.format(ua))    # 设置随机User-Agent
        # 设置代理IP
        if proxy:
            print('Chrome浏览器代理已更改({})...'.format(proxy))
            options.add_argument("--proxy-server={}".format(proxy))
        # 开启无头模式
        options.set_headless(headless=True)
        self.browser = webdriver.Chrome(chrome_options=options)
        # 设置隐式等待时间
        self.browser.implicitly_wait(IMPLY_WAIT_TIME)
#        self.browser.maximize_window()
        
    def quit(self):
        self.browser.quit()
    
    def get(self, url):
        self.browser.get(url)
    
    def download(self, request, callback=None):
        '''
        # param request: scrapy.Request对象
        # param callback: 回调函数,callback(selenium.webdriver)->status,传入参数必须是selenium.webdriver对象,返回HTTP状态码
        '''
        url = request.url
        self.browser.get(url)
        # 检查HTTP状态码
        status = 200
        if callback:
            status_ = callback(self.browser)
            status = 200 if not isinstance(status_, int) else status_
        
        # 生成response
        response = HtmlResponse(
            url=self.browser.current_url,       # 获取url
            body=self.browser.page_source,      # 获取html文本
            encoding='utf-8', 
            request=self.request, 
            status=status
            )
        return response

