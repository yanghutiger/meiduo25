# celery启动文件
from celery import Celery
import os

# 告诉celery，它里面用的django配置文件在哪
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meiduo_mall.settings.dev")

# 创建celery实例
celery_app = Celery('meiduo')

# 加载celery配置
celery_app.config_from_object('celery_tasks.config')

# 自动注册celery任务
celery_app.autodiscover_tasks(['celery_tasks.sms', 'celery_tasks.email'])