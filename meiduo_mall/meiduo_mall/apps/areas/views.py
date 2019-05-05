from django.shortcuts import render
from django.contrib.auth import mixins
from django.views import View
from django import http
from django.core.cache import cache

from .models import Area
from meiduo_mall.utils.response_code import RETCODE
# Create your views here.


class AreasView(mixins.LoginRequiredMixin, View):
    def get(self, request):
        # 获取area_id参数
        area_id = request.GET.get("area_id")

        if area_id is None:
            # 先尝试性去redis获取省份
            provinces_list = cache.get("provinces_list")

            if not provinces_list:
                # 如果redis中没有省份
                # 获取省份
                provinces_model_qs = Area.objects.filter(parent_id=None)
                provinces_list = []
                for province in provinces_model_qs:
                    province_dict = {
                        "id": province.id,
                        "name": province.name
                    }
                    provinces_list.append(province_dict)
                cache.set("provinces_list", provinces_list, 3600)

            return http.JsonResponse({"code": RETCODE.OK, "errmsg": "OK", "province_list": provinces_list})

        else:
            # 先尝试性去redis获取sub_data
            sub_data = cache.get("sub_data_%s" % area_id)

            if not sub_data:
                # 如果redis中没有
                # 通过省id获取市，通过市id获取区
                try:
                    area_model = Area.objects.get(id=area_id)
                except Area.DoesNotExist:
                    return http.HttpResponseForbidden("area_id无效")
                else:
                    area_model_qs = area_model.subs.all()
                    subs = []
                    for area in area_model_qs:
                        area_dict = {
                            "id": area.id,
                            "name": area.name
                        }
                        subs.append(area_dict)
                    sub_data = {
                        "id": area_model.id,
                        "name": area_model.name,
                        "subs": subs
                    }
                    cache.set("sub_data_%s" % area_id, sub_data, 3600)

            return http.JsonResponse({"code": RETCODE.OK, "errmsg": "OK", "sub_data": sub_data})