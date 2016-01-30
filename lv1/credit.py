# -*- coding: utf-8 -*-
__author__ = 'tracedeng'

from tornado.web import MissingArgumentError, asynchronous
import json
import common_pb2
import log
g_log = log.WrapperLog('stream', name=__name__, level=log.DEBUG).log  # 启动日志功能
from level1_base import Base, InvalidArgumentError


class Credit(Base):
    def __init__(self, *args, **kwargs):
        Base.__init__(self, *args, **kwargs)
        self.merchant_exclude = ""

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
                               "credit_list": self.consumer_fetch_all_credit,
                               "credit_list_of_merchant": self.consumer_fetch_credit_of_merchant,
                               "credit_list_detail": self.consumer_fetch_all_credit_detail,
                               "credit_list_m": self.merchant_fetch_all_credit,
                               "credit_list_m_of_consumer": self.merchant_fetch_credit_of_consumer,
                               "apply_list_m": self.merchant_fetch_apply_credit,
                               "credit_detail": self.consumer_fetch_credit_detail,
                               "confirm": self.confirm_apply_credit, "refuse": self.refuse_apply_credit,
                               "interchange": self.credit_interchange}
            self.mode = self.get_argument("type")
            g_log.debug("[credit.%s.request]", self.mode)
            features_handle.get(self.mode, self.dummy_command)()
        except MissingArgumentError as e:
            # 缺少请求参数
            g_log.error("miss argument %s, %s", e.arg_name, e)
            self.write(json.dumps({"c": 1040001, "m": "miss argument"}))
            g_log.debug("[credit.%s.response]", self.mode)
            self.finish()
        except InvalidArgumentError as e:
            # 缺少请求参数
            g_log.error("invalid argument %s, %s", e.arg_name, e)
            self.write(json.dumps({"c": 1040008, "m": "invalid argument"}))
            g_log.debug("[credit.%s.response]", self.mode)
            self.finish()
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 1040002, "m": "exception"}))
            g_log.debug("[credit.%s.response]", self.mode)
            self.finish()

    def on_response(self, response):
        try:
            super(Credit, self).on_response(response)
            if not self.response:
                g_log.error("illegal response")
                self.write(json.dumps({"c": 1040003, "m": "exception"}))
            else:
                features_response = {"consumption": self.create_consumption_response,
                                     "credit_list": self.consumer_fetch_all_credit_response,
                                     "credit_list_of_merchant": self.consumer_fetch_credit_of_merchant_response,
                                     "credit_list_detail": self.consumer_fetch_all_credit_detail_response,
                                     "credit_list_m": self.merchant_fetch_all_credit_response,
                                     "credit_list_m_of_consumer": self.merchant_fetch_credit_of_consumer_response,
                                     "apply_list_m": self.merchant_fetch_apply_credit_response,
                                     "credit_detail": self.consumer_fetch_credit_detail_response,
                                     "confirm": self.confirm_apply_credit_response,
                                     "refuse": self.refuse_apply_credit_response,
                                     "interchange": self.credit_interchange_response}

                self.code, self.message = features_response.get(self.mode, self.dummy_command)(self.response)
                if self.code == 1:
                    self.write(json.dumps({"c": self.code, "r": self.message}))
                else:
                    self.write(json.dumps({"c": self.code, "m": self.message}))
        except Exception as e:
            from print_exception import print_exception
            print_exception()
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 1040004, "m": "exception"}))
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
            return 1040005, "no handler"
        else:
            # 无效的命令
            g_log.debug("unsupported type %s", self.mode)
            self.write(json.dumps({"c": 1040006, "m": "unsupported type"}))
            self.finish()

    def create_consumption(self):
        """
        生成一笔消费
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

    def consumer_fetch_all_credit(self):
        """
        获取用户拥有的所有积分总量列表，不统计消费金
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        session_key = self.get_argument("session_key", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 306
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

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
                has_un_exchanged = 0  # 有未兑换消费
                for credit_one in aggressive_credit_one.credit:
                    if credit_one.exchanged == 1:
                        total += credit_one.credit_rest
                    else:
                        has_un_exchanged = 1
                if total == 0 and has_un_exchanged == 0:
                    # 积分券全部消费完毕并且没有未兑换消费，不显示
                    continue
                m = {"t": merchant_name, "l": merchant_logo, "a": total, "i": merchant_identity}
                g_log.debug(m)
                r.append(m)
            return 1, r
        else:
            g_log.debug("consumer fetch all credit failed, %s:%s", code, message)
            return 1040201, message

    def consumer_fetch_credit_of_merchant(self):
        """
        获取用户拥有的某商家积分列表，包括消费记录
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        merchant_identity = self.get_argument("merchant")
        session_key = self.get_argument("session_key", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 306
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

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
                    credit = {"i": credit_one.identity, "e": credit_one.exchanged, "am": credit_one.credit_rest,
                              "ct": credit_one.exchange_time, "et": credit_one.exchange_time, "s": credit_one.sums}
                    if credit_one.exchanged == 1:
                        # 已用完的积分不展示
                        if credit_one.credit_rest == 0:
                            continue
                        total += credit_one.credit_rest
                    credit_list.append(credit)
                merchant["a"] = total
                r = {"m": merchant, "c": credit_list}
                break
            # g_log.debug(r)
            return 1, r
        else:
            g_log.debug("consumer fetch all credit failed, %s:%s", code, message)
            return 1040202, message

    def consumer_fetch_all_credit_detail(self):
        """
        获取用户拥有的所有积分总量列表，不统计消费金
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        session_key = self.get_argument("session_key", "")
        self.merchant_exclude = self.get_argument("merchant", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 306
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.consumer_credit_retrieve_request
        body.numbers = numbers

        # 请求逻辑层
        self.send_to_level2(request)

    def consumer_fetch_all_credit_detail_response(self, response):
        """
        逻辑层返回后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            # level2返回1为成功，其它认为失败
            g_log.debug("consumer fetch all credit detail success")
            body = response.consumer_credit_retrieve_response
            aggressive_credit = body.consumer_credit.aggressive_credit
            g_log.debug("consumer has %d merchant", len(aggressive_credit))
            r = []
            for aggressive_credit_one in aggressive_credit:
                # 未认证的商家不支持互换
                # if "no" == aggressive_credit_one.merchant.verified:
                #     continue
                if self.merchant_exclude == aggressive_credit_one.merchant.identity:
                    continue
                merchant_name = aggressive_credit_one.merchant.name
                merchant_logo = aggressive_credit_one.merchant.logo
                merchant_identity = aggressive_credit_one.merchant.identity
                total = 0
                credit = []
                for credit_one in aggressive_credit_one.credit:
                    if credit_one.exchanged == 1:
                        total += credit_one.credit_rest

                    # 测试时都返回
                    if credit_one.credit_rest == 0:
                        continue
                    credit.append({"et": credit_one.expire_time, "id": credit_one.identity,
                                   "qu": credit_one.credit_rest})
                # 消费阶段的数据不返回
                if total == 0:
                    continue
                m = {"t": merchant_name, "l": merchant_logo, "a": total, "i": merchant_identity, "cr": credit}
                r.append(m)
                g_log.debug(m)
            return 1, r
        else:
            g_log.debug("consumer fetch all credit failed, %s:%s", code, message)
            return 1040201, message

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

    def merchant_fetch_all_credit(self):
        # 解析post参数
        numbers = self.get_argument("numbers")
        merchant_identity = self.get_argument("merchant")
        session_key = self.get_argument("session_key", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 302
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.merchant_credit_retrieve_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity

        # 请求逻辑层
        self.send_to_level2(request)

    def merchant_fetch_all_credit_response(self, response):
        """
        逻辑层返回后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            # level2返回1为成功，其它认为失败
            g_log.debug("merchant fetch all credit success")
            body = response.merchant_credit_retrieve_response
            aggressive_credit = body.merchant_credit[0].aggressive_credit
            # g_log.debug(aggressive_credit)
            # g_log.debug("consumer has %d merchant", len(aggressive_credit))
            r = []
            for aggressive_credit_one in aggressive_credit:
                nickname = aggressive_credit_one.consumer.nickname
                avatar = aggressive_credit_one.consumer.avatar
                numbers = aggressive_credit_one.consumer.numbers
                identity = aggressive_credit_one.consumer.identity
                # merchant_identity = aggressive_credit_one.merchant.identity
                total = 0
                for credit_one in aggressive_credit_one.credit:
                    if credit_one.exchanged == 1:
                        total += credit_one.credit_rest
                credit = {"nu": numbers, "ni": nickname, "ava": avatar, "cid": identity, "a": total}
                r.append(credit)
            return 1, r
        else:
            g_log.debug("merchant fetch all credit failed, %s:%s", code, message)
            return 1040202, message

    def merchant_fetch_credit_of_consumer(self):
        # 解析post参数
        numbers = self.get_argument("numbers")
        merchant_identity = self.get_argument("merchant")
        consumer_numbers = self.get_argument("consumer")
        session_key = self.get_argument("session_key", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 302
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.merchant_credit_retrieve_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity
        body.consumer_numbers = consumer_numbers

        # 请求逻辑层
        self.send_to_level2(request)

    def merchant_fetch_credit_of_consumer_response(self, response):
        """
        逻辑层返回后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            # level2返回1为成功，其它认为失败
            g_log.debug("merchant fetch all credit success")
            body = response.merchant_credit_retrieve_response
            aggressive_credit = body.merchant_credit[0].aggressive_credit
            g_log.debug(aggressive_credit)
            # g_log.debug("consumer has %d merchant", len(aggressive_credit))
            r = []
            for aggressive_credit_one in aggressive_credit:
                # nickname = aggressive_credit_one.consumer.nickname
                # avatar = aggressive_credit_one.consumer.avatar
                # merchant_identity = aggressive_credit_one.merchant.identity
                total = 0
                for credit_one in aggressive_credit_one.credit:
                    if credit_one.exchanged == 1:
                        total += credit_one.credit_rest
                        credit = {"qu": credit_one.credit_rest, "et": credit_one.expire_time, "cid": credit_one.identity}
                        r.append(credit)
                # 只处理一个用户的积分
                break
            return 1, r
        else:
            g_log.debug("merchant fetch all credit failed, %s:%s", code, message)
            return 1040202, message

    def merchant_fetch_apply_credit(self):
        # 解析post参数
        numbers = self.get_argument("numbers")
        # merchant_identity = self.get_argument("merchant")
        session_key = self.get_argument("session_key", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 302
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.merchant_credit_retrieve_request
        body.numbers = numbers
        # body.merchant_identity = merchant_identity

        # 请求逻辑层
        self.send_to_level2(request)

    def merchant_fetch_apply_credit_response(self, response):
        """
        逻辑层返回后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            # level2返回1为成功，其它认为失败
            g_log.debug("merchant fetch apply credit success")
            body = response.merchant_credit_retrieve_response
            aggressive_credit = body.merchant_credit[0].aggressive_credit
            # g_log.debug("merchant has %d apply", len(aggressive_credit))
            credit_list = []
            for aggressive_credit_one in aggressive_credit:
                consumer_nickname = aggressive_credit_one.consumer.nickname
                consumer_avatar = aggressive_credit_one.consumer.avatar

                for credit_one in aggressive_credit_one.credit:
                    # credit = {}
                    if credit_one.exchanged == 0:
                        credit = {"ni": consumer_nickname, "ava": consumer_avatar, "sums": credit_one.sums,
                                  "ct": credit_one.consumption_time, "id": credit_one.identity}
                        credit_list.append(credit)
            return 1, credit_list
        else:
            g_log.debug("consumer fetch all credit failed, %s:%s", code, message)
            return 1040202, message

    def confirm_apply_credit(self):
        # 解析post参数
        numbers = self.get_argument("numbers")
        credit_identity = self.get_argument("credit")
        merchant_identity = self.get_argument("merchant")
        sums = self.get_argument("sums", "0")
        session_key = self.get_argument("session_key", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 303
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.confirm_consumption_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity
        body.credit_identity = credit_identity
        body.sums = int(sums)

        # 请求逻辑层
        self.send_to_level2(request)

    def confirm_apply_credit_response(self, response):
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            # level2返回1为成功，其它认为失败
            g_log.debug("confirm apply credit success")
            return 1, "yes"
        else:
            g_log.debug("confirm apply credit failed, %s:%s", code, message)
            return 1040401, message

    def refuse_apply_credit(self):
        numbers = self.get_argument("numbers")
        credit_identity = self.get_argument("credit")
        merchant_identity = self.get_argument("merchant")
        reason = self.get_argument("reason")
        session_key = self.get_argument("session_key", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 304
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.refuse_consumption_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity
        body.credit_identity = credit_identity
        body.reason = reason

        # 请求逻辑层
        self.send_to_level2(request)

    def refuse_apply_credit_response(self, response):
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            # level2返回1为成功，其它认为失败
            g_log.debug("refuse apply credit success")
            return 1, "yes"
        else:
            g_log.debug("refuse apply credit failed, %s:%s", code, message)
            return 1040501, message

    def credit_interchange(self):
        # 解析post参数
        numbers = self.get_argument("numbers")
        credit = self.get_argument("credit")
        exec_interchange = self.get_argument("exec_interchange", "0")
        from_merchant = self.get_argument("from")
        to_merchant = self.get_argument("to")
        quantity = self.get_argument("quantity", "0")
        session_key = self.get_argument("session_key", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 309
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.credit_interchange_request
        body.numbers = numbers
        body.exec_interchange = int(exec_interchange)
        body.credit_identity = credit
        body.from_merchant = from_merchant
        body.to_merchant = to_merchant
        body.credit = int(quantity)

        # 请求逻辑层
        self.send_to_level2(request)

    def credit_interchange_response(self, response):
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            # level2返回1为成功，其它认为失败
            g_log.debug("credit interchange success")
            body = response.credit_interchange_response
            return 1, {"quantity": body.credit, "fee": body.fee}
        else:
            g_log.debug("credit interchange failed, %s:%s", code, message)
            return 1040601, message
