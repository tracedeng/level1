# -*- coding: utf-8 -*-
__author__ = 'tracedeng'

import sys
wrapper_path = ["./lv1/", "./coframe", "../level2/wrapper", "../level2/proto", "../level2/proto/lv2", "../level2/lv2", "../level2/proto/branch"]
for path in wrapper_path:
    if path not in sys.path:
        print("add path %s", path)
        sys.path.append(path)

from coframe.async_server import Server
if __name__ == "__main__":
    server = Server()
    server.run()
