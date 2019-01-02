# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html


from .toolkit import IdManager, itemToSql
from scrapy.exceptions import DropItem




class DianpingMysqlInsertPipeline(object):
    def open_spider(self, spider):
        # 连接数据库(读写爬取的数据)
#        self.conn = MysqlConn(mysqlCrawler)
        self.conn = IdManager()
        

    def close_spider(self, spider):
        spider.idManager.close()    # 关闭爬虫的商铺ID管理器(也是个数据库连接)
        self.conn.close()
        

    def process_item(self, item, spider):
        '''
        # 把数据记录在MySql数据库中
        '''
#        if item['ID'] not in self.idSet:
        id_ = item['ID']
        code = self.conn.checkId(id_)
        if code == 100:
            # 此ID尚未入库(插入操作)
            sql = 'INSERT INTO dianping_restaurants{}'.format(itemToSql(item, 'insert'))
        else:
            # 此ID已经入库(更新操作)
            sql = 'UPDATE dianping_restaurants {0} WHERE id = {1}'.format(itemToSql(item, 'update'), id_)
        try:
            self.conn.manipulate(sql)
            # 把店铺ID添加至spider列表中
#                self.idSet.add(item['ID'])
            print('数据库写入成功...')
            # 依然返回item
            return item 
        except:
            print('数据库写入失败...')
            raise

