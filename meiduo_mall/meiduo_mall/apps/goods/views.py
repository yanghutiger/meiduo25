from django.shortcuts import render
from django.views import View
from django import http
from django.core.paginator import Paginator
from django.utils import timezone

from contents.utils import get_categories
from .models import GoodsCategory, SKU, SPUSpecification, SpecificationOption, SKUSpecification, GoodsVisitCount
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


class DetailView(View):
    def get(self, request, sku_id):
        """提供商品详情页"""
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return render(request, '404.html')

        category = sku.category

        # 获取商品详情等
        spu = sku.spu

        """1.准备当前商品的规格选项列表[8, 11]"""
        current_sku_spec_qs = sku.specs.order_by("spec_id")
        current_sku_option_ids = []
        for current_spec in current_sku_spec_qs:
            current_sku_option_ids.append(current_spec.option_id)
        print(current_sku_option_ids)

        """2.构建规格选择仓库{(8, 11): 3, (8, 12): 4, (9, 11): 5, (9, 12): 6, (10, 11): 7, (10, 12): 8}"""
        temp_sku_qs = spu.sku_set.all()

        temp_sku_map = {}
        for temp_sku in temp_sku_qs:
            temp_sku_spec_qs = temp_sku.specs.order_by("spec_id")
            temp_sku_option_ids = []
            for temp_spec in temp_sku_spec_qs:
                temp_sku_option_ids.append(temp_spec.option_id)
            temp_sku_map[tuple(temp_sku_option_ids)] = temp_sku.id
            # print(temp_sku_map)

        """3.组合，并找到sku_id进行绑定"""
        spu_spec_qs = spu.specs.order_by('id')  # 获取当前spu中的所有规格

        for index, spec in enumerate(spu_spec_qs):  # 遍历当前所有的规格
            # print(spec)
            spec_option_qs = spec.options.all()  # 获取当前规格中的所有选项
            temp_option_ids = current_sku_option_ids[:]  # 复制一个新的当前显示商品的规格选项列表
            for option in spec_option_qs:  # 遍历当前规格下的所有选项
                temp_option_ids[index] = option.id  # [8, 12]
                # print(temp_option_ids)
                option.sku_id = temp_sku_map.get(tuple(temp_option_ids))  # 给每个选项对象绑定下他sku_id属性

            spec.spec_options = spec_option_qs  # 把规格下的所有选项绑定到规格对象的spec_options属性上

        # 获取商品规格等
        # spu_spec_qs = SPUSpecification.objects.filter(spu_id=spu.id).order_by("id")
        #
        # # 商品选项
        # for spu_spec in spu_spec_qs:
        #     spec_opt_qs = SpecificationOption.objects.filter(spec=spu_spec)
        #     spu_spec.opt_qs = spec_opt_qs

        context = {
            "categories": get_categories(),
            "breadcrumb": get_breadcrumb(category),
            "sku": sku,
            "spu": spu,
            "spu_spec": spu_spec_qs
        }
        return render(request, 'detail.html', context)


class DetailVisitView(View):
    """详情页分类商品访问量"""
    def post(self, request, category_id):
        """记录分类商品访问量"""
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return http.HttpResponseForbidden("商品类别不存在")

        today_date = timezone.localdate()
        try:
            count_date = GoodsVisitCount.objects.get(category=category, date=today_date)
        except GoodsVisitCount.DoesNotExist:
            count_date = GoodsVisitCount(
                category=category,
            )

        count_date.count += 1
        count_date.save()
        return http.JsonResponse({"code": RETCODE.OK, "errmsg": "OK"})