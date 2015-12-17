# -*- coding: utf-8 -*-
__author__ = 'tracedeng'

from tornado.web import MissingArgumentError, asynchronous
import json
import redis
import common_pb2
import log
g_log = log.WrapperLog('stream', name=__name__, level=log.DEBUG).log  # 启动日志功能
from level1_base import Base, InvalidArgumentError


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
            features_handle = {"create": self.create_consumer, "retrieve": self.retrieve_consumer,
                               "update": self.update_consumer, "delete": self.delete_consumer,
                               "upload_token": self.upload_token, "update_avatar": self.update_avatar}
            self.mode = self.get_argument("type")
            g_log.debug("[consumer.%s.request]", self.mode)
            features_handle.get(self.mode, self.dummy_command)()
        except MissingArgumentError as e:
            # 缺少请求参数
            g_log.error("miss argument %s, %s", e.arg_name, e)
            self.write(json.dumps({"c": 1020001, "m": "miss argument"}))
            g_log.debug("[consumer.%s.response]", self.mode)
            self.finish()
        except InvalidArgumentError as e:
            # 缺少请求参数
            g_log.error("invalid argument %s, %s", e.arg_name, e)
            self.write(json.dumps({"c": 1020008, "m": "invalid argument"}))
            g_log.debug("[consumer.%s.response]", self.mode)
            self.finish()
        except (redis.ConnectionError, redis.TimeoutError) as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 1020007, "m": "exception"}))
            g_log.debug("[consumer.%s.response]", self.mode)
            self.finish()
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 1020002, "m": "exception"}))
            g_log.debug("[consumer.%s.response]", self.mode)
            self.finish()

    def on_response(self, response):
        try:
            super(Consumer, self).on_response(response)
            if not self.response:
                g_log.error("illegal response")
                self.write(json.dumps({"c": 1020003, "m": "exception"}))
            else:
                features_response = {"create": self.create_consumer_response,
                                     "retrieve": self.retrieve_consumer_response,
                                     "update": self.update_consumer_response,
                                     "delete": self.delete_consumer_response,
                                     "upload_token": self.upload_token_response}
                self.code, self.message = features_response.get(self.mode, self.dummy_command)(self.response)
                if self.code == 1:
                    self.write(json.dumps({"c": self.code, "r": self.message}))
                else:
                    self.write(json.dumps({"c": self.code, "m": self.message}))
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 1020004, "m": "exception"}))
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
            return 1020005, "no handler"
        else:
            # 无效的命令
            g_log.debug("unsupported type %s", self.mode)
            self.write(json.dumps({"c": 1020006, "m": "unsupported type"}))
            self.finish()

    def create_consumer(self):
        """
        创建客户资料
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        session_key = self.get_argument("session_key", "")
        nickname = self.get_argument("nickname", "")
        sexy = self.get_argument("sexy", "unknow")
        age = self.get_argument("age", 0)
        email = self.get_argument("email", "")
        avatar = self.get_argument("avatar", "")
        introduce = self.get_argument("introduce", "")
        country = self.get_argument("country", "")
        location = self.get_argument("location", "")
        qrcode = self.get_argument("qrcode", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 101
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.consumer_create_request
        body.numbers = numbers
        material = body.material
        material.nickname = nickname
        material.sexy = sexy
        material.age = int(age)
        material.email = email
        material.avatar = avatar
        material.introduce = introduce
        material.country = country
        material.location = location
        material.qrcode = qrcode

        # 请求逻辑层
        self.send_to_level2(request)

    def create_consumer_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("create consumer success")
            return 1, "yes"
        else:
            g_log.debug("create consumer failed, %s:%s", code, message)
            return 1020101, message

    def retrieve_consumer(self):
        """
        读取客户资料
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        session_key = self.get_argument("session_key", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 102
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.consumer_retrieve_request
        body.numbers = numbers

        # 请求逻辑层
        self.send_to_level2(request)

    def retrieve_consumer_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("retrieve consumer success")
            body = response.consumer_retrieve_response
            material = body.material
            r = {"ni": material.nickname, "sex": material.sexy, "age": material.age, "em": material.email,
                 "ava": material.avatar, "in": material.introduce, "co": material.country,
                 "lo": material.location, "qr": material.qrcode}
            return 1, r
        else:
            g_log.debug("retrieve consumer failed, %s:%s", code, message)
            return 1020201, message

    def update_consumer(self):
        """
        更新客户资料
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        session_key = self.get_argument("session_key", "")

        default = ["not", "update"]
        nickname = self.get_argument("nickname", default)
        sexy = self.get_argument("sexy", default)
        age = self.get_argument("age", default)
        email = self.get_argument("email", default)
        avatar = self.get_argument("avatar", default)
        introduce = self.get_argument("introduce", default)
        country = self.get_argument("country", default)
        location = self.get_argument("location", default)
        qrcode = self.get_argument("qrcode", default)

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 104
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.consumer_update_request
        body.numbers = numbers
        material = body.material

        if nickname != default:
            material.nickname = nickname
        if sexy != default:
            material.sexy = sexy
        if age != default:
            material.age = int(age)
        if email != default:
            material.email = email
        if avatar != default:
            material.avatar = avatar
        if introduce != default:
            material.introduce = introduce
        if country != default:
            material.country = country
        if location != default:
            material.location = location
        if qrcode != default:
            material.qrcode = qrcode

        # 请求逻辑层
        self.send_to_level2(request)

    def update_consumer_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("update consumer success")
            return 1, "yes"
        else:
            g_log.debug("update consumer failed, %s:%s", code, message)
            return 1020401, message

    def delete_consumer(self):
        """
        创建客户资料
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        session_key = self.get_argument("session_key", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 105
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.consumer_delete_request
        body.numbers = numbers

        # 请求逻辑层
        self.send_to_level2(request)

    def delete_consumer_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("delete consumer success")
            return 1, "yes"
        else:
            g_log.debug("delete consumer failed, %s:%s", code, message)
            return 1020501, message

    def upload_token(self):
        """
        登录
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        kind = self.get_argument("resource", "dummy")
        merchant_identity = self.get_argument("merchant", "")
        debug = self.get_argument("debug", "online")
        session_key = self.get_argument("session_key", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 601
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

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
            # upload_token = body.upload_token
            # key = body.key
            r = {"tok": body.upload_token, "path": body.key}
            return 1, r
        else:
            g_log.debug("get upload token failed, %s:%s", code, message)
            return 1020601, message

    def update_avatar(self):
        pass