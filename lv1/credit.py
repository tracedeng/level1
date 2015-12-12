# -*- coding: utf-8 -*-
__author__ = 'tracedeng'

from tornado.web import MissingArgumentError, asynchronous
import json
import common_pb2
import log
g_log = log.WrapperLog('stream', name=__name__, level=log.DEBUG).log  # 启动日志功能
from level1_base import Base, InvalidArgumentError


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
            features_handle = {"consumption": self.create_consumption,
                               "credit_list_m": self.merchant_fetch_all_credit,
                               "credit_list": self.consumer_fetch_all_credit,
                               "credit_list_of_merchant": self.consumer_fetch_credit_of_merchant,
                               "credit_detail": self.consumer_fetch_credit_detail}
            self.mode = self.get_argument("type")
            g_log.debug("[credit.%s.request]", self.mode)
            features_handle.get(self.mode, self.dummy_command)()
        except MissingArgumentError as e:
            # 缺少请求参数
            g_log.error("miss argument %s, %s", e.arg_name, e)
            self.write(json.dumps({"c": 40001, "m": "miss argument"}))
            g_log.debug("[credit.%s.response]", self.mode)
            self.finish()
        except InvalidArgumentError as e:
            # 缺少请求参数
            g_log.error("invalid argument %s, %s", e.arg_name, e)
            self.write(json.dumps({"c": 40008, "m": "invalid argument"}))
            g_log.debug("[credit.%s.response]", self.mode)
            self.finish()
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 40002, "m": "exception"}))
            g_log.debug("[credit.%s.response]", self.mode)
            self.finish()

    def on_response(self, response):
        try:
            super(Credit, self).on_response(response)
            if not self.response:
                g_log.error("illegal response")
                self.write(json.dumps({"c": 40003, "m": "exception"}))
            else:
                features_response = {"credit_list": self.consumer_fetch_all_credit_response,
                                     "create_consumption": self.create_consumption_response,
                                     "credit_list_of_merchant": self.consumer_fetch_credit_of_merchant_response,
                                     "credit_detail": self.consumer_fetch_credit_detail_response}
                self.code, self.message = features_response.get(self.mode, self.dummy_command)(self.response)
                if self.code == 1:
                    self.write(json.dumps({"c": self.code, "r": self.message}))
                else:
                    self.write(json.dumps({"c": self.code, "m": self.message}))
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 40004, "m": "exception"}))
        g_log.debug("[credit.%s.response]", self.mode)
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
            return 10005, "no handler"
        else:
            # 无效的命令
            g_log.debug("unsupported type %s", self.mode)
            self.write(json.dumps({"c": 10006, "m": "unsupported type"}))
            self.finish()

    def consumer_fetch_all_credit(self):
        """
        获取用户拥有的所有积分总量列表 phoneNumber
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 306
        request.head.seq = 2
        request.head.numbers = numbers

        body = request.consumer_credit_retrieve_request
        body.numbers = numbers

        # 请求逻辑层
        self.send_to_level2(request)

    def consumer_fetch_all_credit_response(self, response):
        """
        逻辑层返回后处理
        :param response: pb格式回包
        """
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
                merchant_identity = aggressive_credit_one.merchant.identity
                total = 0
                for credit_one in aggressive_credit_one.credit:
                    if credit_one.exchanged == 1:
                        total += credit_one.credit_rest
                m = {"t": merchant_name, "l": merchant_logo, "a": total, "i": merchant_identity}
                g_log.debug(m)
                r.append(m)
            return 1, r
        else:
            g_log.debug("consumer fetch all credit failed, %s:%s", code, message)
            return 40201, message

    def create_consumption(self):
        """
        获取用户拥有的所有积分总量列表 phoneNumber
        :return:
        """
        # 解析post参数
        # g_log.debug(self.request.query_arguments)
        numbers = self.get_argument("numbers")
        merchant_identity = self.get_argument("merchant")
        sums = self.get_argument("sums")
        session_key = self.get_argument("session_key", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 301
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.consumption_create_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity
        body.sums = int(sums)

        # 请求逻辑层
        self.send_to_level2(request)

    def create_consumption_response(self, response):
        """
        逻辑层返回后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            # level2返回1为成功，其它认为失败
            g_log.debug("create consumption record success")
            body = response.consumption_create_response
            r = body.credit_identity
            return 1, r
        else:
            g_log.debug("create consumption record failed, %s:%s", code, message)
            return 1040101, message

    def consumer_fetch_credit_of_merchant(self):
        """
        获取用户拥有的某商家积分列表 phoneNumber
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        merchant_identity = self.get_argument("merchant")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 306
        request.head.seq = 2
        request.head.numbers = numbers

        body = request.consumer_credit_retrieve_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity

        # 请求逻辑层
        self.send_to_level2(request)

    def consumer_fetch_credit_of_merchant_response(self, response):
        """
        逻辑层返回后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            # level2返回1为成功，其它认为失败
            g_log.debug("consumer fetch all credit success")
            body = response.consumer_credit_retrieve_response
            aggressive_credit = body.consumer_credit.aggressive_credit
            g_log.debug("consumer has %d merchant", len(aggressive_credit))
            r = {}
            for aggressive_credit_one in aggressive_credit:
                merchant_name = aggressive_credit_one.merchant.name
                merchant_logo = aggressive_credit_one.merchant.logo
                merchant_identity = aggressive_credit_one.merchant.identity
                merchant = {"t": merchant_name, "l": merchant_logo, "i": merchant_identity}
                total = 0
                credit_list = []
                for credit_one in aggressive_credit_one.credit:
                    #uint32 gift = 1;        // 是否赠送
                    #
                    # uint32 sums = 2;
                    # string consumption_time = 3;
                    #
                    # uint32 exchanged = 4;   // 是否兑换成积分，yes、no、exchange、refuse
                    # uint64 credit = 5;
                    # string manager_numbers = 6;
                    # string exchange_time = 7;
                    #
                    # uint64 credit_rest = 8; // 还剩多少积分
                    #
                    # string numbers = 10;
                    credit = {"i": credit_one.identity, "e": credit_one.exchanged, "am": credit_one.credit_rest,
                              "ct": credit_one.exchange_time, "et": credit_one.exchange_time}
                    if credit_one.exchanged == 1:
                        total += credit_one.credit_rest
                    credit_list.append(credit)
                merchant["a"] = total
                r = {"m": merchant, "c": credit_list}
                break
            # g_log.debug(r)
            return 1, r
        else:
            g_log.debug("consumer fetch all credit failed, %s:%s", code, message)
            return 40201, message

    def consumer_fetch_credit_detail(self):
        """
        获取用户拥有的所有积分总量列表 phoneNumber
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 306
        request.head.seq = 2
        request.head.numbers = numbers

        body = request.consumer_credit_retrieve_request
        body.numbers = numbers

        # 请求逻辑层
        self.send_to_level2(request)

    def consumer_fetch_credit_detail_response(self, response):
        """
        逻辑层返回后处理
        :param response: pb格式回包
        """
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
                merchant_identity = aggressive_credit_one.merchant.identity
                total = 0
                for credit_one in aggressive_credit_one.credit:
                    if credit_one.exchanged == 1:
                        total += credit_one.credit_rest
                m = {"t": merchant_name, "l": merchant_logo, "a": total, "i": merchant_identity}
                g_log.debug(m)
                r.append(m)
            return 1, r
        else:
            g_log.debug("consumer fetch all credit failed, %s:%s", code, message)
            return 40201, message