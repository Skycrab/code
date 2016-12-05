# -*- coding: utf-8 -*-

import datetime
import time
import hashlib

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib import auth

import util

def health_check(request):
    return HttpResponse("<html>success</html>")


@login_required
def admin_login(request, *args, **kwargs):
    """重定向django admin登陆页面"""
    pass


@login_required
def edit(request):
    """用户信息修改"""
    if is_demo_user(request.user):
        return HttpResponse(util.json_failed(6))
    if request.method == "GET":
        return render_to_response('statistics/edit.html', context_instance=RequestContext(request))
    elif request.method == "POST":
        oldpassword = request.POST.get("oldpassword")
        user = auth.authenticate(username=request.user.username, password=oldpassword)
        if user is not None and user.is_active:
            newpassword = request.POST.get("newpassword")
            user.set_password(newpassword)
            login = Login(user)
            login.change_password()
            user.save()
            return HttpResponse(util.json_success(""))
        return HttpResponse(util.json_failed(1))



@perm_required("204")
@util.cache_error
def pay_richlist_download(request):
    game = request.GET.get("game")
    server = request.GET.get("server")
    start = request.GET.get("start")
    type_snapshot = request.GET.get("type")
    download = RichDownload(game, server, start, request, type_snapshot)
    return download.dump()


def download(model, request):
    if request.method == "GET":
        gameid = request.GET.get("gameid")
        gamename = request.GET.get("gamename")
        obj = model(gameid, request, gamename)
        filename, filedata = obj.download()
        response = HttpResponse(filedata)
        response['Content-Type'] = 'application/octet-stream;charset=utf-8'
        response['Content-Disposition'] = 'attachment;filename="{0}"'.format(filename)
        return response



def upload_view(request, datetype):
    """
    sdk上传
    curl -i --form file=@b.csv  http://bas.com/day
    """
    fp = request.FILES.get('file')
    sign = request.REQUEST.get("sign")
    if sign is None or sign != hashlib.md5(_key).hexdigest():
        return HttpResponse(util.json_failed(6))
    if fp:
        src_fn = save_file(fp)
        file_storage(src_fn, datetype)
        return HttpResponse(util.json_success(src_fn))
    else:
        return HttpResponse(util.json_failed(4))


def brand_upload(request, datatype):
    """品牌文件上传
    curl -i --form file=@2016-06-01.csv http://127.0.0.1:2345/month_upload/brand/
    """
    if request.method == "POST":
        fp = request.FILES.get("file")
        brand.storage(fp, datatype)
    return HttpResponse("success")


def upload_handler(request, action):
    """处理外部上传
    UserRegisterDay
    curl -i --form file=@b.csv  http://as.com/modelupload/UserRegisterDay/?
    """
    sign = request.REQUEST.get("sign")
    if not request.user.is_superuser and (sign is None or sign != hashlib.md5(_key).hexdigest()):
        return HttpResponse(util.json_failed(6))

    actions = ["UserRegisterDay"]
    if request.method == "POST":
        if action not in actions:
            return HttpResponse("action failed")
        fp = request.FILES.get("file")
        brand.storage(fp, action)
        brand.change_db_value(fp, action)
    return HttpResponse("success")



@super_required
def email_data(request, name):
    """自动邮件图片"""
    response = HttpResponse()
    response['Content-Type'] = "image/png"
    response['X-Accel-Redirect'] = "/inter_email/data/%s" % name
    return response



