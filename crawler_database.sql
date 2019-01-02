
# ip池数据库
CREATE TABLE ippool(
	proxy VARCHAR(200) COMMENT '完整代理名{secheme}://{ip}:{port}',
	ip VARCHAR(100) COMMENT 'ip地址',
	port VARCHAR(20) COMMENT '端口', 
	scheme VARCHAR(20) COMMENT '协议',
	verify DATETIME COMMENT '最后验证时间',
	CONSTRAINT pk_ippool_proxy PRIMARY KEY(proxy)
);


# 大众点评商铺信息数据表
CREATE TABLE dianping_restaurants(
	id VARCHAR(200) COMMENT '大众点评商铺ID(www.dianping.com/shop/{id})',
	name VARCHAR(200) COMMENT '店铺名',
	address VARCHAR(200) COMMENT '店铺地址',
	type_ VARCHAR(200) COMMENT '店铺类型',
	tag VARCHAR(100) COMMENT '地址标签',
	comments_n MEDIUMINT(8) COMMENT '点评数量',
	consumption_per_capita DOUBLE(10,2) COMMENT '人均消费额',
	stars TINYINT(3) COMMENT '星数',
	flavor DOUBLE(3,1) COMMENT '口味评分',
	envir DOUBLE(3,1) COMMENT '环境评分',
	service DOUBLE(3,1) COMMENT '服务评分',
	lon DOUBLE(11,7) COMMENT '经度',
	lat DOUBLE(11,7) COMMENT '纬度'
	
);


CREATE VIEW 
	vw_death_proxy (proxy, birth_time, death_time, expire_time, lifetime, hehe, score, ban_by_dianping)
AS SELECT 
	proxy, birth_time, death_time, expire_time, TIMESTAMPDIFF(SECOND, birth_time, death_time)/60, TIMESTAMPDIFF(SECOND, death_time, expire_time)/60, score, ban_by_dianping 
FROM 
	ippool 
WHERE 
	birth_time > CURDATE() AND 
	death=1
;

CREATE VIEW
	vw_desc_proxy(download_n, nd_n, avg_score, avg_lifetime, avg_score_nd, avg_lifetime_nd)
AS 
(
	SELECT 
		avg(e.n), avg(f.n), avg(a.score), avg(c.lifetime), avg(b.score), avg(d.lifetime)
	FROM
		(SELECT score FROM vw_death_proxy) a, 
		(SELECT score FROM vw_death_proxy WHERE ban_by_dianping<3) b, 
		(SELECT lifetime FROM vw_death_proxy) c,
		(SELECT lifetime FROM vw_death_proxy WHERE ban_by_dianping<3) d,
		(SELECT count(*) n FROM ippool WHERE birth_time > CURDATE()) e, 
		(SELECT count(*) n FROM vw_death_proxy WHERE ban_by_dianping<3) f
);


CREATE USER 'zhangshuxun'@'101.87.181.73' IDENTIFIED BY '111111';


GRANT
	SELECT
ON
	crawler.ippool
TO
	'zhangshuxun'@'101.87.181.73';