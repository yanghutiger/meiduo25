"""meiduo_mall URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from .views import RegisterView, UsernameCountView, MobileCountView, LoginView, LogoutView, UserInfoView, EmailView, VerifyEmailView, AddressView, CreateAddress, UpdateDestroyAddressView, DefaultAddressView, UpdateTitleAddressView, ChangePasswordView

urlpatterns = [
    url(r'^register/$', RegisterView.as_view(), name="register"),
    url(r'^usernames/(?P<username>[a-zA-Z0-9_-]{5,20})/count/$', UsernameCountView.as_view(), name="usernamecount"),
    url(r'^mobiles/(?P<mobile>1[3456789]\d{9})/count/$', MobileCountView.as_view(), name="mobilecount"),
    url(r'^login/$', LoginView.as_view(), name="login"),
    url(r'^logout/$', LogoutView.as_view(), name="logout"),
    url(r'^info/$', UserInfoView.as_view(), name="info"),
    url(r'^emails/$', EmailView.as_view(), name="email"),
    url(r'^emails/verification/$', VerifyEmailView.as_view(), name="verifyemail"),

    # 收货地址界面
    url(r'^addresses/$', AddressView.as_view(), name="address"),

    # 新增收货地址
    url(r'^addresses/create/$', CreateAddress.as_view(), name="createaddress"),

    # 修改/删除收货地址
    url(r'^addresses/(?P<address_id>\d+)/$', UpdateDestroyAddressView.as_view(), name="updatedestroyaddress"),

    # 设置默认收货地址
    url(r'^addresses/(?P<address_id>\d+)/default/$', DefaultAddressView.as_view(), name="defaultaddress"),

    # 修改地址标题
    url(r'^addresses/(?P<address_id>\d+)/title/$', UpdateTitleAddressView.as_view(), name="updatetitleaddress"),

    # 修改密码
    url(r'^password/$', ChangePasswordView.as_view(), name="changepassword"),

]
