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


class Account(Base):
    @asynchronous
    def post(self, *args, **kwargs):
        """
        根据post["type"]分发处理
        :param args:
        :param kwargs:
        :return:
        """
        try:
            features_handle = {"register": self.register, "login": self.login, "change_password": self.change_password,
                               "get_sms_code": self.get_sms_code, "verify_sms_code": self.verify_sms_code}
            self.mode = self.get_argument("type")
            g_log.debug("[account.%s.request]", self.mode)
            features_handle.get(self.mode, self.dummy_command)()
        except MissingArgumentError as e:
            # 缺少请求参数
            g_log.error("miss argument %s, %s", e.arg_name, e)
            self.write(json.dumps({"c": 1010001, "m": "miss argument"}))
            g_log.debug("[account.%s.response]", self.mode)
            self.finish()
        except InvalidArgumentError as e:
            # 无效请求参数
            g_log.error("invalid argument %s, %s", e.arg_name, e)
            self.write(json.dumps({"c": 1010008, "m": "invalid argument"}))
            g_log.debug("[account.%s.response]", self.mode)
            self.finish()
        except (redis.ConnectionError, redis.TimeoutError) as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 1010007, "m": "exception"}))
            g_log.debug("[account.%s.response]", self.mode)
            self.finish()
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 1010002, "m": "exception"}))
            g_log.debug("[account.%s.response]", self.mode)
            self.finish()

    def on_response(self, response):
        try:
            super(Account, self).on_response(response)
            if not self.response:
                g_log.error("illegal response")
                self.write(json.dumps({"c": 1010003, "m": "exception"}))
            else:
                features_response = {"register": self.register_response, "login": self.login_response,
                                     "change_password": self.change_password_response, "get_sms_code": self.get_sms_code}
                #                      "verify_sms_code": self.verify_sms_code}
                self.code, self.message = features_response.get(self.mode, self.dummy_command)(self.response)
                if self.code == 1:
                    self.write(json.dumps({"c": self.code, "r": self.message}))
                else:
                    self.write(json.dumps({"c": self.code, "m": self.message}))
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 1010004, "m": "exception"}))
        g_log.debug("[account.%s.response]", self.mode)
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
            return 1010005, "no handler"
        else:
            # 无效的命令
            g_log.debug("unsupported type %s", self.mode)
            self.write(json.dumps({"c": 1010006, "m": "unsupported type"}))
            self.finish()

    def login(self):
        """
        登录
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        password_md5 = self.get_argument("password_md5")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 2
        request.head.seq = 2
        request.head.numbers = numbers

        body = request.login_request
        body.numbers = numbers
        body.password_md5 = password_md5

        # 请求逻辑层
        self.send_to_level2(request)

    def login_response(self, response):
        """
        逻辑层返回登录请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            # level2 成功返回
            g_log.debug("login success")
            body = response.login_response
            session_key = body.session_key
            return 1, session_key
        else:
            g_log.debug("login failed, %s:%s", code, message)
            return 1010101, message

    def register(self):
        """
        账号注册phoneNumber, password, passwordMd5, kind
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        password = self.get_argument("password")
        password_md5 = self.get_argument("password_md5")
        sms_code = self.get_argument("sms_code")

        # 检查验证码
        if "match" != self._verify_sms_code(numbers, sms_code):
            g_log.error("invalid sms code %s", sms_code)
            self.write(json.dumps({"c": 1010202, "m": "invalid sms code"}))
            g_log.debug("[account.register.response]")
            self.finish()
            return

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 3
        request.head.seq = 2
        request.head.numbers = numbers

        body = request.register_request
        body.numbers = numbers
        body.password = password
        body.password_md5 = password_md5

        # 请求逻辑层
        self.send_to_level2(request)

    def register_response(self, response):
        """
        逻辑层返回注册请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("register success")
            return 1, "yes"
        else:
            g_log.debug("register failed, %s:%s", code, message)
            return 1010201, message

    def change_password(self):
        """
        重置账号密码phoneNumber, password, passwordMd5, kind
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        password = self.get_argument("password")
        password_md5 = self.get_argument("password_md5")
        sms_code = self.get_argument("sms_code")

        # 检查验证码
        if "match" != self._verify_sms_code(numbers, sms_code):
            g_log.error("invalid sms code %s", sms_code)
            self.write(json.dumps({"c": 1010302, "m": "invalid sms code"}))
            g_log.debug("[account.change_password.response]")
            self.finish()
            return

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 4
        request.head.seq = 2
        request.head.numbers = numbers

        body = request.change_password_request
        body.numbers = numbers
        body.password = password
        body.password_md5 = password_md5

        # 请求逻辑层
        self.send_to_level2(request)

    def change_password_response(self, response):
        """
        逻辑层返回重置密码请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("change password success")
            return 1, "yes"
        else:
            g_log.debug("change password failed, %s:%s", code, message)
            return 1010301, message

    def get_sms_code(self):
        """
        获取短信验证码phoneNumber
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")

        # 生成随机的验证码
        sms_code = generate_verify_code()

        # redis cache验证码，60秒
        sms_code_expire = 30
        connection = get_redis_connection(numbers)
        if not connection:
            raise redis.ConnectionError
        key = "sms_code:%s" % numbers
        g_log.debug("%s:%s:%ss", numbers, sms_code, sms_code_expire)
        connection.set(key, sms_code)
        connection.expire(key, sms_code_expire)
        # TODO... 接入短信平台

        self.get_sms_code_response(sms_code)

    def get_sms_code_response(self, response):
        """
        返回验证码
        :param response: 验证码
        """
        self.write(json.dumps({"c": 1, "r": response}))
        g_log.debug("[account.get_sms_code.response]")
        self.finish()

    def _verify_sms_code(self, numbers, sms_code):
        # redis cache中验证短信验证码
        connection = get_redis_connection(numbers)
        key = "sms_code:%s" % numbers
        value = connection.get(key)
        g_log.debug("%s -> %s, %s", key, value, sms_code)
        if sms_code == value:
            match = "match"
        else:
            match = "not match"
        return match

    def verify_sms_code(self):
        """
        验证验证码
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        sms_code = self.get_argument("sms_code")

        match = self._verify_sms_code(numbers, sms_code)
        self.verify_sms_code_response(match)

    def verify_sms_code_response(self, response):
        """
        """
        self.write(json.dumps({"c": 1, "r": response}))
        g_log.debug("[account.verify_sms_code.response]")
        self.finish()


def generate_verify_code(digits=4):
    """
    生成digits位的数字［0-9］验证码
    :param digits: 多少位
    :return:
    """
    verify_code = []
    while digits > 0:
        verify_code.append(random.choice("0123456789"))
        digits -= 1

    return ''.join(verify_code)


if __name__ == "__main__":
    print(generate_verify_code(4))