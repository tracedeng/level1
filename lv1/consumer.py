# -*- coding: utf-8 -*-
__author__ = 'tracedeng'

from tornado.web import MissingArgumentError, asynchronous
import json
import random
import redis
import common_pb2
import log
g_log = log.WrapperLog('stream', name=__name__, level=log.DEBUG).log  # 启动日志功能
from level1_base import Base, InvalidArgumentError
from redis_connection import get_redis_connection


class Consumer(Base):
    @asynchronous
    def post(self, *args, **kwargs):
        """
        根据post["type"]分发处理
        :param args:
        :param kwargs:
        :return:
        """
        try:
            features_handle = {"upload_token": self.upload_token, "update_avatar": self.update_avatar}
            self.mode = self.get_argument("type")
            g_log.debug("[consumer.%s.request]", self.mode)
            features_handle.get(self.mode, self.dummy_command)()
        except MissingArgumentError as e:
            # 缺少请求参数
            g_log.error("miss argument %s, %s", e.arg_name, e)
            self.write(json.dumps({"c": 20001, "m": "miss argument"}))
            g_log.debug("[consumer.%s.response]", self.mode)
            self.finish()
        except InvalidArgumentError as e:
            # 缺少请求参数
            g_log.error("invalid argument %s, %s", e.arg_name, e)
            self.write(json.dumps({"c": 20008, "m": "invalid argument"}))
            g_log.debug("[consumer.%s.response]", self.mode)
            self.finish()
        except (redis.ConnectionError, redis.TimeoutError) as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 20007, "m": "exception"}))
            g_log.debug("[consumer.%s.response]", self.mode)
            self.finish()
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 20002, "m": "exception"}))
            g_log.debug("[consumer.%s.response]", self.mode)
            self.finish()

    def on_response(self, response):
        try:
            super(Consumer, self).on_response(response)
            if not self.response:
                g_log.error("illegal response")
                self.write(json.dumps({"c": 20003, "m": "exception"}))
            else:
                features_response = {"upload_token": self.upload_token_response}
                self.code, self.message = features_response.get(self.mode, self.dummy_command)(self.response)
                if self.code == 1:
                    self.write(json.dumps({"c": self.code, "r": self.message}))
                else:
                    self.write(json.dumps({"c": self.code, "m": self.message}))
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 20004, "m": "exception"}))
        g_log.debug("[consumer.%s.response]", self.mode)
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
            return 20005, "no handler"
        else:
            # 无效的命令
            g_log.debug("unsupported type %s", self.mode)
            self.write(json.dumps({"c": 20006, "m": "unsupported type"}))
            self.finish()

    def upload_token(self):
        """
        登录
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        kind = self.get_argument("resource_kind", "dummy")
        merchant_identity = self.get_argument("merchant", "")
        debug = self.get_argument("debug", "online")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 601
        request.head.seq = 2
        request.head.numbers = numbers

        body = request.upload_token_request
        body.numbers = numbers
        body.resource_kind = kind
        body.merchant_identity = merchant_identity
        body.debug = debug

        # 请求逻辑层
        self.send_to_level2(request)

    def upload_token_response(self, response):
        """
        逻辑层返回登录请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            # level2 成功返回
            g_log.debug("get upload token success")
            body = response.upload_token_response
            upload_token = body.upload_token
            return 1, upload_token
        else:
            g_log.debug("get upload token failed, %s:%s", code, message)
            return 20101, message

    def update_avatar(self):
        pass