from django.shortcuts import render
from django.views import View
import json, pickle, base64
from django import http
from django_redis import get_redis_connection

from goods.models import SKU
from meiduo_mall.utils.response_code import RETCODE
# Create your views here.


class CartsView(View):
    def post(self, request):

        # 接收参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get("sku_id")
        count = json_dict.get("count")
        selected = json_dict.get("selected", True)

        # 校验
        if all([sku_id, count]) is False:
            return http.HttpResponseForbidden("缺少必传参数")

        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden("sku不存在")

        try:
            count = int(count)
        except Exception:
            return http.HttpResponseForbidden("参数count有误")

        if selected:
            if not isinstance(selected, bool):
                return http.HttpResponseForbidden('参数selected有误')

        user = request.user
        response = http.JsonResponse({"code": RETCODE.OK, "errmsg": "OK"})

        if user.is_authenticated:
            # 操作redis数据库
            redis_conn = get_redis_connection("carts")
            pl = redis_conn.pipeline()

            """
            hash: {sku_id_1: count, sku_id2: count}
            set: {sku_id_1, sku_id_2}
            """
            # hincrby()
            pl.hincrby("carts_%s" % user.id, sku_id, count)

            # sadd()
            if selected:  # 只有勾选的才向set集合中添加
                pl.sadd('selected_%s' % user.id, sku_id)

            pl.execute()

        else:
            # 操作cookie
            """
            {
                sku_id_1: {'count': 2, 'selected': True},
                sku_id_2: {'count': 2, 'selected': True}
            }
            """
            # 判断cookie中是否存在购物车数据
            carts_str = request.COOKIES.get("carts")
            if carts_str:
                # 如果cookie中有购物车数据,把cookie购物车字符串转回到字典
                # cart_str_bytes = cart_str.encode()
                # cart_bytes = base64.b64decode(cart_str_bytes)
                # cart_dict = pickle.loads(cart_bytes)
                carts_dict = pickle.loads(base64.b64decode(carts_str.encode()))
            else:
                carts_dict = {}

            # 判断要添加的sku_id 在字典中是否存在,如果存在,需要对count做增量计算
            if sku_id in carts_dict:
                origin_count = carts_dict[sku_id]["count"]
                count += origin_count

            # 添加
            carts_dict[sku_id] = {
                'count': count,
                'selected': selected
            }

            carts_str = base64.b64encode(pickle.dumps(carts_dict)).decode()

            response.set_cookie("carts", carts_str)

        return response

    def get(self, request):
        user = request.user
        # 判断用户是否登录
        if user.is_authenticated:
            redis_conn = get_redis_connection("carts")

            # 获取hash数据
            redis_carts = redis_conn.hgetall("carts_%s" % user.id)

            # 获取set数据{b'1', b'2'}
            selected_ids = redis_conn.smembers('selected_%s' % user.id)

            # 将redis购物车数据格式转换成和cookie购物车数据格式一致  目的为了后续数据查询转换代码和cookie共用一套代码
            carts_dict = {}
            for sku_id_bytes, count_bytes in redis_carts.items():
                carts_dict[int(sku_id_bytes)] = {
                    'count': int(count_bytes),
                    'selected': sku_id_bytes in selected_ids
                }
        else:
            carts_str = request.COOKIES.get("carts")

            # 判断有没有cookie购物车数据
            if carts_str:
                carts_dict = pickle.loads(base64.b64decode(carts_str.encode()))
            else:
                return render(request, "cart.html")

        sku_qs = SKU.objects.filter(id__in=carts_dict.keys())
        cart_skus = []
        for sku in sku_qs:
            cart_skus.append({
                "id": sku.id,
                "name": sku.name,
                "price": str(sku.price),
                "default_image_url": sku.default_image.url,
                "count": int(carts_dict[sku.id]["count"]),
                "selected": str(carts_dict[sku.id]["selected"]),
                "amount": str(sku.price * int(carts_dict[sku.id]['count']))
            })

        context = {
            "cart_skus": cart_skus
        }

        return render(request, "cart.html", context)

    def put(self, request):
        """修改购物车数据"""

        # 接收参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get("sku_id")
        count = json_dict.get("count")
        selected = json_dict.get("selected")

        # 校验
        if not all([sku_id, count]):
            return http.HttpResponseForbidden("缺少必传参数")

        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden("sku不存在")

        try:
            count = int(count)
        except Exception:
            return http.HttpResponseForbidden("参数count有误")

        cart_sku = {
            "id": sku_id,
            "name": sku.name,
            "price": sku.price,
            "default_image_url": sku.default_image.url,
            "count": count,
            "amount": sku.price * count,
            "selected": selected
        }

        response = http.JsonResponse({"code": RETCODE.OK, "errmsg": "OK", "cart_sku": cart_sku})

        # 判断用户是否登录
        user = request.user
        if user.is_authenticated:
            # 获取redis中的购物车数据
            redis_coon = get_redis_connection("carts")
            pl = redis_coon.pipeline()

            pl.hset("carts_%s" % user.id, sku_id, count)

            if selected:
                pl.sadd("selected_%s" % user.id, sku_id)
            else:
                pl.srem("selected_%s" % user.id, sku_id)

            pl.execute()

        else:
            # 获取cookie中的购物车
            carts_str = request.COOKIES.get("carts")

            # 判断cookie有没有值
            if carts_str:
                carts_dict = pickle.loads(base64.b64decode(carts_str.encode()))
            else:
                return http.JsonResponse({"code": RETCODE.DBERR, "errmsg": "cookie数据没有获取"})

            carts_dict[sku_id] = {
                "count": count,
                "selected": selected
            }

            carts_str = base64.b64encode(pickle.dumps(carts_dict)).decode()
            response.set_cookie("carts", carts_str)

        return response

    def delete(self, request):
        # 获取参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get("sku_id")

        # 校验参数
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden("sku不存在")

        response = http.JsonResponse({"code": RETCODE.OK, "errmsg": "OK"})

        # 判断用户是否登录
        user = request.user
        if user.is_authenticated:
            redis_coon = get_redis_connection("carts")
            pl = redis_coon.pipeline()

            pl.hdel("carts_%s" % user.id, sku_id)
            pl.srem("selected_%s" % user.id, sku_id)

            pl.execute()

        else:
            # 获取cookie中的购物车
            carts_str = request.COOKIES.get("carts")

            if carts_str:
                carts_dict = pickle.loads(base64.b64decode(carts_str.encode()))

            else:
                return http.JsonResponse({"code": RETCODE.DBERR, "errmsg": "cookie没有获取到"})

            if sku_id in carts_dict:
                del carts_dict[sku_id]

            if len(carts_dict.keys()) == 0:
                response.delete_cookie("carts")
                return response

            carts_str = base64.b64encode(pickle.dumps(carts_dict)).decode()
            response.set_cookie("carts", carts_str)

        return response


class CartsSelectAllView(View):
    """全选购物车"""

    def put(self, request):
        selected = json.loads(request.body.decode()).get("selected")

        if not isinstance(selected, bool):
            return http.HttpResponseForbidden("参数selected有误")

        # 判断用户是否登录
        user = request.user

        response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})
        if user.is_authenticated:
            redis_conn = get_redis_connection("carts")
            redis_carts = redis_conn.hgetall("carts_%s" % user.id)

            if selected:
                redis_conn.sadd("selected_%s" % user.id, *redis_carts.keys())
            else:
                # redis_conn.srem("selected_%s" % user.id, *carts_dict.keys())
                redis_conn.delete("selected_%s" % user.id)

        else:
            carts_str = request.COOKIES.get("carts")
            if carts_str:
                carts_dict = pickle.loads(base64.b64decode(carts_str.encode()))
            else:
                return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': 'cookie数据没有获取到'})

            for sku_id in carts_dict:
                carts_dict[sku_id]["selected"] = selected

            carts_str = base64.b64encode(pickle.dumps(carts_dict)).decode()
            response.set_cookie("carts", carts_str)

        return response


class CartsSimpleView(View):
    """商品页面右上角购物车"""
    # 复制CartsView视图中到get，再进行修改

    def get(self, request):

        user = request.user
        if user.is_authenticated:

            # 创建redis连接对象
            redis_conn = get_redis_connection('carts')
            # 获取hash数据
            redis_carts = redis_conn.hgetall('carts_%s' % user.id)

            # 获取set数据{b'1', b'2'}
            selected_ids = redis_conn.smembers('selected_%s' % user.id)
            # 将redis购物车数据格式转换成和cookie购物车数据格式一致  目的为了后续数据查询转换代码和cookie共用一套代码
            cart_dict = {}
            for sku_id_bytes, count_bytes in redis_carts.items():
                cart_dict[int(sku_id_bytes)] = {
                    'count': int(count_bytes),
                    'selected': sku_id_bytes in selected_ids
                }

        else:
            # 获取cookie购物车数据
            cart_str = request.COOKIES.get('carts')
            # 判断有没有cookie购物车数据
            if cart_str:
                # 将字符串转换成字典
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                return http.JsonResponse({"code": RETCODE.DBERR, "errmsg": "为获取到cookie中到购物车数据"})

        # 查询到购物车中所有sku_id对应的sku模型
        sku_qs = SKU.objects.filter(id__in=cart_dict.keys())
        cart_skus = []  # 用来装每个转换好的sku字典
        for sku in sku_qs:
            sku_dict = {
                'id': sku.id,
                'name': sku.name,
                'default_image_url': sku.default_image.url,
                'count': int(cart_dict[sku.id]['count']),  # 方便js中的json对数据渲染
            }
            cart_skus.append(sku_dict)

        return http.JsonResponse({"code": RETCODE.OK, "errmsg": "OK", "cart_skus": cart_skus})
