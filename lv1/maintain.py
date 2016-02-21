# -*- coding: utf-8 -*-
__author__ = 'tracedeng'

from tornado.web import MissingArgumentError, asynchronous
import json
import common_pb2
import log
g_log = log.WrapperLog('stream', name=__name__, level=log.DEBUG).log  # 启动日志功能
from level1_base import Base, InvalidArgumentError


class Maintain(Base):
    @asynchronous
    def post(self, *args, **kwargs):
        """
        根据post["type"]分发处理
        :param args:
        :param kwargs:
        :return:
        """
        try:
            features_handle = {"version": self.version_report,
                               "boot": self.boot_report,
                               "active": self.active_report,
                               "feedback": self.feed_back}
            self.mode = self.get_argument("type")
            g_log.debug("[maintain.%s.request]", self.mode)
            features_handle.get(self.mode, self.dummy_command)()
        except MissingArgumentError as e:
            # 缺少请求参数
            g_log.error("miss argument %s, %s", e.arg_name, e)
            self.write(json.dumps({"c": 1090001, "m": "miss argument"}))
            g_log.debug("[maintain.%s.response]", self.mode)
            self.finish()
        except InvalidArgumentError as e:
            # 缺少请求参数
            g_log.error("invalid argument %s, %s", e.arg_name, e)
            self.write(json.dumps({"c": 1090008, "m": "invalid argument"}))
            g_log.debug("[maintain.%s.response]", self.mode)
            self.finish()
        except Exception as e:
            # from print_exception import print_exception
            # print_exception()
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 1090002, "m": "exception"}))
            g_log.debug("[maintain.%s.response]", self.mode)
            self.finish()

    def on_response(self, response):
        try:
            super(Maintain, self).on_response(response)
            if not self.response:
                g_log.error("illegal response")
                self.write(json.dumps({"c": 1090003, "m": "exception"}))
            else:
                features_response = {"version": self.version_report_response,
                                     "boot": self.boot_report_response,
                                     "active": self.active_report_response,
                                     "feedback": self.feed_back_response}
                self.code, self.message = features_response.get(self.mode, self.dummy_command)(self.response)
                if self.code == 1:
                    self.write(json.dumps({"c": self.code, "r": self.message}))
                else:
                    self.write(json.dumps({"c": self.code, "m": self.message}))
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 1090004, "m": "exception"}))
        g_log.debug("[maintain.%s.response]", self.mode)
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
            return 1090005, "no handler"
        else:
            # 无效的命令
            g_log.debug("unsupported type %s", self.mode)
            self.write(json.dumps({"c": 1090006, "m": "unsupported type"}))
            self.finish()

    def version_report(self):
        """
        版本上报
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        session_key = self.get_argument("session_key", "")
        version = self.get_argument("version", "N/A")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 901
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.version_report_request
        body.numbers = numbers
        body.version = version

        # 请求逻辑层
        self.send_to_level2(request)

    def version_report_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("version report success")
            return 1, "yes"
        else:
            g_log.debug("version report failed, %s:%s", code, message)
            return 1090101, message

    def boot_report(self):
        """
        app启动上报
        :return:
        """
        # 解析post参数
        # numbers = self.get_argument("numbers")
        # session_key = self.get_argument("session_key", "")
        version = self.get_argument("version", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 902
        request.head.seq = 2
        # request.head.numbers = numbers
        # request.head.session_key = session_key

        body = request.boot_report_request
        body.version = version

        # 请求逻辑层
        self.send_to_level2(request)

    def boot_report_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("boot report success")
            return 1, "yes"
        else:
            g_log.debug("boot report failed, %s:%s", code, message)
            return 1090201, message

    def active_report(self):
        """
        商家确认优惠券
        :return:
        """
        # 解析post参数
        manager = self.get_argument("numbers")
        numbers = self.get_argument("consumer")
        session_key = self.get_argument("session_key", "")
        merchant_identity = self.get_argument("merchant", "")
        maintain_identity = self.get_argument("maintain", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 903
        request.head.seq = 2
        request.head.numbers = manager
        request.head.session_key = session_key

        body = request.confirm_maintain_request
        body.numbers = manager
        body.merchant_identity = merchant_identity
        body.maintain_identity = maintain_identity
        body.c_numbers = numbers

        # 请求逻辑层
        self.send_to_level2(request)

    def active_report_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("active report success")
            return 1, "yes"
        else:
            g_log.debug("active report failed, %s:%s", code, message)
            return 1090301, message

    def feed_back(self):
        """
        商家确认优惠券
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        version = self.get_argument("version", "N/A")
        session_key = self.get_argument("session_key", "")
        mode = self.get_argument("mode", "consumer")
        feedback = self.get_argument("feedback", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 904
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.feed_back_request
        body.numbers = numbers
        body.version = version
        body.mode = mode
        body.feedback = feedback

        # 请求逻辑层
        self.send_to_level2(request)

    def feed_back_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("feedback report success")
            return 1, "yes"
        else:
            g_log.debug("feedback report failed, %s:%s", code, message)
            return 1090401, message
