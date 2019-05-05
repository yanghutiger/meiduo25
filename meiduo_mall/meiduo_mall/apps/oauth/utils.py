from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadData
from django.conf import settings


def generate_openid_signature(openid):
    # 对openid进行加密

    # 创建Serializer对象
    serializer = Serializer(secret_key=settings.SECRET_KEY, expires_in=600)

    data = {"openid": openid}

    data = serializer.dumps(data).decode()  # 加密后返回二进制要解码

    return data


def check_openid_signature(openid_sig):
    serializer = Serializer(secret_key=settings.SECRET_KEY, expires_in=600)

    try:
        data = serializer.loads(openid_sig)

    except BadData as e:
        return None

    else:
        return data.get("openid")