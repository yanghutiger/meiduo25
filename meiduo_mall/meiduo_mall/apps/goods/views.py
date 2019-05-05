from django.shortcuts import render
from django.views import View
from django import http
from django.core.paginator import Paginator

from contents.utils import get_categories
from .models import GoodsCategory, SKU
from .utils import get_breadcrumb
from meiduo_mall.utils.response_code import RETCODE

# Create your views here.


class ListView(View):
    def get(self, request, category_id, page_num):

        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return http.HttpResponseNotFound("商品类型不存在")

        sort = request.GET.get("sort", "default")
        if sort == "hot":
            sort_field = "-sales"
        elif sort == "price":
            sort_field = "price"
        else:
            sort_field = "create_time"

        sku_qs = SKU.objects.filter(category_id=category_id, is_launched=True).order_by(sort_field)
        paginator = Paginator(sku_qs, 5)
        page_skus = paginator.page(page_num)
        total_page = paginator.num_pages

        # 渲染页面
        context = {
            'categories': get_categories(),  # 频道分类
            'breadcrumb': get_breadcrumb(category),  # 面包屑导航
            'sort': sort,  # 排序字段
            'category': category,  # 第三级分类
            'page_skus': page_skus,  # 分页后数据
            'total_page': total_page,  # 总页数
            'page_num': page_num,  # 当前页码
        }
        return render(request, "list.html", context)


class HotGoodsView(View):
    def get(self, request, category_id):
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return http.HttpResponseNotFound('商品类别不存在')

        # hot_skus_qs = SKU.objects.filter(category_id=category_id, is_launched=True).order_by("-sales")[0:2]
        hot_skus_qs = category.sku_set.filter(is_launched=True).order_by('-sales')[0:2]

        hot_skus = []
        # for sku in hot_skus:
        #     hot_skus.append(sku)

        for sku in hot_skus_qs:
            hot_skus.append({
                'id': sku.id,
                'name': sku.name,
                'price': sku.price,
                'default_image_url': sku.default_image.url
            })
            # 不能直接在返回json数据时传对象，因为json不能序列化对象，所有此时append字典或列表

        return http.JsonResponse({"code": RETCODE.OK, "errmsg": "OK", "hot_skus": hot_skus})