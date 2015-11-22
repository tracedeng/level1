# -*- coding: utf-8 -*-
__author__ = 'tracedeng'

from tornado.web import MissingArgumentError, asynchronous
import json
import common_pb2
import log
g_log = log.WrapperLog('stream', name=__name__, level=log.DEBUG).log  # 启动日志功能
from level1_base import Base


class Account(Base):
    # @asynchronous
    # def get(self):
    #     req = common_pb2.Request()
    #     req.head.cmd = 102
    #     req.head.seq = 2
    #     numbers = "18688982240"
    #     req.head.numbers = numbers
    #     req.consumer_retrieve_request.numbers = numbers
    #     message = package.serial_pb(req)
    #     udp_client = async_udp.AsyncUDPClient()
    #     request = async_udp.UDPRequest("localhost", 9527, message)
    #     udp_client.fetch(request=request, callback=self.on_response)

    @asynchronous
    def post(self, *args, **kwargs):
        """
        根据post["type"]分发处理
        :param args:
        :param kwargs:
        :return:
        """
        try:
            # features_handle = {"register": self.register, "login": self.login, "change_password": self.change_password,
                               # "get_sms_code": self.get_sms_code, "verify_sms_code": self.verify_sms_code}
            features_handle = {"register": self.register}
            self.mode = self.get_argument("type", "dummy")
            g_log.debug("[account] receive %s request", self.mode)
            self.code, self.message = features_handle.get(self.mode, self.dummy_command)()
            if self.code not in [10000, 10100, 10200, 10300, 10400, 10500]:
                self.write(json.dumps({"c": self.code, "m": self.message}))
                self.finish()
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 10001, "m": "exception"}))
            self.finish()

    def on_response(self, response):
        try:
            res = super(Account, self).on_response(response)
            if not res:
                g_log.error("super on_response None")
                self.write(json.dumps({"c": 10002, "m": "exception"}))
            else:
                # features_response = {"register": self.register_response, "login": self.login_response,
                #                      "change_password": self.change_password_response, "get_sms_code": self.get_sms_code,
                #                      "verify_sms_code": self.verify_sms_code}
                features_response = {"register": self.register_response}
                g_log.debug("[account] %s response", self.mode)
                self.code, self.message = features_response.get(self.mode, self.dummy_command)(res)
                self.write(json.dumps({"c": self.code, "m": self.message}))
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 10003, "m": "exception"}))
        self.finish()

    def put(self, *args, **kwargs):
        pass

    def delete(self, *args, **kwargs):
        pass

    def head(self, *args, **kwargs):
        pass

    def patch(self, *args, **kwargs):
        pass

    def options(self, *args, **kwargs):
        pass

    def dummy_command(self, arg=None):
        # 无效的命令
        g_log.debug("unsupported mode %s", self.mode)
        return 10004, "unsupported mode"

    def register(self):
        """
        账号注册phoneNumber, password, passwordMd5, kind
        :return:
        """
        try:
            # 解析post参数
            numbers = self.get_argument("phone_number")
            password = self.get_argument("password")
            password_md5 = self.get_argument("password_md5")
            g_log.debug("[level2.register]")

            # 组请求包
            request = common_pb2.Request()
            request.head.cmd = 3
            request.head.seq = 2
            request.head.numbers = numbers

            body = request.register_request
            body.phone_number = numbers
            body.password = password
            body.password_md5 = password_md5

            # 请求逻辑层
            if self.send_to_level2(request):
                return 10201, "platform failed"
            return 10200, "yes"
        except MissingArgumentError as e:
            g_log.error("miss argument %s", e.arg_name)
            g_log.debug("%s", e)
            return 10202, "miss argument"
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            return 10203, "exception"

    def register_response(self, response):
        """
        逻辑层返回注册请求后处理
        :param response: pb格式回包
        """
        try:
            mode = self.mode
            head = response.head
            code = head.code
            message = head.message
            if 1 == code:
                g_log.debug("register success")
                return 10200, "yes"
            else:
                g_log.debug("register failed, %s:%s", code, message)
                return 10204, message
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            return 10205, "exception"