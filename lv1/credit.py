# -*- coding: utf-8 -*-
__author__ = 'tracedeng'

from tornado.web import MissingArgumentError, asynchronous
import json
import common_pb2
import log
g_log = log.WrapperLog('stream', name=__name__, level=log.DEBUG).log  # 启动日志功能
from level1_base import Base


class Credit(Base):
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
            features_handle = {"credit_list": self.consumer_fetch_all_credit}
            self.mode = self.get_argument("type", "dummy")
            g_log.debug("[account] receive %s request", self.mode)
            self.code, self.message = features_handle.get(self.mode, self.dummy_command)()
            if self.code not in [40000, 40100, 40200, 40300, 40400, 40500]:
                self.write(json.dumps({"c": self.code, "m": self.message}))
                self.finish()
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 40001, "m": "exception"}))
            self.finish()

    def on_response(self, response):
        try:
            res = super(Credit, self).on_response(response)
            if not res:
                g_log.error("super on_response None")
                self.write(json.dumps({"c": 40002, "m": "exception"}))
            else:
                # features_response = {"register": self.register_response, "login": self.login_response,
                #                      "change_password": self.change_password_response, "get_sms_code": self.get_sms_code,
                #                      "verify_sms_code": self.verify_sms_code}
                features_response = {"credit_list": self.consumer_fetch_all_credit_response}
                g_log.debug("[credit] %s response", self.mode)
                self.code, self.message = features_response.get(self.mode, self.dummy_command)(res)
                if self.code in [40000, 40100, 40200, 40300, 40400, 40500]:
                    self.write(json.dumps({"c": self.code, "r": self.message}))
                else:
                    self.write(json.dumps({"c": self.code, "m": self.message}))
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 40003, "m": "exception"}))
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
        return 40004, "unsupported mode"

    def consumer_fetch_all_credit(self):
        """
        账号注册phoneNumber, password, passwordMd5, kind
        :return:
        """
        try:
            # 解析post参数
            numbers = self.get_argument("phone_number")
            # password = self.get_argument("password")
            # password_md5 = self.get_argument("password_md5")
            g_log.debug("[level2.consumer_fetch_all_credit]")

            # 组请求包
            request = common_pb2.Request()
            request.head.cmd = 306
            request.head.seq = 2
            request.head.numbers = numbers

            body = request.consumer_credit_retrieve_request
            body.numbers = numbers
            # body.password = password
            # body.password_md5 = password_md5

            # 请求逻辑层
            if self.send_to_level2(request):
                return 40201, "platform failed"
            return 40200, "yes"
        except MissingArgumentError as e:
            g_log.error("miss argument %s", e.arg_name)
            g_log.debug("%s", e)
            return 40202, "miss argument"
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            return 40203, "exception"

    def consumer_fetch_all_credit_response(self, response):
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
                # level2返回1为成功，其它认为失败
                g_log.debug("consumer fetch all credit success")
                body = response.consumer_credit_retrieve_response
                aggressive_credit = body.consumer_credit.aggressive_credit
                g_log.debug("consumer has %d merchant", len(aggressive_credit))
                r = []
                for aggressive_credit_one in aggressive_credit:
                    merchant_name = aggressive_credit_one.merchant.name
                    merchant_logo = aggressive_credit_one.merchant.logo
                    total = 0
                    for credit_one in aggressive_credit_one.credit:
                        if credit_one.exchanged == 1:
                            total += credit_one.credit_rest
                    m = {"t": merchant_name, "l": merchant_logo, "a": total}
                    g_log.debug(m)
                    r.append(m)
                return 40200, r
            else:
                g_log.debug("consumer fetch all credit failed, %s:%s", code, message)
                return 40204, message
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            return 40205, "exception"