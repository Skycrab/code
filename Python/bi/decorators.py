# coding=utf8

from functools import wraps

from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required

import util
from bi.basic import Perm
from bi.login import Login


def change_passwd(view_func):
    """第一次登陆修改密码"""
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        login = Login(request.user)
        if not login.is_demo_user() and not login.is_password_change():
            return HttpResponseRedirect("/edit/?first=true")
        else:
            return view_func(request, *args, **kwargs)
    return wrapper

login_required2 = change_passwd


def perm_required(permcode):
    """权限控制"""
    def wrapper(view_func):
        @login_required2
        @wraps(view_func)
        def decorator(request, *args, **kwargs):
            perm = Perm(request)
            if perm.check and permcode not in perm.menu:
                return HttpResponse(util.json_failed(6))
            request.perm = perm
            return view_func(request, *args, **kwargs)
        return decorator
    return wrapper


def super_required(view_func):
    """超级用户控制"""
    @login_required2
    @wraps(view_func)
    def decorator(request, *args, **kwargs):
        if request.user.is_authenticated() and request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        else:
            return HttpResponseRedirect("/login/?next={0}".format(request.path))
    return decorator
