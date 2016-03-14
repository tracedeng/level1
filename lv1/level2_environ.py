# -*- coding: utf-8 -*-
__author__ = 'tracedeng'

import ConfigParser
import log
g_log = log.WrapperLog('stream', name=__name__, level=log.DEBUG).log  # 启动日志功能
from singleton import singleton


@singleton
class Level2Environ():
    LEVEL2_ADDRESS = "127.0.0.1:9527"
    LEVEL2_TIMEOUT = 1000           # 逻辑层超时时间

    def __init__(self):
        """
        :param conf_path: 配置文件路径
        :return:
        """
        conf_path = "./coframe/server.conf"
        config = ConfigParser.ConfigParser()
        config.read(conf_path)
        self.config = config

        # 解析逻辑层lv2地址
        try:
            lv2_address = config.get("level2", "address")
            lv2_expire = config.get("level2", "timeout")
        except ConfigParser.NoSectionError as e:
            g_log.warning("config file miss section level2")
        except ConfigParser.NoOptionError as e:
            g_log.warning("config file miss %s:%s", e.section, e.option)
        except Exception as e:
            g_log.warning("<%s> %s", e.__class__, e)
        if not lv2_address:
            lv2_address = self.__class__.LEVEL2_ADDRESS
        if not lv2_expire:
            lv2_expire = self.__class__.LEVEL2_TIMEOUT
        self.lv2_address = lv2_address
        self.lv2_expire = lv2_expire
        g_log.debug("level2 address %s, expire time %s", lv2_address, lv2_expire)


def get_level2_environ():
    """
    获取level2的环境参数
    :return: (ip, port, expire)/成功，None/失败
    """
    try:
        level2 = Level2Environ()
        address = level2.lv2_address
        address = address.split(":")
        ip = address[0]
        port = int(address[1])
        return ip, port, level2.lv2_expire
    except Exception as e:
        g_log.error("<%s> %s", e.__class__, e)
        return None
