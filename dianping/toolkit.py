# -*- coding: utf-8 -*-

'''
# 大众点评爬虫工具包
'''

import pymysql
import requests
import json
import datetime
import random
import time
import pandas as pd

from .settings import DEATH_N, BAN_BY_DIANPING, LIFETIME



mysqlCrawler = {
    'user': 'root',       
    'passwd': '123456', 
    'host': 'localhost', 
    'port': 3306, 
    'db': 'crawler', 
    'charset': 'utf8'
    }

def itemToSql(item, option):
    '# 将ITEM对象转换为SQL模式'
    if option.lower() == 'insert':
        l1, l2 = [], []
        for k in item:
            v = item.get(k, None)
            if v is not None:
                if isinstance(v, str):
                    v = '"{}"'.format(v)
                else:
                    v = str(v)
                l1.append(k)
                l2.append(v)
        result = '({0}) VALUE({1})'.format(', '.join(l1), ', '.join(l2))
    
    elif option.lower() == 'update':
        l = []
        for k in item:
            v = item.get(k, None)
            if v is not None:
                if isinstance(v, str):
                    v = '"{}"'.format(v)
                else:
                    v = str(v)
                l.append('{0} = {1}'.format(k, v))
        result = 'SET {}'.format(', '.join(l))
        
    return result



def httpStatus(driver):
    # 验证元素,检查网页状态
    if driver.find_elements_by_xpath('//title[contains(text(), "验证")]'):
        # 检查是否需要输入验证码
        print('\n***需要输入验证码***\n')
        return 403
    
    if driver.find_elements_by_xpath('//button[text()="去大众点评首页"]'):
        # 出现引导页面
        print('\n***出现引导页面***\n')
        return 403
    
    return 200



class IdManager:
    # 一个MySQL数据库通道,附带了操作商铺ID的功能
    def __init__(self):
        self.conn = MysqlConn(mysqlCrawler)
    
    def lockId(self, *args):
        '# 取出一个ID,并将其锁止'
        if args:
            cond = 'AND ' + ' AND '.join(args)
        else:
            cond = ''
        # 取出一条ID
        sql0 = 'SELECT DISTINCT id FROM dianping_restaurants WHERE lock_ = 0 {} LIMIT 1'.format(cond)
        id_ = next(self.conn.fetchOne(sql0))['id']
        # 锁止该ID
        sql1 = 'UPDATE dianping_restaurants SET lock_=1 WHERE id={}'.format(id_)
        self.conn.manipulate(sql1)
        return id_
    
    def releaseId(self, id_, val=0):
        '# 释放指定ID'
        # lock_可以设为其他数,用来辨别是没有数据还是没有抓到
        sql = 'UPDATE dianping_restaurants SET lock_={1} WHERE id={0}'.format(id_, val)
        self.conn.manipulate(sql)
        
    def checkId(self, id_):
        '''
        # 检查传入的ID,在数据库中是什么情况
        # 返回代码:
        # 100: 该ID尚未入库
        # 200: 该ID已经获取全部信息
        # 301: 该ID地理位置信息尚未获取
        # 400: 商铺的基础信息没有全部获取
        # 499: 商铺的基础信息没有全部获取,但是地理信息已获取
        '''
        sql = '''
        SELECT 
            id, lon, lat, type_
        FROM 
            dianping_restaurants
        WHERE 
            id={}
        '''.format(id_)
        try:
            ser = next(self.conn.fetchOne(sql))
            if ser['type_'] is None:
                # 商铺的基础信息没有获取全(代码4xx)
                if not(ser['lon'] is None or ser['lat'] is None):
                    # 商铺坐标已获取
                    return 499
                return 400
            
            else:
                # 商铺的基础信息已获取(代码3XX/2XX)
                if ser['lon'] is None or ser['lat'] is None:
                    return 301
                # 该ID信息已获取全部信息
                return 200 
                
        except StopIteration:
            # 该ID尚未入库
            return 100
    
    def manipulate(self, sql):
        self.conn.manipulate(sql)        
        
    def close(self):
        self.conn.close()



class ProxyManager:
    # 代理管理器
    def __init__(self, n):
        self.conn = MysqlConn(mysqlCrawler)
        self.n = n      # 额定存活代理量
        self.n_ = 0     # 当前存活代理量
        self.todayn = 0 # 当日下载总量
        
    @staticmethod  
    def isValidProxy(scheme, ip, port):
        '# 测试代理是否可用'
        testUrl = r'http://httpbin.org/ip'
        proxy = '{0}://{1}:{2}'.format(scheme, ip, port)
        proxies = {
            scheme: proxy
            }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:6.0) Gecko/20100101 Firefox/6.0', 
            'Connection': 'close'
            }
        try:
            r = requests.get(
                    testUrl, 
                    headers=headers, 
                    proxies=proxies, 
                    verify=False
                )
        except requests.exceptions.ProxyError:
            print('代理({})验证不通过...'.format(proxy))
            return False
        if r.status_code==200:
            ip = json.loads(r.text)['origin']
            print('代理({0})验证通过(实际IP为:{1})...'.format(proxy, ip))
            return True
        
    def downloadProxy(self, n):
        '# 从芝麻代理上获取代理'
        # http://webapi.http.zhimacangku.com/getip?num=1&type=2&pro=310000&city=0&yys=0&port=1&pack=37728&ts=0&ys=0&cs=0&lb=1&sb=0&pb=5&mr=2&regions=
        url = (
            r'http://webapi.http.zhimacangku.com/getip?' +      # 隧道IP: http://http.tiqu.alicdns.com/getip3?
            r'pack=37728' +                                     # 用户套餐ID
            r'&ts=1' +                                          # 显示IP过期时间
            r'&num={}'.format(n) +                              # 一次提取的数量    
            r'&port={}'.format(1) +                             # 设定IP协议, 1:HTTP, 2:SOCK5, 11:HTTPS
            r'&time={}'.format(LIFETIME) +                      # 设定代理寿命
            r'&type=2&pro=310000&city=0&yys=0&ys=0&cs=0&lb=1&sb=0&pb=5&mr=1&regions='
            )
        headers = {
            'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:6.0) Gecko/20100101 Firefox/6.0', 
            'Connection': 'close'
            }
        r = requests.get(
                    url, 
                    headers=headers, 
                    verify=False
                )
        if r.status_code==200:
            info = json.loads(r.text)
            if info['success']:
                data = info['data']
                now = str(datetime.datetime.now())
                for d in data:
                    scheme = 'http'
                    ip = d['ip']
                    port = d['port']
                    expire = d['expire_time']
                    proxy = '{0}://{1}:{2}'.format(scheme, ip, port)
                    # 可能会出现重复的代理
#                    self.conn.manipulate('DELETE FROM ippool WHERE proxy="{}"'.format(proxy))
                    self.conn.manipulate(
                        '''
                        UPDATE 
                            ippool 
                        SET 
                            proxy = "{0}_{1}" 
                        WHERE 
                            proxy="{0}"
                        '''.format(proxy, int(time.time()*100))     # 当前时间戳的(小数点向后移动两位)
                        )
                    # 插入代理
                    sql = '''
                    INSERT INTO 
                        ippool(
                            proxy, ip, port, scheme, expire_time, birth_time, lifetime
                        )
                    VALUE(
                            "{0}", "{1}", "{2}", "{3}", "{4}", "{5}", {6}
                        )
                    '''.format(proxy, ip, port, scheme, expire, now, LIFETIME)
                    self.conn.manipulate(sql)
                    print('写入新代理{}...'.format(proxy))
            else:
                print('无法获取新代理({})...'.format(info['msg']))
                return False
    
    def killProxy(self, proxy):
        '# 指定代理死亡次数+1'
        now = str(datetime.datetime.now())
        sql = '''
        UPDATE 
            ippool
        SET
            death = death+1,
            death_time = "{0}"
        WHERE 
            proxy = "{1}"
        '''.format(now, proxy)
        self.conn.manipulate('FLUSH TABLE ippool')
        self.conn.manipulate(sql)
        print('杀死代理({})...'.format(proxy))
    
    def flushProxyInUsing(self, proxy, n):
        '# 更新代理的当前使用计数'
        sql = '''
        UPDATE 
            ippool
        SET
            using_n = using_n+{0}*1
        WHERE 
            proxy = "{1}"
        '''.format(n, proxy)
        self.conn.manipulate('FLUSH TABLE ippool')
        self.conn.manipulate(sql)

    def flushProxyScore(self, proxy, score):
        '# 更新代理的成绩(成功爬取次数以及被BAN次数)'
        if score>0:
            sql = '''
            UPDATE 
                ippool
            SET
                score = score+1, 
                ban_by_dianping = 0
            WHERE 
                proxy = "{}"
            '''.format(proxy)
        else:
            sql = '''
            UPDATE 
                ippool
            SET
                ban_by_dianping = ban_by_dianping+1
            WHERE 
                proxy = "{}"
            '''.format(proxy)
        self.conn.manipulate('FLUSH TABLE ippool') 
        self.conn.manipulate(sql)
    
    def getProxy(self):
        '# 从MySQL中获取代理'
        # 死亡次数小于1次,而且被点评BAN的次数小于10次
        sql = '''
        SELECT 
            proxy, scheme, ip, port
        FROM
            ippool
        WHERE 
            death < {0} AND
            ban_by_dianping <{1}
        '''.format(DEATH_N, BAN_BY_DIANPING)
        self.conn.manipulate('FLUSH TABLE ippool')
        df = self.conn.fetchAll(sql)
        self.n_ = len(df)   # 更新当前可用代理总数
        if self.n_:
            rn = random.randint(0, len(df)-1)
            proxy, scheme, ip, port = df['proxy'][rn], df['scheme'][rn], df['ip'][rn], df['port'][rn]
            if self.isValidProxy(scheme, ip, port):
                # 代理使用计数加1
                self.flushProxyInUsing(proxy, 1)
                return proxy
            else:
                # 该代理死亡次数n+1
                self.killProxy(proxy)
                # 下在一个新的代理补充进去
                self.downloadProxy(1)
                # 递归调用此函数,直至获取有效代理
                return self.getProxy()
        else:
            print('无代理可用...')
            return None

    def refleshProxy(self):
        '# 对所有代理进行一次检查'
        self.conn.manipulate('FLUSH TABLE ippool')
        now = str(datetime.datetime.now())
        # 检查没有被BAN的IP的总量,如果总量少于额定总量,则补充新代理,并且杀死这些代理
        sql0 = '''
        UPDATE 
            ippool
        SET
            death = {0}, 
            death_time = "{2}"
        WHERE 
            death < {0} AND
            ban_by_dianping >= {1}
        '''.format(DEATH_N, BAN_BY_DIANPING, now)
        self.conn.manipulate(sql0)
        # 跟新当日获取的代理数量及还存活的代理数量
        today = datetime.date.today()
        # 获取今日下载的代理数量
        sql1 = '''
        SELECT 
            count(*) n
        FROM
            ippool
        WHERE 
            birth_time > "{}" 
        '''.format(str(today))
        # 获取存活的代理数量
        sql2 = '''
        SELECT 
            count(*) n
        FROM
            ippool
        WHERE
            death < {}
        '''.format(DEATH_N)
        s1 = self.conn.fetchOne(sql1)
        s2 = self.conn.fetchOne(sql2)
        self.todayn = next(s1)['n']
        self.n_ = next(s2)['n']
        print('当日已下载{}个(非重复)代理...'.format(self.todayn))
        # 补充代理
        gap = self.n - self.n_
        if gap>0:
            # 补充差额
            print('补充下载{}个新代理...'.format(gap))
            self.downloadProxy(gap)
    
    def close(self):
        self.conn.close()



class MysqlConn():
    '# MySQL数据库连接器'
    def __init__(self, connParam=None):
        if connParam:
            self.connect(**connParam)
    
    def connect(self, **connParam):
        self.conn = pymysql.connect(**connParam)
        
    def query(self, sql, fetchAll):
        '# 查询生成器'
        with self.conn.cursor() as cur:
            n = cur.execute(sql)
            feilds = tuple(col[0] for col in cur.description)
            if fetchAll:
                yield pd.DataFrame(list(cur.fetchall()), columns=feilds)
            else:
                for _ in range(n):
                    data = cur.fetchmany(0)
                    yield pd.Series(data[0], index=feilds)
        
    def fetchOne(self, sql):
        '# 逐条查询,返回生成器,生成器pd.Series'
        return self.query(sql, False)
    
    def fetchAll(self, sql):
        '# 查询全部,返回pd.DataFrame'
        return next(self.query(sql, True))

    def manipulate(self, sql):
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql)
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
    
    def close(self):
        self.conn.close()