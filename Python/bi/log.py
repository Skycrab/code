# coding=utf8

import logging
from logging import handlers

log = logging.getLogger("analysis")


def init(filename):
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    rotate = handlers.RotatingFileHandler(filename, maxBytes=10 * 1024 * 1024, backupCount=0)
    rotate.setLevel(logging.DEBUG)
    fmt = logging.Formatter('%(asctime)s %(filename)s [line:%(lineno)d] %(levelname)s %(message)s')
    console.setFormatter(fmt)
    rotate.setFormatter(fmt)
    log.addHandler(console)
    log.addHandler(rotate)
    log.setLevel(logging.DEBUG)


def test():
    init("cs.log")
    log.error("error")
    log.warning("dfd")


if __name__ == "__main__":
    test()
