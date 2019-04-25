from meiduo_mall.libs.captcha.captcha import captcha
from django.views.generic import View
from django_redis import get_redis_connection
from django import http
from meiduo_mall.utils.response_code import RETCODE
import random
import logging
from celery_tasks.sms.tasks import send_sms_code
# Create your views here.

logger = logging.getLogger("django")

class ImageCodeView(View):
    def get(self, request, uuid):
        name, text, image = captcha.generate_captcha()
        redis_coon = get_redis_connection("verify_code")
        redis_coon.setex("img_%s" % uuid, 300, text)
        return http.HttpResponse(image, content_type="image/png")


class SMSCodeView(View):
    def get(self, request, mobile):
        # 避免频繁发送验证码
        redis_conn = get_redis_connection("verify_code")
        if redis_conn.get("send_flag_%s" % mobile):
            return http.JsonResponse({"code": RETCODE.THROTTLINGERR, "errmsg": "发送短信验证码过于频繁"})

        # 接收参数
        image_code_client = request.GET.get("image_code")
        uuid = request.GET.get("uuid")

        # 校验参数
        if not all([image_code_client, uuid]):
            return http.JsonResponse({"code": RETCODE.NECESSARYPARAMERR, "errmsg": "缺少必传参数"})

        #获取图形验证码
        image_code_server = redis_conn.get("img_%s" % uuid)

        # 删除图形验证码
        redis_conn.delete("img_%s" % uuid)

        # 对比图形验证码
        if image_code_server is None or image_code_server.decode().lower() != image_code_client.lower():
            return http.JsonResponse({"code": RETCODE.IMAGECODEERR, "errmsg": "验证码错误"})

        # 生成短信验证码
        sms_code = "%06d" % random.randint(0, 999999)
        logger.info(sms_code)

        # 创建redis管道
            # # 保存短信验证码
            # redis_conn.setex("sms_%s" % mobile, 300, sms_code)
            # # 设置短信验证码标志
            # redis_conn.setex("send_flag_%s" % mobile, 60, 1)
        pl = redis_conn.pipeline()
        pl.setex("sms_%s" % mobile, 300, sms_code)
        pl.setex("send_flag_%s" % mobile, 60, 1)
        pl.execute()

        # 调用发送短信任务
            # # 发送短信验证码
            # CCP().send_template_sms(mobile, [sms_code, 5], 1)
        send_sms_code.delay(mobile, sms_code)

        # 响应结果
        return http.JsonResponse({"code": RETCODE.OK, "errmsg": "短信发送成功"})