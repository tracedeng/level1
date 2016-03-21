# -*- coding: utf-8 -*-
__author__ = 'tracedeng'


import socket
import time
from tornado.iostream import IOStream
from tornado.ioloop import IOLoop
from tornado import stack_context
import functools
import collections


class UDPRequest(object):
    def __init__(self, address, port, data):
        self.address = address
        self.port = port
        self.data = data

    def __getattribute__(self, name):
        data = object.__getattribute__(self, name)
        # if name == 'data' and data.rfind('\r\n\r\n') != len(data)-4 or len(data) < 4:
        #     data += '\r\n\r\n'
        return data


class _UDPConnection(object):
    def __init__(self, io_loop, client, request, release_callback, final_callback, max_buffer_size):
        self.start_time = time.time()
        self.io_loop = io_loop
        self.client = client
        self.request = request
        self.release_callback = release_callback
        self.final_callback = final_callback

        address_info = socket.getaddrinfo(request.address, request.port, socket.AF_INET, socket.SOCK_DGRAM, 0, 0)
        af, socket_type, proto, _, socket_address = address_info[0]
        self.stream = IOStream(socket.socket(af, socket_type, proto), io_loop=self.io_loop,
                               max_buffer_size=max_buffer_size)

        self.stream.connect(socket_address, self._on_connect)

    def _on_connect(self):
        self.stream.write(self.request.data)
        # self.stream.read_bytes(65536, self._on_response)
        self.stream.read_until('}}', self._on_response)
        # print("asdfsfeiwjef")

    def _on_response(self, data):
        if self.release_callback is not None:
            release_callback = self.release_callback
            self.release_callback = None
            release_callback()
        self.stream.close()
        if self.final_callback is not None:
            final_callback = self.final_callback
            self.final_callback = None
            final_callback(data)


class AsyncUDPClient(object):
    def __init__(self, io_loop=None):
        self.io_loop = io_loop or IOLoop.instance()
        self.max_clients = 10
        self.queue = collections.deque()
        self.active = {}
        self.max_buffer_size = 81920

    def fetch(self, request, callback, **kwargs):
        callback = stack_context.wrap(callback)
        self.queue.append((request, callback))
        self._process_queue()

    def _process_queue(self):
        with stack_context.NullContext():
            while self.queue and len(self.active) < self.max_clients:
                request, callback = self.queue.popleft()
                key = object()
                self.active[key] = (request, callback)
                _UDPConnection(self.io_loop, self, request, functools.partial(self._release_fetch, key),
                               callback, self.max_buffer_size)

    def _release_fetch(self, key):
        del self.active[key]
        self._process_queue()