from django.shortcuts import render, redirect
from django.views import View
from QQLoginTool.QQtool import OAuthQQ
from django.contrib.auth import settings, login
from django import http
import logging
import re
from django_redis import get_redis_connection

from meiduo_mall.utils.response_code import RETCODE
from .models import OAuthQQUser
from .utils import generate_openid_signature, check_openid_signature
from users.models import User

# Create your views here.
logger = logging.getLogger("django")


class OAuthURLView(View):
    # 提供qq登录界面网址
    def get(self, request):
        next = request.GET.get("next")
        # 创建OAuthQQ对象
        # client_id = None, client_secret = None, redirect_uri = None, state = None
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID, client_secret=settings.QQ_CLIENT_SECRET, redirect_uri=settings.QQ_REDIRECT_URI, state=next)

        # 获取qq登录扫码页面，扫码后得到code
        login_url = oauth.get_qq_url()
        # logger.info(login_url)

        return http.JsonResponse({"login_url": login_url, "code": RETCODE.OK, "errmsg": "OK"})


class OAuthUserView(View):
    # 用户扫码登录的回调处理
    def get(self, request):
        # 获取Authorization Code
        code = request.GET.get("code")
        state = request.GET.get("state", "/")

        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID, client_secret=settings.QQ_CLIENT_SECRET, redirect_uri=settings.QQ_REDIRECT_URI)

        try:
            # 通过code获取access_token
            access_token = oauth.get_access_token(code)

            # 通过access_token获取openid
            openid = oauth.get_open_id(access_token)
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({"code": RETCODE.SERVERERR, "errmsg": "QQ服务器错误"})

        # 判断openid是否绑定过用户
        try:
            oauth_user = OAuthQQUser.objects.get(openid=openid)
        except OAuthQQUser.DoesNotExist as e:
            logger.error(e)

            # 加密openid
            openid_sig = generate_openid_signature(openid)

            return render(request, "oauth_callback.html", {"openid": openid_sig})
        else:
            user = oauth_user.user
            login(request, user)

            # 状态保持
            response = redirect(state)
            response.set_cookie("username", user.username, max_age=3600 * 24 * 14)

            return response

    def post(self, request):
        # 接收参数
        mobile = request.POST.get("mobile")
        password = request.POST.get("password")
        sms_code_client = request.POST.get("sms_code")
        openid_sig = request.POST.get("openid")

        if not all([mobile, password, sms_code_client, openid_sig]):
            return http.HttpResponseForbidden("缺少必传参数")

        # 校验参数
        if not re.match(r"^1[3456789]\d{9}$", mobile):
            return http.HttpResponseForbidden("请输入正确的手机号码")

        if not re.match(r"^[a-zA-Z0-9]{8,20}$", password):
            return http.HttpResponseForbidden("请输入8-20位的密码")

        redis_coon = get_redis_connection("verify_code")
        sms_code_server = redis_coon.get("sms_%s" % mobile)
        if sms_code_server is None or sms_code_client.lower() != sms_code_server.decode().lower():
            return http.HttpResponseForbidden("短信验证码错误")

        # 解密openid
        openid = check_openid_signature(openid_sig)
        if openid is None:
            return http.HttpResponseForbidden("openid无效")

        # 绑定用户
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist as e:
            user = User.objects.create_user(
                username=mobile,
                password=password,
                mobile = mobile
            )

        else:
            if not user.check_password(password):
                return http.HttpResponseForbidden("账号或密码错误")

        oauth_user = OAuthQQUser.objects.create(
            openid=openid,
            user=user
        )

        # 状态保持, 重定向
        login(request, user)
        response = redirect(request.GET.get("state", "/"))
        response.set_cookie("username", user.username, max_age=3600 * 24 * 14)
        return response
