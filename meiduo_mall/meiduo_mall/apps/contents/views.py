from django.shortcuts import render
from django.views.generic import View

from .models import ContentCategory
from .utils import get_categories
# Create your views here.


class IndexView(View):
    def get(self, request):
        """
        广告数据展示
        """
        """
        {
            'index_lbt': lbt_qs,
            'index_kx': kx_qs
        }
        """
        contents = {}
        contentcategory_qs = ContentCategory.objects.all()  # 获取所有广告类别数据

        for category in contentcategory_qs:
            content_qs = category.content_set.filter(status=True).order_by("sequence")
            contents[category.key] = content_qs

        context = {
            "categories": get_categories(),
            "contents": contents
        }

        return render(request, "index.html", context)