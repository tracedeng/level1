# -*- coding: utf-8 -*-
__author__ = 'tracedeng'

from tornado.web import MissingArgumentError, asynchronous
import json
import redis
import common_pb2
import log
g_log = log.WrapperLog('stream', name=__name__, level=log.DEBUG).log  # 启动日志功能
from level1_base import Base, InvalidArgumentError


class Merchant(Base):
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
            features_handle = {"create": self.create_merchant, "retrieve": self.retrieve_merchant,
                               "update": self.update_merchant, "verify": self.update_merchant_verified,
                               "delete": self.delete_merchant, "create_manager": self.create_merchant_manager,
                               "delete_manager": self.merchant_delete_manager,
                               "delegate": self.merchant_delegate_manager,
                               "upload_token": self.upload_token,
                               "verified_merchant": self.retrieve_verified_merchant,
                               "exchange_in_merchant": self.retrieve_exchange_in_merchant}
            self.mode = self.get_argument("type")
            g_log.debug("[merchant.%s.request]", self.mode)
            features_handle.get(self.mode, self.dummy_command)()
        except MissingArgumentError as e:
            # 缺少请求参数
            g_log.error("miss argument %s, %s", e.arg_name, e)
            self.write(json.dumps({"c": 1030001, "m": "miss argument"}))
            g_log.debug("[merchant.%s.response]", self.mode)
            self.finish()
        except InvalidArgumentError as e:
            # 缺少请求参数
            g_log.error("invalid argument %s, %s", e.arg_name, e)
            self.write(json.dumps({"c": 1030008, "m": "invalid argument"}))
            g_log.debug("[merchant.%s.response]", self.mode)
            self.finish()
        except (redis.ConnectionError, redis.TimeoutError) as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 1030007, "m": "exception"}))
            g_log.debug("[merchant.%s.response]", self.mode)
            self.finish()
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 1030002, "m": "exception"}))
            g_log.debug("[merchant.%s.response]", self.mode)
            self.finish()

    def on_response(self, response):
        try:
            super(Merchant, self).on_response(response)
            if not self.response:
                g_log.error("illegal response")
                self.write(json.dumps({"c": 1030003, "m": "exception"}))
            else:
                features_response = {"create": self.create_merchant_response,
                                     "retrieve": self.retrieve_merchant_response,
                                     "update": self.update_merchant_response,
                                     "verify": self.update_merchant_verified_response,
                                     "delete": self.delete_merchant_response,
                                     "create_manager": self.create_merchant_manager_response,
                                     "delete_manager": self.merchant_delete_manager_response,
                                     "delegate": self.merchant_delegate_manager_response,
                                     "upload_token": self.upload_token_response,
                                     "verified_merchant": self.retrieve_verified_merchant_response,
                                     "exchange_in_merchant": self.retrieve_exchange_in_merchant_response}
                self.code, self.message = features_response.get(self.mode, self.dummy_command)(self.response)
                if self.code == 1:
                    self.write(json.dumps({"c": self.code, "r": self.message}))
                else:
                    self.write(json.dumps({"c": self.code, "m": self.message}))
        except Exception as e:
            g_log.error("<%s> %s", e.__class__, e)
            self.write(json.dumps({"c": 1030004, "m": "exception"}))
        g_log.debug("[merchant.%s.response]", self.mode)
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
            return 1030005, "no handler"
        else:
            # 无效的命令
            g_log.debug("unsupported type %s", self.mode)
            self.write(json.dumps({"c": 1030006, "m": "unsupported type"}))
            self.finish()

    def create_merchant(self):
        """
        创建商家资料
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        session_key = self.get_argument("session_key", "")
        name = self.get_argument("name", "")
        name_en = self.get_argument("name_en", "")

        qrcode = self.get_argument("qrcode", "")
        contact_numbers = self.get_argument("contact_numbers", "")
        logo = self.get_argument("logo", "")
        email = self.get_argument("email", "")
        introduce = self.get_argument("introduce", "")
        longitude = self.get_argument("longitude", "")
        latitude = self.get_argument("latitude", "")
        country = self.get_argument("country", "")
        location = self.get_argument("location", "")
        contract = self.get_argument("contract", "")
        ratio = self.get_argument("ratio", 1)

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 201
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.merchant_create_request
        body.numbers = numbers
        material = body.material
        material.name = name
        material.name_en = name_en

        material.qrcode = qrcode
        material.contact_numbers = contact_numbers
        material.logo = logo
        material.email = email
        material.introduce = introduce
        material.longitude = longitude      # level1_base 中已经处理
        material.latitude = latitude
        material.country = country
        material.location = location
        material.contract = contract
        body.ratio = int(ratio)

        # 请求逻辑层
        self.send_to_level2(request)

    def create_merchant_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("create merchant success")
            body = response.merchant_create_response
            return 1, body.merchant_identity
        else:
            g_log.debug("create merchant failed, %s:%s", code, message)
            return 1030101, message

    def retrieve_merchant(self):
        """
        读取商家资料
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        session_key = self.get_argument("session_key", "")
        merchant_identity = self.get_argument("merchant", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 202
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.merchant_retrieve_request
        body.numbers = numbers
        if merchant_identity:
            body.merchant_identity = merchant_identity

        # 请求逻辑层
        self.send_to_level2(request)

    def retrieve_merchant_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("retrieve merchant success")
            body = response.merchant_retrieve_response
            # materials = body.materials
            r = []
            for material in body.materials:
                merchant = {"n": material.name, "ne": material.name_en, "con": material.contact_numbers,
                            "em": material.email, "logo": material.logo, "in": material.introduce,
                            "co": material.country, "v": material.verified, "lo": material.location,
                            "qr": material.qrcode, "fou": material.numbers, "ctr": material.contract,
                            "lon": material.longitude, "lat": material.latitude, "id": material.identity}
                r.append(merchant)
            return 1, r
        else:
            g_log.debug("retrieve merchant failed, %s:%s", code, message)
            return 1030201, message

    def update_merchant(self):
        """
        更新商家资料
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        session_key = self.get_argument("session_key", "")
        merchant_identity = self.get_argument("merchant", "")

        default = ["not", "update"]
        name = self.get_argument("name", default)
        name_en = self.get_argument("name_en", default)
        logo = self.get_argument("logo", default)
        contract = self.get_argument("contract", default)
        contact_numbers = self.get_argument("contact_numbers", default)
        email = self.get_argument("email", default)
        introduce = self.get_argument("introduce", default)
        country = self.get_argument("country", default)
        location = self.get_argument("location", default)
        qrcode = self.get_argument("qrcode", default)
        longitude = self.get_argument("longitude", -1.0)
        latitude = self.get_argument("latitude", -1.0)

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 204
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.merchant_update_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity
        material = body.material

        if name != default:
            material.name = name
        if name_en != default:
            material.name_en = name_en
        if logo != default:
            material.logo = logo
        if contract != default:
            material.contract = int(contract)
        if email != default:
            material.email = email
        if contact_numbers != default:
            material.contact_numbers = contact_numbers
        if introduce != default:
            material.introduce = introduce
        if country != default:
            material.country = country
        if location != default:
            material.location = location
        if qrcode != default:
            material.qrcode = qrcode
        if longitude != -1.0:
            material.longitude = longitude
        if latitude != -1.0:
            material.latitude = latitude

        # 请求逻辑层
        self.send_to_level2(request)

    def update_merchant_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("update merchant verified success")
            return 1, "yes"
        else:
            g_log.debug("update merchant verified failed, %s:%s", code, message)
            return 1030501, message

    def update_merchant_verified(self):
        """
        更新商家资料
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        session_key = self.get_argument("session_key", "")
        merchant_identity = self.get_argument("merchant", "")
        verified = self.get_argument("verified", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 205
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.merchant_update_verified_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity
        body.verified = verified

        # 请求逻辑层
        self.send_to_level2(request)

    def update_merchant_verified_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("update merchant verified success")
            return 1, "yes"
        else:
            g_log.debug("update merchant verified failed, %s:%s", code, message)
            return 1030501, message

    def delete_merchant(self):
        """
        删除商家资料
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        session_key = self.get_argument("session_key", "")
        merchant_identity = self.get_argument("merchant", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 206
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.merchant_delete_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity

        # 请求逻辑层
        self.send_to_level2(request)

    def delete_merchant_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("delete merchant success")
            return 1, "yes"
        else:
            g_log.debug("delete merchant failed, %s:%s", code, message)
            return 1030601, message

    def create_merchant_manager(self):
        """
        新增商家管理员
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        session_key = self.get_argument("session_key", "")
        merchant_identity = self.get_argument("merchant", "")
        manager = self.get_argument("manager")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 207
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.merchant_create_manager_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity
        body.manager_numbers = manager

        # 请求逻辑层
        self.send_to_level2(request)

    def create_merchant_manager_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("add merchant manager success")
            return 1, "yes"
        else:
            g_log.debug("add merchant manager failed, %s:%s", code, message)
            return 1030701, message

    def merchant_delegate_manager(self):
        """
        商家委托给其它管理员
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        session_key = self.get_argument("session_key", "")
        merchant_identity = self.get_argument("merchant", "")
        delegate_manager = self.get_argument("manager")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 208
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.merchant_delegate_manager_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity
        body.delegate_numbers = delegate_manager

        # 请求逻辑层
        self.send_to_level2(request)

    def merchant_delegate_manager_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("merchant delegate success")
            return 1, "yes"
        else:
            g_log.debug("merchant delegate to manager failed, %s:%s", code, message)
            return 1030801, message

    def merchant_delete_manager(self):
        """
        商家委托给其它管理员
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        session_key = self.get_argument("session_key", "")
        merchant_identity = self.get_argument("merchant", "")
        manager = self.get_argument("manager")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 209
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.merchant_delete_manager_request
        body.numbers = numbers
        body.merchant_identity = merchant_identity
        # managers = body.managers.add()
        # managers = manager
        body.manager_numbers.append(manager)

        # 请求逻辑层
        self.send_to_level2(request)

    def merchant_delete_manager_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("merchant delegate success")
            body = response.merchant_delete_manager_response
            s = []
            f = []
            for manager in body.success_managers:
                s.append(manager)
            for manager in body.failed_managers:
                f.append(manager)
            r = {"success": s, "failed": f}
            g_log.debug("success:%s, failed:%s", s, f)
            return 1, r
        else:
            g_log.debug("merchant delegate to manager failed, %s:%s", code, message)
            return 1030901, message

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

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 601
        request.head.seq = 2
        request.head.numbers = numbers

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
            r = {"tok": body.upload_token, "path": body.key}
            # upload_token = body.upload_token
            return 1, r
        else:
            g_log.debug("get upload token failed, %s:%s", code, message)
            return 1032001, message

    def retrieve_verified_merchant(self):
        """
        读取商家资料
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        session_key = self.get_argument("session_key", "")
        verified = self.get_argument("verified", "both")
        self.merchant_exclude = self.get_argument("merchant_exclude", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 210
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.retrieve_merchant_request
        body.numbers = numbers
        body.verified = verified

        # 请求逻辑层
        self.send_to_level2(request)

    def retrieve_verified_merchant_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("retrieve verified merchant success")
            body = response.retrieve_merchant_response
            # materials = body.materials
            r = []
            for material in body.materials:
                if self.merchant_exclude != material.identity:
                    merchant = {"n": material.name, "ne": material.name_en, "con": material.contact_numbers,
                                "em": material.email, "logo": material.logo, "in": material.introduce,
                                "co": material.country, "v": material.verified, "lo": material.location,
                                "qr": material.qrcode, "fou": material.numbers, "ctr": material.contract,
                                "lon": material.longitude, "lat": material.latitude, "id": material.identity}
                    r.append(merchant)
            return 1, r
        else:
            g_log.debug("retrieve merchant failed, %s:%s", code, message)
            return 1031001, message

    def retrieve_exchange_in_merchant(self):
        """
        读取允许积分导入的商家列表
        :return:
        """
        # 解析post参数
        numbers = self.get_argument("numbers")
        session_key = self.get_argument("session_key", "")
        self.merchant_exclude = self.get_argument("merchant_exclude", "")

        # 组请求包
        request = common_pb2.Request()
        request.head.cmd = 211
        request.head.seq = 2
        request.head.numbers = numbers
        request.head.session_key = session_key

        body = request.retrieve_exchange_in_merchant_request
        body.numbers = numbers

        # 请求逻辑层
        self.send_to_level2(request)

    def retrieve_exchange_in_merchant_response(self, response):
        """
        逻辑层返回请求后处理
        :param response: pb格式回包
        """
        head = response.head
        code = head.code
        message = head.message
        if 1 == code:
            g_log.debug("retrieve exchange in merchant success")
            body = response.retrieve_exchange_in_merchant_response
            # materials = body.materials
            r = []
            for material in body.materials:
                if self.merchant_exclude != material.identity:
                    merchant = {"n": material.name, "ne": material.name_en, "con": material.contact_numbers,
                                "em": material.email, "logo": material.logo, "in": material.introduce,
                                "co": material.country, "v": material.verified, "lo": material.location,
                                "qr": material.qrcode, "fou": material.numbers, "ctr": material.contract,
                                "lon": material.longitude, "lat": material.latitude, "id": material.identity}
                    r.append(merchant)
            return 1, r
        else:
            g_log.debug("retrieve exchange in merchant failed, %s:%s", code, message)
            return 1031101, message