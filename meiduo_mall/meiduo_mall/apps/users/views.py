from django.shortcuts import render, redirect, reverse
from django.views.generic import View
from django import http
from django_redis import get_redis_connection
import re
from django.db import DatabaseError
import logging
from django.contrib.auth import login, authenticate, logout, mixins
import json

from .models import User, Address
from meiduo_mall.utils.response_code import RETCODE
from celery_tasks.email.tasks import send_verify_email
from .utils import generate_verify_email_url, check_token_to_user
from goods.models import SKU
from carts.utils import merge_cart_cookie_to_redis

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
        if sms_code_server is None or sms_code_client.lower() != sms_code_server.decode().lower():
            return http.HttpResponse("短信验证码错误")

        # 保存注册数据
        try:
            user = User.objects.create_user(username=username, password=password, mobile=mobile)
        except DatabaseError as e:
            logger.error(e)
            return render(request, "register.html", {"register_errmsg": "用户注册失败"})

        # 状态保持
        login(request, user)

        # 首页用户名展示,通过设置cookie传递vue中的username变量
        response = redirect("/")
        response.set_cookie("username", user.username, max_age=3600 * 24 * 14)
        
        # 响应注册结果,重定向
        return response


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

        # 首页用户名展示
        response = redirect(request.GET.get("next", "/"))
        response.set_cookie("username", user.username, max_age=3600 * 24 * 14)

        # 合并购物车
        merge_cart_cookie_to_redis(request, user, response)

        # 响应重定向
        return response


class LogoutView(View):
    def get(self, request):
        # 清理session
        logout(request)

        # 重定向到登录页
        response = redirect(reverse("users:login"))

        # 清楚cookie
        response.delete_cookie("username")

        return response


class UserInfoView(mixins.LoginRequiredMixin, View):
    def get(self, request):
        # 判断用户是否登录方法一
        # user = request.user
        # if user.is_authenticated:
        #     return render(request, "user_center_info.html")
        # else:
        #     return redirect("/login/?next=/info/")

        # 显示用户基本信息（方法一）
        # 方法二：在前端页面把{{ username }}直接改为{{ requset.user.username }}
        # context = {
        #     'username': request.user.username,
        #     'mobile': request.user.mobile,
        #     'email': request.user.email,
        #     'email_active': request.user.email_active
        # }
        return render(request, "user_center_info.html")


class EmailView(mixins.LoginRequiredMixin, View):
    # 添加用户邮箱
    def put(self, request):
        json_dict = json.loads(request.body)
        email = json_dict.get("email")

        # 参数校验
        if email is None or re.match(r"^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$", email) is None:
            return http.HttpResponseForbidden("邮箱格式错误")

        # 赋值email字段
        try:
            user = request.user
            user.email = email
            user.save()
        except Exception as e:
            return http.JsonResponse({"code": RETCODE.EMAILERR, "errmsg": "邮箱添加失败"})
        else:
            verify_url = generate_verify_email_url(user)

            # from django.conf import settings
            # from django.core.mail import send_mail
            # to_email = email
            # subject = "美多商城邮箱验证"
            # html_message = '<p>尊敬的用户您好！</p>' \
            #                '<p>感谢您使用美多商城。</p>' \
            #                '<p>您的邮箱为：%s 。请点击此链接激活您的邮箱：</p>' \
            #                '<p><a href="%s">%s<a></p>' % (to_email, verify_url, verify_url)
            # send_mail(subject, "", settings.EMAIL_HOST_USER, [to_email], html_message=html_message)


            send_verify_email.delay(email, verify_url)
            return http.JsonResponse({"code": RETCODE.OK, "errmsg": "OK"})


class VerifyEmailView(View):
    # 激活邮箱
    def get(self, request):
        token = request.GET.get("token")
        user = check_token_to_user(token)
        if user is None:
            return http.HttpResponseForbidden("token无效")

        # 修改当前email_active字段
        user.email_active = True
        user.save()

        # 响应
        return redirect("/info/")


class AddressView(mixins.LoginRequiredMixin, View):
    def get(self, request):
        user = request.user

        try:
            addresses_qs = Address.objects.filter(user=user, is_deleted=False)
        except Address.DoesNotExist:
            return http.HttpResponseForbidden("用户无收货地址")
        else:
            address_list = []
            for address in addresses_qs:
                address_dict = {
                    "id": address.id,
                    "title": address.title,
                    "receiver": address.receiver,
                    "province": address.province.name,
                    "city": address.city.name,
                    "district": address.district.name,
                    "place": address.place,
                    "mobile": address.mobile,
                    "tel": address.tel,
                    "email": address.email,
                    "province_id": address.province_id,
                    "city_id": address.city_id,
                    "district_id": address.district_id,
                }
                address_list.append(address_dict)

            context = {
                "addresses": address_list,
                "default_address_id": user.default_address_id # 不能写user.default_address.id,因为如果没有设置default，None.id会报错
            }
        return render(request, "user_center_site.html", context)


class CreateAddress(mixins.LoginRequiredMixin, View):
    # 新增收货地址

    def post(self, request):
        user = request.user

        # 判断用户收货地址是否超过20个
        count = Address.objects.filter(user=user, is_deleted=False).count()
        if count >= 20:
            return http.HttpResponseForbidden("用户收货地址已达上线")

        # 接收参数
        json_dict = json.loads(request.body)
        """
        form_address: {
            title: '',
            receiver: '',
            province_id: '',
            city_id: '',
            district_id: '',
            place: '',
            mobile: '',
            tel: '',
            email: '',
        },
        """
        title = json_dict.get("title")
        receiver = json_dict.get("receiver")
        province_id = json_dict.get("province_id")
        city_id = json_dict.get("city_id")
        district_id = json_dict.get("district_id")
        place = json_dict.get("place")
        mobile = json_dict.get("mobile")
        tel = json_dict.get("tel")
        email = json_dict.get("email")

        # 校验参数
        if not all([title, receiver, province_id, city_id, district_id, place, mobile]):
            return http.HttpResponseForbidden("缺少必传参数")

        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('参数mobile有误')

        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')

        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')

        # 保存地址信息
        try:
            address = Address.objects.create(
                user=user,
                title=title,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )

            # 判断默认地址是否存在
            default_address = user.default_address
            if default_address is None:
                user.default_address = address
                user.save()

        except Exception:
            return http.HttpResponseForbidden("地址保存失败")
        else:
            address_dict = {
                "id": address.id,
                "title": address.title,
                "receiver": address.receiver,
                "province": address.province.name,
                "city": address.city.name,
                "district": address.district.name,
                "place": address.place,
                "mobile": address.mobile,
                "tel": address.tel,
                "email": address.email
            }
            return http.JsonResponse({"code": RETCODE.OK, "errmsg": "OK", "address": address_dict})


class UpdateDestroyAddressView(mixins.LoginRequiredMixin, View):
    def put(self, request, address_id):
        # 查询要修改的地址对象
        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            return http.HttpResponseForbidden("地址id无效")

        # 接收参数
        json_dict = json.loads(request.body)
        """
        form_address: {
            title: '',
            receiver: '',
            province_id: '',
            city_id: '',
            district_id: '',
            place: '',
            mobile: '',
            tel: '',
            email: '',
        },
        """
        title = json_dict.get("title")
        receiver = json_dict.get("receiver")
        province_id = json_dict.get("province_id")
        city_id = json_dict.get("city_id")
        district_id = json_dict.get("district_id")
        place = json_dict.get("place")
        mobile = json_dict.get("mobile")
        tel = json_dict.get("tel")
        email = json_dict.get("email")

        # 校验参数
        if not all([title, receiver, province_id, city_id, district_id, place, mobile]):
            return http.HttpResponseForbidden("缺少必传参数")

        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('参数mobile有误')

        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')

        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')

        # 保存地址信息
        try:
            Address.objects.filter(id=address_id).update(
                user=request.user,
                title=title,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )
        except Exception:
            return http.HttpResponseForbidden("地址更新失败")
        else:
            # 构造响应数据
            address = Address.objects.get(id=address_id)
            address_dict = {
                "id": address.id,
                "title": address.title,
                "receiver": address.receiver,
                "province": address.province.name,
                "city": address.city.name,
                "district": address.district.name,
                "place": address.place,
                "mobile": address.mobile,
                "tel": address.tel,
                "email": address.email
            }
            # 响应更新地址结果
            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'address': address_dict})

    def delete(self, request, address_id):
        # 查询要修改的地址对象
        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            return http.HttpResponseForbidden("地址id无效")

        address.is_deleted = True
        address.save()

        return http.JsonResponse({"code": RETCODE.OK, "errmsg": "OK"})


class DefaultAddressView(mixins.LoginRequiredMixin, View):
    def put(self, request, address_id):
        # 查询要修改的地址对象
        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            return http.HttpResponseForbidden("地址id无效")

        user = request.user
        user.default_address_id = address_id
        user.save()

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})


class UpdateTitleAddressView(mixins.LoginRequiredMixin, View):
    def put(self, request, address_id):
        # 查询要修改的地址对象
        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            return http.HttpResponseForbidden("地址id无效")

        json_dict = json.loads(request.body)
        title = json_dict.get("title")

        address.title = title
        address.save()

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})


class ChangePasswordView(mixins.LoginRequiredMixin, View):
    def get(self, request):
        return render(request, "user_center_pass.html")

    def post(self, request):
        user = request.user
        # 获取参数
        old_pwd = request.POST.get("old_pwd")
        new_pwd = request.POST.get("new_pwd")
        new_cpwd = request.POST.get("new_cpwd")

        if not all([old_pwd, new_pwd, new_cpwd]):
            return http.HttpResponseForbidden("缺少必传参数")

        # 校验参数
        if not user.check_password(old_pwd):
            return render(request, "user_center_pass.html", {"origin_pwd_errmsg": "原始密码错误"})

        if not re.match(r"^[a-zA-Z0-9]{8,20}$", new_pwd):
            return http.HttpResponseForbidden("请输入8-20位的新密码")

        if new_cpwd != new_pwd:
            return http.HttpResponseForbidden("两次密码输入不一致")

        # 修改密码
        try:
            user.set_password(new_pwd)
            user.save()
        except Exception:
            return render(request, "user_center_pass.html", {"change_pwd_errmsg": "修改密码失败"})

        # 退出登录，清理状态保持信息
        logout(request)
        response = redirect("/login/")
        response.delete_cookie("username") # 删除vue变量username

        return response


class UserBrowseHistory(View):
    """用户浏览记录"""
    def post(self, request):
        """保存用户浏览记录"""
        user = request.user
        if not user.is_authenticated:
            return http.JsonResponse({"code": RETCODE.SESSIONERR, "errmsg": "用户未登录"})

        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get("sku_id")

        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden("sku不存在")

        redis_coon = get_redis_connection("history")
        pl = redis_coon.pipeline()

        key = "history_%s" % user.id

        # 先去重
        pl.lrem(key, 0, sku_id)

        # 再存储到列表开头
        pl.lpush(key, sku_id)

        # 截取前五个
        pl.ltrim(key, 0, 4)

        pl.execute()

        return http.JsonResponse({"code": RETCODE.OK, "errmsg": "OK"})

    def get(self, request):
        """获取用户浏览记录"""
        user = request.user

        redis_coon = get_redis_connection("history")
        sku_id_list = redis_coon.lrange("history_%s" % user.id, 0, -1)

        skus = []
        for sku_id in sku_id_list:
            sku = SKU.objects.get(id=sku_id)
            skus.append({
                "id": sku.id,
                "default_image_url": sku.default_image.url,
                "name": sku.name,
                "price": sku.price
            })

        return http.JsonResponse({"code": RETCODE.OK, "errmsg": "OK", "skus": skus})