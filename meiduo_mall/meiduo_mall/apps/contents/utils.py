from goods.models import GoodsChannel


def get_categories():
    """
    商品分类及广告数据展示
    """
    """
       { 
           "1": {
               'channels': [cat1-1, cat1-2,...]  第一组里面的所有一级数据
               'sub_cats': [cat2-1, cat2-2]   用来装所有二级数据, 在二级中再包含三级数据cat2-1.cat_subs = cat3
               },

           "2": {
               'channels': [cat1-1...],
               'sub_cats': [...]
               }


       }
    """

    categories = {}  # 用来包装所有商品数据

    goodchannel_qs = GoodsChannel.objects.order_by("group_id", "sequence")  # 查询一级数据

    for channel in goodchannel_qs:
        group_id = channel.group_id  # 获取组号

        # 判断当前的组号在字典中是否存在
        if group_id not in categories:
            categories[group_id] = {"channels": [], "sub_cats": []}

        cat1 = channel.category  # 获取一级类别数据
        cat1.url = channel.url   # 将频道中的url绑定给一级类型对象
        categories[group_id]["channels"].append(cat1)

        cat2_qs = cat1.subs.all()  # 获取当前一组下面的所有二级数据
        for cat2 in cat2_qs:
            cat3_qs = cat2.subs.all()  # 获取当前二级下面的所有三级 得到三级查询集
            cat2.sub_cats = cat3_qs  # 把二级下面的所有三级绑定给cat2对象的cat_subs属性,由前端代码可得
            categories[group_id]["sub_cats"].append(cat2)

    return categories
