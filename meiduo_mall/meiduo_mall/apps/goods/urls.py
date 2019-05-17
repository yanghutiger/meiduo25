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
from .views import ListView, HotGoodsView, DetailView, DetailVisitView

urlpatterns = [
    url(r'^list/(?P<category_id>\d+)/(?P<page_num>\d+)/$', ListView.as_view(), name="list"),
    url(r'^hot/(?P<category_id>\d+)/$', HotGoodsView.as_view(), name="hotgoods"),

    # 商品详情界面
    url(r'^detail/(?P<sku_id>\d+)/$', DetailView.as_view(), name="detail"),

    # 统计商品访问量
    url(r'^detail/visit/(?P<category_id>\d+)/$', DetailVisitView.as_view(), name="detailvisit"),
]





