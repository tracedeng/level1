# -*- coding: utf-8 -*-
__author__ = 'tracedeng'

from tornado.web import MissingArgumentError, asynchronous
import json
from urllib import quote
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA
from Crypto.Signature import PKCS1_v1_5
from OpenSSL.crypto import load_privatekey, FILETYPE_PEM, sign
import base64
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
            features_handle = {"retrieve": self.retrieve_credit_flow, "allow": self.merchant_allow_exchange_in,
                               "recharge": self.merchant_recharge, "withdrawals": self.merchant_withdrawals,
                               "balance_record": self.retrieve_balance_record,
                               "balance": self.retrieve_merchant_balance, "trade_no": self.retrieve_trade_no,
                               "notify": self.alipay_async_notify}
            self.mode = self.get_argument("type")
            # g_log.debug("http://%s%s?%s", self.request.host, self.request.path, self.request.arguments)
            if self.mode == "" and self.get_argument("seller_email") == "biiyooit@qq.com":
                g_log.debug("async notify from alipay")
                self.mode = "notify"
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
                                     "allow": self.merchant_allow_exchange_in_response,
                                     "recharge": self.merchant_recharge_response,
                                     "withdrawals": self.merchant_withdrawals_response,
                                     "balance_record": self.retrieve_balance_record_response,
                                     "balance": self.retrieve_merchant_balance_response,
                                     "trade_no": self.retrieve_trade_no_response,
                                     "notify": self.alipay_async_notify_response}
                self.code, self.message = features_response.get(self.mode, self.dummy_command)(self.response)
                if self.mode == "notify":
                    self.write("success")
                else:
                    if self.code == 1:
                        self.write(json.dumps({"c": self.code, "r": self.message}))
                    else:
                        self.write(json.dumps({"c": self.code, "m": self.message}))
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            if self.mode == "notify":
                self.write("success")
            else:
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
                consumption = material.consumption
                balance = material.balance

                m = {"t": merchant_name, "l": merchant_logo, "i": merchant_identity, "up": upper_bound, "is": issued,
                     "mi": may_issued, "in": interchange_in, "out": interchange_out, "co": consumption,
                     "bal": balance}
                # g_log.debug(m)
                r.append(m)
            return 1, r
            # return 1, "yes"
        else:
            g_log.debug("retrieve credit flow failed, %s:%s", code, message)
            return 1060101, message

    def merchant_allow_exchange_in(self):
        """
        商家允许积分转入
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        merchant_identity = self.get_argument("merchant", "")
        session_key = self.get_argument("session_key", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 502
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.merchant_allow_exchange_in_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity

        # 请求逻辑层
        self.send_to_level2(request)

    def merchant_allow_exchange_in_response(self, response):
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            # level2返回1为成功，其它认为失败
            g_log.debug("merchant allow exchange in success")
            body = response.merchant_allow_exchange_in_response
            return 1, body.allow
        else:
            g_log.debug("merchant allow exchange in failed, %s:%s", code, message)
            return 1060201, message

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
        trade_no = self.get_argument("trade_no", "")

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
        body.trade_no = trade_no

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

    def merchant_withdrawals(self):
        """
        商家提现
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        money = self.get_argument("money", "0")
        merchant_identity = self.get_argument("merchant", "")
        session_key = self.get_argument("session_key", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 504
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.merchant_withdrawals_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity
        body.money = int(money)

        # 请求逻辑层
        self.send_to_level2(request)

    def merchant_withdrawals_response(self, response):
        """
        逻辑层返回登录请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("withdrawals success")
            return 1, "yes"
        else:
            g_log.debug("withdrawals failed, %s:%s", code, message)
            return 1060401, message

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
                    record.append({"mo": record_one.money, "ti": record_one.time, "op": record_one.operator,
                                   "di": record_one.direction})
                m = {"t": merchant_name, "l": merchant_logo, "i": merchant_identity, "a": record}
                # g_log.debug(m)
                r.append(m)
            return 1, r
        else:
            g_log.debug("retrieve balance record failed, %s:%s", code, message)
            return 1060501, message

    def retrieve_merchant_balance(self):
        """
        读取商家帐户余额
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        merchant_identity = self.get_argument("merchant", "")
        session_key = self.get_argument("session_key", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 506
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.merchant_balance_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity

        # 请求逻辑层
        self.send_to_level2(request)

    def retrieve_merchant_balance_response(self, response):
        """
        逻辑层返回登录请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("retrieve balance success")
            body = response.merchant_balance_response
            balance = body.balance
            g_log.debug("merchant balance %d", balance)

            return 1, balance
        else:
            g_log.debug("retrieve balance failed, %s:%s", code, message)
            return 1060601, message

    def retrieve_trade_no(self):
        """
        请求商家充值订单号
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        money = self.get_argument("money", "0")
        merchant_identity = self.get_argument("merchant", "")
        session_key = self.get_argument("session_key", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 507
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.merchant_recharge_trade_no_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity
        body.money = int(money)

        # 请求逻辑层
        self.send_to_level2(request)

    def retrieve_trade_no_response(self, response):
        """
        逻辑层返回登录请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("query recharge trade no success")
            body = response.merchant_recharge_trade_no_response
            trade_no = body.trade_no
            # with open('./rsa_private_key_pkcs8.pem', 'r') as f:
            #     key = f.read()      # pkcs8私钥
            #     g_log.debug(key)
            money = self.get_argument("money", "0")
            # g_log.debug(money)
            order = {"partner": "\"2088221780225801\"", "seller_id": "\"biiyooit@qq.com\"", "out_trade_no": "\"%s\"" % trade_no,
                     "subject": "\"charge\"", "body": "\"charge\"", "total_fee": "\"%s\"" % money,
                     "notify_url": "\"http://www.weijifen.me:8000/flow\"", "service": "\"mobile.securitypay.pay\"",
                     "payment_type": "\"1\"", "_input_charset": "\"utf-8\"", "it_b_pay": "\"30m\""}
            g_log.debug(order)
            sign = rsa_order(order)
            return 1, {"trade_no": trade_no, "sign": sign}
        else:
            g_log.debug("query trade no failed, %s:%s", code, message)
            return 1060701, message

    def check_rsa_sign(self):
        """
        检查rsa签名
        :return:True/有效，False/无效
        """
        try:
            sign = self.get_argument("sign", "")

            query = self.request.arguments
            query.pop("sign")
            query.pop("sign_type")
            plain = ""
            for key in sorted(query):
                plain += "&%s=%s" % (key, query[key][0])
            g_log.debug(plain)
            verifier = PKCS1_v1_5.new(RSA.importKey(open('./rsa_alipay_public_key.pem', 'r').read()))
            if verifier.verify(SHA.new(plain[1:]), base64.b64decode(sign)):
                return True

            return False
        except Exception as e:
            g_log.error("%s", e)
            return False

    def alipay_async_notify(self):
        """
        请求商家充值订单号
        :return:
        """
        # 检查签名
        sign_type = self.get_argument("sign_type", "RSA")
        if sign_type.upper() != "RSA":
            g_log.debug("check sign failed, invalid sign type %s", sign_type)
            self.write("success")
            self.finish()
            return

        if not self.check_rsa_sign():
            g_log.debug("check notify sign failed")
            self.write("success")
            self.finish()
            return

        # 解析post参数
        trade_status = self.get_argument("trade_status")
        sign = self.get_argument("sign", "")
        notify_type = self.get_argument("notify_type", "")
        notify_id = self.get_argument("notify_id", "")
        buyer_id = self.get_argument("buyer_id", "")
        buyer_email = self.get_argument("buyer_email", "")
        out_trade_no = self.get_argument("out_trade_no", "")
        trade_no = self.get_argument("trade_no", "")
        seller_email = self.get_argument("seller_email", "")
        seller_id = self.get_argument("seller_id", "")
        total_fee = self.get_argument("total_fee", "0")
        notify_time = self.get_argument("notify_time", "")
        gmt_create = self.get_argument("gmt_create", "")
        gmt_payment = self.get_argument("gmt_payment", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 508
        request.head.seq = 2

        body = request.alipay_async_notify_request
        body.trade_status = trade_status
        body.sign_type = sign_type
        body.sign = sign
        body.notify_type = notify_type
        body.notify_id = notify_id
        body.buyer_id = buyer_id
        body.buyer_email = buyer_email
        body.out_trade_no = out_trade_no
        body.trade_no = trade_no
        body.seller_email = seller_email
        body.seller_id = seller_id
        # body.total_fee = 1 if float(total_fee) < 1.0 else int(total_fee)
        body.total_fee = int(float(total_fee))
        body.notify_time = notify_time
        body.gmt_create = gmt_create
        body.gmt_payment = gmt_payment

        # 请求逻辑层
        self.send_to_level2(request)

    def alipay_async_notify_response(self, response):
        """
        逻辑层返回登录请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("deal alipay async notify success")
            return 1, "yes"
        else:
            g_log.debug("deal alipay async notify failed, %s:%s", code, message)
            return 1060801, message


def rsa_order(order):
    """
    订单rsa加密
    :return:
    """
    # order = {"partner": "2088221780225801", "seller_id": "biiyooit@qq.com", "out_trade_no": trade_no,
    #          "subject": "charge", "body": "charge", "total_fee": str(money),
    #          "notify_url": "http://www.weijifen.me:8000/flow", "service": "mobile.securitypay.pay",
    #          "payment_type": "1", "_input_charset": "utf-8", "it_b_pay": "30m"}

    # g_log.debug(order)
    plain = ""
    for key in sorted(order):
        # g_log.debug("%s=%s", key, order[key])
        plain += "&%s=%s" % (key, order[key])
        # g_log.debug(plain)

    # g_log.debug(plain[1:])
    # cipher = PKCS1_v1_5_ENCRYPT.new(RSA.importKey(open('./rsa_private_key_pkcs8.pem', 'r').read()))
    # cipher = base64.b64encode(cipher.encrypt(plain))
    # return base64.b64encode(cipher.encrypt(plain[1:]))
    key = load_privatekey(FILETYPE_PEM, open("rsa_private_key_pkcs8.pem").read())
    cipher = sign(key, plain[1:], 'sha1')
    return quote(base64.b64encode(cipher))