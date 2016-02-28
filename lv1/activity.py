# -*- coding: utf-8 -*-
__author__ = 'tracedeng'

from tornado.web import MissingArgumentError, asynchronous
import json
import common_pb2
import log
g_log = log.WrapperLog('stream', name=__name__, level=log.DEBUG).log  # 启动日志功能
from level1_base import Base, InvalidArgumentError


class Activity(Base):
    @asynchronous
    def post(self, *args, **kwargs):
        """
        根据post["type"]分发处理
        :param args:
        :param kwargs:
        :return:
        """
        try:
            features_handle = {"create": self.create_activity, "retrieve": self.retrieve_activity,
                               "update": self.update_activity, "delete": self.delete_activity,
                               "consumer_retrieve": self.consumer_retrieve_activity,
                               "buy": self.buy_activity,
                               "upload_token": self.upload_token}
            self.mode = self.get_argument("type")
            g_log.debug("[activity.%s.request]", self.mode)
            features_handle.get(self.mode, self.dummy_command)()
        except MissingArgumentError as e:
            # 缺少请求参数
            g_log.error("miss argument %s, %s", e.arg_name, e)
            self.write(json.dumps({"c": 1070001, "m": "miss argument"}))
            g_log.debug("[activity.%s.response]", self.mode)
            self.finish()
        except InvalidArgumentError as e:
            # 缺少请求参数
            g_log.error("invalid argument %s, %s", e.arg_name, e)
            self.write(json.dumps({"c": 1070008, "m": "invalid argument"}))
            g_log.debug("[activity.%s.response]", self.mode)
            self.finish()
        except Exception as e:
            # from print_exception import print_exception
            # print_exception()
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 1070002, "m": "exception"}))
            g_log.debug("[activity.%s.response]", self.mode)
            self.finish()

    def on_response(self, response):
        try:
            super(Activity, self).on_response(response)
            if not self.response:
                g_log.error("illegal response")
                self.write(json.dumps({"c": 1070003, "m": "exception"}))
            else:
                features_response = {"create": self.create_activity_response,
                                     "retrieve": self.retrieve_activity_response,
                                     "update": self.update_activity_response,
                                     "delete": self.delete_activity_response,
                                     "consumer_retrieve": self.consumer_retrieve_activity_response,
                                     "buy": self.buy_activity_response,
                                     "upload_token": self.upload_token_response}
                self.code, self.message = features_response.get(self.mode, self.dummy_command)(self.response)
                if self.code == 1:
                    self.write(json.dumps({"c": self.code, "r": self.message}))
                else:
                    self.write(json.dumps({"c": self.code, "m": self.message}))
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 1070004, "m": "exception"}))
        g_log.debug("[activity.%s.response]", self.mode)
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
            return 1070005, "no handler"
        else:
            # 无效的命令
            g_log.debug("unsupported type %s", self.mode)
            self.write(json.dumps({"c": 1070006, "m": "unsupported type"}))
            self.finish()

    def create_activity(self):
        """
        创建活动
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        session_key = self.get_argument("session_key", "")
        title = self.get_argument("title", "")
        introduce = self.get_argument("introduce", "")
        credit = self.get_argument("credit", 0)
        poster = self.get_argument("poster", "")
        merchant_identity = self.get_argument("merchant", "")
        expire_time = self.get_argument("expire", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 701
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.activity_create_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity
        material = body.material
        material.title = title
        material.credit = int(credit)
        material.poster = poster
        material.introduce = introduce
        material.expire_time = expire_time

        # 请求逻辑层
        self.send_to_level2(request)

    def create_activity_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("create activity success")
            body = response.activity_create_response
            return 1, body.identity
        else:
            g_log.debug("create activity failed, %s:%s", code, message)
            return 1070101, message

    def retrieve_activity(self):
        """
        读取活动列表
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        session_key = self.get_argument("session_key", "")
        merchant_identity = self.get_argument("merchant", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 702
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.activity_retrieve_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity

        # 请求逻辑层
        self.send_to_level2(request)

    def retrieve_activity_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("retrieve activity success")
            body = response.activity_retrieve_response

            r = {"mn": body.merchant.name}
            activities = []
            for activity_one in body.materials:
                activity = {"t": activity_one.title, "in": activity_one.introduce, "cr": activity_one.credit,
                            "po": activity_one.poster, "et": activity_one.expire_time, "id": activity_one.identity}
                activities.append(activity)
            r["act"] = activities
            return 1, r
        else:
            g_log.debug("retrieve activity failed, %s:%s", code, message)
            return 1070201, message

    def update_activity(self):
        """
        更新活动
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        session_key = self.get_argument("session_key", "")
        merchant_identity = self.get_argument("merchant", "")
        activity_identity = self.get_argument("activity", "")

        default = ["not", "update"]
        title = self.get_argument("title", default)
        credit = self.get_argument("credit", default)
        poster = self.get_argument("poster", default)
        introduce = self.get_argument("introduce", default)
        expire_time = self.get_argument("expire", default)

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 704
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.activity_update_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity
        body.activity_identity = activity_identity
        material = body.material

        if title != default:
            material.title = title
        if credit != default:
            material.credit = int(credit)
        if poster != default:
            material.poster = poster
        if introduce != default:
            material.introduce = introduce
        if expire_time != default:
            material.expire_time = expire_time

        # 请求逻辑层
        self.send_to_level2(request)

    def update_activity_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("update activity success")
            return 1, "yes"
        else:
            g_log.debug("update activity failed, %s:%s", code, message)
            return 1070301, message

    def delete_activity(self):
        """
        删除活动
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        session_key = self.get_argument("session_key", "")
        merchant_identity = self.get_argument("merchant", "")
        activity_identity = self.get_argument("activity", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 705
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.activity_delete_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity
        body.activity_identity = activity_identity

        # 请求逻辑层
        self.send_to_level2(request)

    def delete_activity_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("delete activity success")
            return 1, "yes"
        else:
            g_log.debug("delete activity failed, %s:%s", code, message)
            return 1070401, message

    def consumer_retrieve_activity(self):
        """
        用户读取活动列表
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        session_key = self.get_argument("session_key", "")
        # TODO 经纬度

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 706
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.consumer_retrieve_activity_request
        body.numbers = numbers

        # 请求逻辑层
        self.send_to_level2(request)

    def consumer_retrieve_activity_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("consumer retrieve activity success")
            body = response.consumer_retrieve_activity_response
            r = []
            for activity_one in body.materials:
                merchant = activity_one.merchant
                activity = {"t": activity_one.title, "in": activity_one.introduce, "cr": activity_one.credit,
                            "po": activity_one.poster, "et": activity_one.expire_time, "id": activity_one.identity,
                            "mna": merchant.name, "mlo": merchant.location, "mco": merchant.contact_numbers,
                            "vol": activity_one.volume}
                r.append(activity)
            return 1, r
        else:
            g_log.debug("retrieve activity failed, %s:%s", code, message)
            return 1070601, message

    def buy_activity(self):
        """
        购买活动
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        session_key = self.get_argument("session_key", "")
        merchant_identity = self.get_argument("merchant", "")
        activity_identity = self.get_argument("discount", "")
        spend_credit = self.get_argument("spend", "[]")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 708
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.buy_activity_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity
        body.activity_identity = activity_identity

        spend_credit = json.loads(spend_credit)
        # g_log.debug("spend_credit:%s", spend_credit)
        for credit in spend_credit:
            # g_log.debug(credit)
            credit_one = body.credits.add()
            credit_one.identity = credit["identity"]
            credit_one.quantity = int(credit["quantity"])

        # 请求逻辑层
        self.send_to_level2(request)

    def buy_activity_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("buy activity success")
            body = response.buy_activity_response
            return 1, body.voucher
        else:
            g_log.debug("buy activity failed, %s:%s", code, message)
            return 1070701, message

    def upload_token(self):
        """
        登录
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        kind = self.get_argument("resource", "dummy")
        merchant_identity = self.get_argument("merchant", "")
        debug = self.get_argument("debug", "debug")
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
            return 1070601, message