# coding=utf8

import errno
import socket
import select
import greenlet as rawgreenlet
from greenlet import greenlet


class Sock(object):
    def __init__(self, socket_=None):
        if socket_ is None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        else:
            sock = socket_
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # 设置非阻塞
        sock.setblocking(0)
        self.sock = sock

    def listen(self, backlog):
        self.sock.listen(backlog)

    def bind(self, host, port):
        self.sock.bind((host, port))

    def accept(self):
        while True:
            try:
                print("accept")
                client_sock, address = self.sock.accept()
                break
            except socket.error as e:
                print(e)
                if e.args[0] != errno.EAGAIN:
                    raise
            # switch是回调函数，当loop回调时会再次回到这里
            switch = rawgreenlet.getcurrent().switch
            # 注册读事件，当sock可读时调用回调函数
            ioloop.wait(self.sock, switch, ioloop.READ)

        return Sock(client_sock), address

    def recv(self, *args):
        while True:
            try:
                print("recv")
                return self.sock.recv(*args)
            except socket.error as e:
                print(e)
                if e.args[0] != errno.EAGAIN:
                    raise
            switch = rawgreenlet.getcurrent().switch
            ioloop.wait(self.sock, switch, ioloop.READ)


def spawn(f):
    g = greenlet(f, parent=ioloop)
    ioloop.add_callback(g.switch)
    return g


class IOLoop(greenlet):
    """"main greenlet"""
    READ = select.EPOLLIN
    WRITE = select.EPOLLOUT
    ERROR = select.EPOLLERR | select.EPOLLHUP

    def __init__(self):
        self.poller = select.epoll()
        self.handler = {}
        self.callbacks = []

    def wait(self, sock, callback, event):
        """wait until waiter avaliable"""
        self.add_handler(sock, callback, event)
        self.switch()

    def add_handler(self, sock, callback, event):
        """
        fd: file description
        callback: when event avaliable, invoke callback
        evnet: poll evnet
        """
        fd = sock.fileno()
        if fd in self.handler:
            self.poller.unregister(fd)
        self.poller.register(fd, event)
        self.handler[fd] = callback

    def add_callback(self, callback):
        self.callbacks.append(callback)

    def start(self):
        self.switch()

    def run(self):
        print("ioloop run")
        while True:
            # invoke callback
            while self.callbacks:
                callback = self.callbacks.pop()
                callback()

            # poller
            events = self.poller.poll(1)
            print("poller:", events)
            for fd, event in events:
                if event & self.READ:
                    handler = self.handler[fd]
                    handler()

ioloop = IOLoop()


def f():
    sock = Sock()
    sock.bind("localhost", 8088)
    sock.listen(5)
    client_sock, address = sock.accept()
    print("connection from:", address)
    while 1:
        print(client_sock.recv(10))

    # return this greenlet will dead

spawn(f)
ioloop.start()
