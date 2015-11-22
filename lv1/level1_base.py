# -*- coding: utf-8 -*-
__author__ = 'tracedeng'

from tornado.web import RequestHandler, asynchronous
from tornado import gen
import common_pb2
import log
g_log = log.WrapperLog('stream', name=__name__, level=log.DEBUG).log  # 启动日志功能
# from level2_access import send_to_level2, receive_from_level2
import async_udp
import package
from level2_environ import get_level2_environ


class Base(RequestHandler):
    """
    业务处理基础类
    """
    # def __init__(self, *args, **kwargs):
    def __init__(self, application, request, **kwargs):
        super(Base, self).__init__(application, request, **kwargs)
        self.code = 1   # 模块号(2位) + 功能号(2位) + 错误号(2位)
        self.message = ""
        self.mode = ""

    def send_to_level2(self, request):
        """
        请求level2服务
        :param request: pb格式请求
        :return: 0/成功，1/失败
        """
        try:
            environ = get_level2_environ()
            message = package.serial_pb(request)
            request = async_udp.UDPRequest(environ[0], environ[1], message)
            udp_client = async_udp.AsyncUDPClient()
            udp_client.fetch(request=request, callback=self.on_response)
            return 0
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            return 1

    def on_response(self, response):
        """
        返回解包
        :param response: level2回包
        :return: pb格式/成功，None/失败
        """
        try:
            res = package.un_serial_pb(response)
            g_log.debug('%s', res)
            return res
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            return None