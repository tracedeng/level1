# -*- coding: utf-8 -*-
__author__ = 'tracedeng'

# 因为level1和level2很多文件重名出错，所以不在level2中import
import sys
sys.path.remove("/Users/tracedeng/PycharmProjects/testproject/calculus/lv2")

import ConfigParser
from tornado.ioloop import IOLoop
from tornado.web import Application

import log
g_log = log.WrapperLog('stream', name=__name__, level=log.DEBUG).log  # 启动日志功能
from account import Account
from credit import Credit
from consumer import Consumer
from merchant import Merchant
from business import Business


class Server():
    """
    异步tornado服务
    """
    PORT = 8000

    def __init__(self, conf_path="server.conf"):
        """
        :param conf_path: 配置文件路径
        :return:
        """
        config = ConfigParser.ConfigParser()
        config.read(conf_path)
        self.config = config

        # 解析web server监听端口，master处理模块和类
        try:
            port = config.get("web_server", "port")
        except ConfigParser.NoSectionError as e:
            g_log.warning("config file miss section web_server, listen on port 8000")
        except ConfigParser.NoOptionError as e:
            g_log.warning("config file miss %s:%s", e.section, e.option)
        except Exception as e:
            g_log.warning("<%s> %s", e.__class__, e)
        if not port:
            port = self.__class__.PORT
        self.port = port
        g_log.debug("listen on port %s" % self.port)

    def run(self):
        try:
            # url路由
            route = [(r"/account", Account), (r"/consumer", Consumer), (r"/merchant", Merchant), (r"/credit", Credit), (r"/business", Business)]
            application = Application(route)
            application.listen(self.port)

            # 启动level1
            g_log.debug("now start loop")
            IOLoop.current().start()
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)


if __name__ == "__main__":
    server = Server()
    server.run()