# -*- coding: utf-8 -*-
__author__ = 'tracedeng'

from tornado.web import RequestHandler, HTTPError
import log
g_log = log.WrapperLog('stream', name=__name__, level=log.DEBUG).log  # 启动日志功能
import async_udp
import package
from level2_environ import get_level2_environ
from account_valid import numbers_to_account, AccountMode


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
        self.response = None

    def send_to_level2(self, request):
        """
        请求level2服务
        :param request: pb格式请求
        """
        g_log.debug("%s", request)
        environ = get_level2_environ()
        message = package.serial_pb(request)
        request = async_udp.UDPRequest(environ[0], environ[1], message)
        udp_client = async_udp.AsyncUDPClient()
        udp_client.fetch(request=request, callback=self.on_response)
        g_log.debug("send request to level2")

    def on_response(self, response):
        """
        返回解包
        :param response: level2回包
        :return: pb格式/成功，None/失败
        """
        g_log.debug("receive response from level2")
        self.response = package.un_serial_pb(response)
        g_log.debug('%s', self.response)

    def get_argument(self, name, default="", check=True):
        """
        获取参数
        :param name: 参数名称
        :param default: 缺省值
        :return:
        """
        value = super(Base, self).get_argument(name, default)
        if name == "numbers":
            # 将numbers转换成平台账号
            # account_mode = AccountMode.MERCHANT if "merchant" == super(Base, self).get_argument("kind", "consumer") \
            #     else AccountMode.CONSUMER
            # value = numbers_to_account(value, account_mode)
            if not value:
                # None == value
                raise InvalidArgumentError("numbers")
        elif name == "manager":
            # value = numbers_to_account(value, AccountMode.MERCHANT)
            if not value:
                # None == value
                raise InvalidArgumentError("manager")
        elif name == "password":
            if not value:
                raise InvalidArgumentError("password")
        elif name == "password_md5":
            pass
            # if not value or len(value) != 32:
            #     raise InvalidArgumentError("password_md5")
        elif name == "name":
            # 创建商家必须要有名称
            if not value:
                raise InvalidArgumentError("name")
        elif name == "longitude":
            # 经度判断
            if value:
                try:
                    g_log.debug(value)
                    value = float(value)
                    g_log.debug(value)
                    if value > 180 or value < -180:
                        raise InvalidArgumentError("longitude")
                except Exception as e:
                    raise InvalidArgumentError("longitude")
            else:
                value = -1.0
        elif name == "latitude":
            # 纬度判断
            if value:
                try:
                    value = float(value)
                    if value > 90 or value < -90:
                        raise InvalidArgumentError("latitude")
                except Exception as e:
                    raise InvalidArgumentError("latitude")
            else:
                value = -1.0
        elif name == "verified":
            # 商户认证
            value = value.lower()
            if value != "yes" and value != "no":
                raise InvalidArgumentError("verified")

        g_log.debug("%s -> %s", name, value)
        return value


class InvalidArgumentError(HTTPError):
    """Exception raised by `RequestHandler.get_argument`.

    according MissingArgumentError
    无效参数异常
    """
    def __init__(self, arg_name):
        super(InvalidArgumentError, self).__init__(
            400, 'Invalid argument %s' % arg_name)
        self.arg_name = arg_name