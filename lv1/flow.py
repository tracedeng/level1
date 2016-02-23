# -*- coding: utf-8 -*-
__author__ = 'tracedeng'

from tornado.web import MissingArgumentError, asynchronous
import json
import common_pb2
import log
g_log = log.WrapperLog('stream', name=__name__, level=log.DEBUG).log  # 启动日志功能
from level1_base import Base, InvalidArgumentError


class Flow(Base):
    @asynchronous
    def post(self, *args, **kwargs):
        """
        根据post["type"]分发处理
        :param args:
        :param kwargs:
        :return:
        """
        try:
            features_handle = {"retrieve": self.retrieve_credit_flow, "settlement": self.merchant_settlement,
                               "recharge": self.merchant_recharge, "balance_record": self.retrieve_balance_record}

            self.mode = self.get_argument("type")
            g_log.debug("[flow.%s.request]", self.mode)
            features_handle.get(self.mode, self.dummy_command)()
        except MissingArgumentError as e:
            # 缺少请求参数
            g_log.error("miss argument %s, %s", e.arg_name, e)
            self.write(json.dumps({"c": 1060001, "m": "miss argument"}))
            g_log.debug("[flow.%s.response]", self.mode)
            self.finish()
        except InvalidArgumentError as e:
            # 无效请求参数
            g_log.error("invalid argument %s, %s", e.arg_name, e)
            self.write(json.dumps({"c": 1060008, "m": "invalid argument"}))
            g_log.debug("[flow.%s.response]", self.mode)
            self.finish()
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 1060002, "m": "exception"}))
            g_log.debug("[flow.%s.response]", self.mode)
            self.finish()

    def on_response(self, response):
        try:
            super(Flow, self).on_response(response)
            if not self.response:
                g_log.error("illegal response")
                self.write(json.dumps({"c": 1060003, "m": "exception"}))
            else:
                features_response = {"retrieve": self.retrieve_credit_flow_response,
                                     "settlement": self.merchant_settlement_response,
                                     "recharge": self.merchant_recharge_response,
                                     "balance_record": self.retrieve_balance_record_response}
                self.code, self.message = features_response.get(self.mode, self.dummy_command)(self.response)
                if self.code == 1:
                    self.write(json.dumps({"c": self.code, "r": self.message}))
                else:
                    self.write(json.dumps({"c": self.code, "m": self.message}))
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 1060004, "m": "exception"}))
        g_log.debug("[flow.%s.response]", self.mode)
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
            return 1060005, "no handler"
        else:
            # 无效的命令
            g_log.debug("unsupported type %s", self.mode)
            self.write(json.dumps({"c": 1060006, "m": "unsupported type"}))
            self.finish()

    def retrieve_credit_flow(self):
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
        request.head.cmd = 501
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.merchant_credit_flow_retrieve_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity

        # 请求逻辑层
        self.send_to_level2(request)

    def retrieve_credit_flow_response(self, response):
        """
        逻辑层返回登录请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            # level2 成功返回
            g_log.debug("retrieve credit flow success")
            body = response.merchant_credit_flow_retrieve_response
            credit_flow = body.credit_flow
            g_log.debug("has %d merchant", len(credit_flow))
            r = []
            for credit_flow_one in credit_flow:
                merchant_name = credit_flow_one.merchant.name
                merchant_logo = credit_flow_one.merchant.logo
                merchant_identity = credit_flow_one.merchant.identity
                # flow = flow_record_one
                material = credit_flow_one.material
                upper_bound = material.upper_bound
                may_issued = material.may_issued
                issued = material.issued
                interchange_in = material.interchange_in
                interchange_out = material.interchange_out
                interchange_consumption = material.interchange_consumption
                settlement = material.settlement

                m = {"t": merchant_name, "l": merchant_logo, "i": merchant_identity, "up": upper_bound, "is": issued,
                     "mi": may_issued, "in": interchange_in, "out": interchange_out, "ic": interchange_consumption,
                     "se": settlement}
                # g_log.debug(m)
                r.append(m)
            return 1, r
            # return 1, "yes"
        else:
            g_log.debug("retrieve credit flow failed, %s:%s", code, message)
            return 1060101, message

    def merchant_settlement(self):
        """
        商家结算
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        merchant_identity = self.get_argument("merchant", "")
        session_key = self.get_argument("session_key", "")
        exec_settlement = self.get_argument("exec_settlement", "0")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 502
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.merchant_settlement_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity
        body.exec_settlement = int(exec_settlement)

        # 请求逻辑层
        self.send_to_level2(request)

    def merchant_settlement_response(self, response):
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            # level2返回1为成功，其它认为失败
            g_log.debug("merchant settlement success")
            body = response.merchant_settlement_response
            return 1, body.settlement
        else:
            g_log.debug("merchant settlement failed, %s:%s", code, message)
            return 1060601, message

    def merchant_recharge(self):
        """
        商家充值
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        money = self.get_argument("money", "0")
        merchant_identity = self.get_argument("merchant", "")
        session_key = self.get_argument("session_key", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 503
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.merchant_recharge_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity
        body.money = int(money)

        # 请求逻辑层
        self.send_to_level2(request)

    def merchant_recharge_response(self, response):
        """
        逻辑层返回登录请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("recharge  success")
            return 1, "yes"
        else:
            g_log.debug("recharge failed, %s:%s", code, message)
            return 1060301, message

    def retrieve_balance_record(self):
        """
        商家更新消费兑换积分比例
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        merchant_identity = self.get_argument("merchant", "")
        session_key = self.get_argument("session_key", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 505
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.merchant_balance_record_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity

        # 请求逻辑层
        self.send_to_level2(request)

    def retrieve_balance_record_response(self, response):
        """
        逻辑层返回登录请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("retrieve balance record success")
            body = response.merchant_balance_record_response
            balance_record = body.balance_record
            g_log.debug("consumer has %d merchant", len(balance_record))
            r = []
            for balance_record_one in balance_record:
                merchant_name = balance_record_one.merchant.name
                merchant_logo = balance_record_one.merchant.logo
                merchant_identity = balance_record_one.merchant.identity
                record = []
                for record_one in balance_record_one.aggressive_record:
                    record.append({"mo": record_one.money, "ti": record_one.time, "op": record_one.operator})
                m = {"t": merchant_name, "l": merchant_logo, "i": merchant_identity, "a": record}
                # g_log.debug(m)
                r.append(m)
            return 1, r
        else:
            g_log.debug("retrieve balance record failed, %s:%s", code, message)
            return 1060501, message