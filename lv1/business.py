# -*- coding: utf-8 -*-
__author__ = 'tracedeng'

from tornado.web import MissingArgumentError, asynchronous
import json
import common_pb2
import log
g_log = log.WrapperLog('stream', name=__name__, level=log.DEBUG).log  # 启动日志功能
from level1_base import Base, InvalidArgumentError


class Business(Base):
    @asynchronous
    def post(self, *args, **kwargs):
        """
        根据post["type"]分发处理
        :param args:
        :param kwargs:
        :return:
        """
        try:
            features_handle = {"update_consumption_ratio": self.update_consumption_ratio,
                               "retrieve_parameters": self.retrieve_business_parameters}
            self.mode = self.get_argument("type")
            g_log.debug("[business.%s.request]", self.mode)
            features_handle.get(self.mode, self.dummy_command)()
        except MissingArgumentError as e:
            # 缺少请求参数
            g_log.error("miss argument %s, %s", e.arg_name, e)
            self.write(json.dumps({"c": 1050001, "m": "miss argument"}))
            g_log.debug("[business.%s.response]", self.mode)
            self.finish()
        except InvalidArgumentError as e:
            # 无效请求参数
            g_log.error("invalid argument %s, %s", e.arg_name, e)
            self.write(json.dumps({"c": 1050008, "m": "invalid argument"}))
            g_log.debug("[business.%s.response]", self.mode)
            self.finish()
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 1050002, "m": "exception"}))
            g_log.debug("[business.%s.response]", self.mode)
            self.finish()

    def on_response(self, response):
        try:
            super(Business, self).on_response(response)
            if not self.response:
                g_log.error("illegal response")
                self.write(json.dumps({"c": 1050003, "m": "exception"}))
            else:
                features_response = {"update_consumption_ratio": self.update_consumption_ratio_response,
                                     "retrieve_parameters": self.retrieve_business_parameters_response}
                self.code, self.message = features_response.get(self.mode, self.dummy_command)(self.response)
                if self.code == 1:
                    self.write(json.dumps({"c": self.code, "r": self.message}))
                else:
                    self.write(json.dumps({"c": self.code, "m": self.message}))
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 1050004, "m": "exception"}))
        g_log.debug("[business.%s.response]", self.mode)
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
        if arg:
            # 未定义返回处理函数
            g_log.debug("not defined response")
            return 1050005, "no handler"
        else:
            # 无效的命令
            g_log.debug("unsupported type %s", self.mode)
            self.write(json.dumps({"c": 1050006, "m": "unsupported type"}))
            self.finish()

    def update_consumption_ratio(self):
        """
        商家更新消费兑换积分比例
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        ratio = self.get_argument("ratio")
        merchant_identity = self.get_argument("merchant", "")
        session_key = self.get_argument("session_key", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 404
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.consumption_ratio_update_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity
        body.consumption_ratio = ratio

        # 请求逻辑层
        self.send_to_level2(request)


    def update_consumption_ratio_response(self, response):
        """
        逻辑层返回登录请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("update consumption ratio success")
            return 1, "yes"
        else:
            g_log.debug("update consumption ratio failed, %s:%s", code, message)
            return 1050101, message

    def retrieve_business_parameters(self):
        """
        读取商家运营参数
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        merchant_identity = self.get_argument("merchant", "")
        session_key = self.get_argument("session_key", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 402
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.business_parameters_retrieve_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity

        # 请求逻辑层
        self.send_to_level2(request)

    def retrieve_business_parameters_response(self, response):
        """
        逻辑层返回登录请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            # level2 成功返回
            g_log.debug("get business parameters success")
            body = response.business_parameters_retrieve_response
            r = {"bo": body.bond, "bal": body.balance, "brt": body.balance_ratio, "crt": body.consumption_ratio}
            return 1, r
        else:
            g_log.debug("update consumption ratio failed, %s:%s", code, message)
            return 1050201, message
