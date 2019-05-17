import pickle, base64
from django_redis import get_redis_connection


def merge_cart_cookie_to_redis(request, user, response):
    """
    登录时合并购物车
    :param request: 登录时借用过来的请求对象
    :param user: 登录时借用过来的用户对象
    :param response: 借用过来准备做删除cookie的响应对象
    :return:
    """

    carts_str = request.COOKIES.get("carts")

    if carts_str:
        carts_dict = pickle.loads(base64.b64decode(carts_str.encode()))

    else:
        return

    # 创建redis连接对象
    redis_conn = get_redis_connection("carts")
    pl = redis_conn.pipeline()

    for sku_id, sku_dict in carts_dict.items():
        pl.hset("carts_%s" % user.id, sku_id, sku_dict["count"])
        if sku_dict["selected"]:
            pl.sadd("selected_%s" % user.id, sku_id)
        else:
            pl.srem("selected_%s" % user.id, sku_id)

    pl.execute()

    response.delete_cookie("carts")