# -*- coding: utf-8 -*-
__author__ = 'tracedeng'

import ConfigParser
import socket
import common_pb2
import log
g_log = log.WrapperLog('stream', name=__name__, level=log.DEBUG).log  # 启动日志功能
from singleton import singleton
from branch_socket import send_to_sock, receive_from_sock, send_to_address
import package


@singleton
class Level2Access():
    LEVEL2_ADDRESS = "127.0.0.1:9527"
    LEVEL2_TIMEOUT = 1000           # 逻辑层超时时间

    def __init__(self):
        """
        :param conf_path: 配置文件路径
        :return:
        """
        conf_path = "server.conf"
        config = ConfigParser.ConfigParser()
        config.read(conf_path)
        self.config = config

        # 解析逻辑层lv2地址
        try:
            lv2_address = config.get("level2", "address")
            lv2_expire = config.get("level2", "timeout")
        except ConfigParser.NoSectionError as e:
            g_log.warning("config file miss section level2")
        except ConfigParser.NoOptionError as e:
            g_log.warning("config file miss %s:%s", e.section, e.option)
        except Exception as e:
            g_log.warning("<%s> %s", e.__class__, e)
        if not lv2_address:
            lv2_address = self.__class__.LEVEL2_ADDRESS
        if not lv2_expire:
            lv2_expire = self.__class__.LEVEL2_TIMEOUT
        self.lv2_address = lv2_address
        self.lv2_expire = lv2_expire
        g_log.debug("level2 address %s, expire time %s", lv2_address, lv2_expire)

        # 创建逻辑层lv2使用的socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setblocking(0)
        address = lv2_address.split(":")
        lv2_address = (address[0], int(address[1]))
        self.lv2_address = lv2_address
        sock.connect((address[0], int(address[1])))
        self.lv2_sock = sock
        g_log.debug("create level2 socket done ...")

    def send_to_level2(self, message):
        # self.lv2_sock.connect(self.lv2_address)
        send_to_sock(self.lv2_sock, message)
        # send_to_address(message, self.lv2_address)

    def receive_from_level2(self):
        return receive_from_sock(self.lv2_sock)


# def get_level2_sock():
#     """
#     获取请求level2的socket
#     :return: sock/成功，None/失败
#     """
#     try:
#         level2 = Level2Access()
#         return level2.lv2_sock
#     except Exception as e:
#         g_log.error("<%s> %s", e.__class__, e)
#         return None
#
#
# def send_to_level2(request):
#     """
#     发送请求到level2
#     :param request: 请求pb
#     :return:
#     """
#     try:
#         message = package.serial_pb(request)
#         level2 = Level2Access()
#         yield level2.send_to_level2(message)
#
#
# # def receive_from_level2(fd, events):
# def receive_from_level2():
#     try:
#         level2 = Level2Access()
#         response = level2.receive_from_level2()
#         g_log.debug(response)
#         res = common_pb2.Response()
#         res.ParseFromString(response[6:-2])
#         # uuid = res.head.coroutine_uuid
#         return res
#     except Exception as e:
#         g_log.debug(e)