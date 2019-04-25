from django.shortcuts import render, redirect
from django.views.generic import View
from django import http
import re
from .models import User
from django.db import DatabaseError
import logging
from django.contrib.auth import login, authenticate
from meiduo_mall.utils.response_code import RETCODE
from django_redis import get_redis_connection

# Create your views here.
logger = logging.getLogger("django")


class RegisterView(View):
    def get(self, request):

        return render(request, "register.html")

    def post(self, request):
        # 接受请求
        username = request.POST.get("username")
        password = request.POST.get("password")
        password2 = request.POST.get("password2")
        mobile = request.POST.get("mobile")
        allow = request.POST.get("allow")
        sms_code_client = request.POST.get("sms_code")

        # 校验参数
        if not all([username, password, password2, mobile, allow, sms_code_client]):
            return http.HttpResponseForbidden("缺少必传参数")

        if not re.match(r"^[a-zA-Z0-9_-]{5,10}$", username):
            return http.HttpResponseForbidden("请输入5-10个字符串的用户名")

        if not re.match(r"^[a-zA-Z0-9]{8,20}$", password):
            return http.HttpResponseForbidden("请输入8-20位的密码")

        if password2 != password:
            return http.HttpResponseForbidden("两次密码输入不一致")

        redis_coon = get_redis_connection("verify_code")
        sms_code_server = redis_coon.get("sms_%s" % mobile)
        if sms_code_client.lower() != sms_code_server.decode().lower():
            return http.HttpResponse("短信验证码错误")

        # 保存注册数据
        try:
            user = User.objects.create_user(username=username, password=password, mobile=mobile)
        except DatabaseError as e:
            logger.error(e)
            return render(request, "register.html", {"register_errmsg": "用户注册失败"})

        # 状态保持
        login(request, user)
        
        # 响应注册结果,重定向
        return redirect("/")


class UsernameCountView(View):
    def get(self, request, username):
        count = User.objects.filter(username=username).count()
        return http.JsonResponse({"count": count, "code": RETCODE.OK, "errmsg": "OK"})


class MobileCountView(View):
    def get(self, request, mobile):
        count = User.objects.filter(mobile=mobile).count()
        return http.JsonResponse({"count": count, "code": RETCODE.OK, "errmsg": "OK"})


class LoginView(View):
    # 登录界面
    def get(self, request):
        return render(request, "login.html")

    def post(self, request):
        # 获取参数
        username = request.POST.get("username")
        password = request.POST.get("password")
        remembered = request.POST.get("remembered")

        # 校验参数
        if not all([username, password]):
            return http.HttpResponse("缺少必传参数")

        if not re.match(r"^[a-zA-Z0-9_-]{5,20}$", username):
            return http.HttpResponse("请输入正确的用户名或密码")

        if not re.match(r"^[0-9A-Za-z]{8,20}$", password):
            return http.HttpResponse("密码最少8位，最长20位")

        # 登录认证
        user = authenticate(username=username, password=password)

        if user is None:
            return render(request, "login.html", {"account_errmsg": "用户名或密码错误"})

        # 状态保持
        login(request, user)

        if remembered != "on":
            request.session.set_expiry(0)

        # 响应重定向
        return redirect("/")