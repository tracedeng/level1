# -*- coding: utf-8 -*-
__author__ = 'tracedeng'

from tornado.web import MissingArgumentError, asynchronous
import json
import common_pb2
import log
g_log = log.WrapperLog('stream', name=__name__, level=log.DEBUG).log  # 启动日志功能
from level1_base import Base, InvalidArgumentError


class Voucher(Base):
    @asynchronous
    def post(self, *args, **kwargs):
        """
        根据post["type"]分发处理
        :param args:
        :param kwargs:
        :return:
        """
        try:
            features_handle = {"retrieve": self.consumer_retrieve_voucher,
                               "merchant_retrieve": self.merchant_retrieve_voucher,
                               "confirm": self.confirm_voucher}
            self.mode = self.get_argument("type")
            g_log.debug("[voucher.%s.request]", self.mode)
            features_handle.get(self.mode, self.dummy_command)()
        except MissingArgumentError as e:
            # 缺少请求参数
            g_log.error("miss argument %s, %s", e.arg_name, e)
            self.write(json.dumps({"c": 1080001, "m": "miss argument"}))
            g_log.debug("[voucher.%s.response]", self.mode)
            self.finish()
        except InvalidArgumentError as e:
            # 缺少请求参数
            g_log.error("invalid argument %s, %s", e.arg_name, e)
            self.write(json.dumps({"c": 1080008, "m": "invalid argument"}))
            g_log.debug("[voucher.%s.response]", self.mode)
            self.finish()
        except Exception as e:
            # from print_exception import print_exception
            # print_exception()
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 1080002, "m": "exception"}))
            g_log.debug("[voucher.%s.response]", self.mode)
            self.finish()

    def on_response(self, response):
        try:
            super(Voucher, self).on_response(response)
            if not self.response:
                g_log.error("illegal response")
                self.write(json.dumps({"c": 1080003, "m": "exception"}))
            else:
                features_response = {"retrieve": self.consumer_retrieve_voucher_response,
                                     "merchant_retrieve": self.merchant_retrieve_voucher_response,
                                     "confirm": self.confirm_voucher_response}
                self.code, self.message = features_response.get(self.mode, self.dummy_command)(self.response)
                if self.code == 1:
                    self.write(json.dumps({"c": self.code, "r": self.message}))
                else:
                    self.write(json.dumps({"c": self.code, "m": self.message}))
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 1080004, "m": "exception"}))
        g_log.debug("[voucher.%s.response]", self.mode)
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
            return 1080005, "no handler"
        else:
            # 无效的命令
            g_log.debug("unsupported type %s", self.mode)
            self.write(json.dumps({"c": 1080006, "m": "unsupported type"}))
            self.finish()

    def consumer_retrieve_voucher(self):
        """
        用户读取优惠券列表
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        session_key = self.get_argument("session_key", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 801
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.consumer_retrieve_voucher_request
        body.numbers = numbers

        # 请求逻辑层
        self.send_to_level2(request)

    def consumer_retrieve_voucher_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("consumer retrieve voucher success")
            body = response.consumer_retrieve_voucher_response
            r = []
            for merchant_voucher_one in body.merchant_voucher:
                merchant = merchant_voucher_one.merchant
                name = merchant.name
                logo = merchant.logo
                for voucher_one in merchant_voucher_one.vouchers:
                    voucher = {"aid": voucher_one.activity_identity, "id": voucher_one.identity, "na": name,
                               "used": voucher_one.used, "ct": voucher_one.create_time, "et": voucher_one.expire_time,
                               "ti": voucher_one.activity_title, "logo": logo}
                    r.append(voucher)
            return 1, r
        else:
            g_log.debug("retrieve voucher failed, %s:%s", code, message)
            return 1080101, message

    def merchant_retrieve_voucher(self):
        """
        商家读取优惠券列表
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        session_key = self.get_argument("session_key", "")
        merchant_identity = self.get_argument("merchant", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 802
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.merchant_retrieve_voucher_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity

        # 请求逻辑层
        self.send_to_level2(request)

    def merchant_retrieve_voucher_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("merchant retrieve voucher success")
            body = response.merchant_retrieve_voucher_response
            r = []
            for voucher_one in body.vouchers:
                voucher = {"aid": voucher_one.activity_identity, "id": voucher_one.identity, "used": voucher_one.used,
                           "ct": voucher_one.create_time, "et": voucher_one.expire_time,
                           "ti": voucher_one.activity_title}
                r.append(voucher)
            return 1, r
        else:
            g_log.debug("retrieve voucher failed, %s:%s", code, message)
            return 1080201, message

    def confirm_voucher(self):
        """
        商家确认优惠券
        :return:
        """
        # 解析post参数
        manager = self.get_argument("numbers")
        numbers = self.get_argument("consumer")
        session_key = self.get_argument("session_key", "")
        merchant_identity = self.get_argument("merchant", "")
        voucher_identity = self.get_argument("voucher", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 803
        request.head.seq = 2
        request.head.numbers = manager
        request.head.session_key = session_key

        body = request.confirm_voucher_request
        body.numbers = manager
        body.merchant_identity = merchant_identity
        body.voucher_identity = voucher_identity
        body.c_numbers = numbers

        # 请求逻辑层
        self.send_to_level2(request)

    def confirm_voucher_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("confirm voucher success")
            return 1, "yes"
        else:
            g_log.debug("confirm voucher failed, %s:%s", code, message)
            return 1080301, message
