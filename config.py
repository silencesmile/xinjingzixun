from redis import StrictRedis
class Config(object):
    # 设置调试模式
    DEBUG = None
    # 设置秘钥 通过os,和base64代码编码生成
    SECRET_KEY = 'k6fQDT/sHyZbrHiefRIESIvzo8LKQkrLYCui5glE2C0='

    # 配置sqlalchemy连接mysql数据库
    SQLALCHEMY_DATABASE_URI = 'mysql://root:mysql@localhost/newsInfo'
    # 配置数据库的动态追踪修改
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 配置redis的ip和port
    REDIS_IP = "127.0.0.1"
    REDIS_PORT = 6379

    # 使用redis保存session信息
    SESSION_TYPE = "redis"
    # 对session信息进行签名
    SESSION__USE_SIGNER = True
    # 存储session的redis实例
    SESSION_REDIS = StrictRedis(host=REDIS_IP, port=REDIS_PORT)
    # 指定session过期时间 1天
    PERMANENT_SESSION_LIFETIME= 86400


class Development(Config):
    DEBUG = True

class Producetion(Config):
    DEBUG = False

# 把配置对象实现字典映射
config = {
    "dev":Development,
    "pro":Producetion
}