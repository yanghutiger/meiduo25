from django.contrib.auth.backends import ModelBackend
import re
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadData
from django.conf import settings

from .models import User


def get_user_by_account(account):
    try:
        if re.match(r"^1[3-9]\d{9}$", account):
            user = User.objects.get(mobile=account)
        else:
            user = User.objects.get(username=account)
    except User.DoesNotExist:
        return None
    else:
        return user


class UsernameMobileAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        user = get_user_by_account(username)

        if user and user.check_password(password):
            return user


def generate_verify_email_url(user):
    # 对当前传入对user生成激活邮箱

    serializer = Serializer(secret_key=settings.SECRET_KEY, expires_in=3600 * 24)
    data = {"user_id": user.id, "email": user.email}
    data_sig = serializer.dumps(data).decode()
    verify_url = settings.EMAIL_VERIFY_URL + "?token=" + data_sig

    return verify_url


def check_token_to_user(token):
    serializer = Serializer(secret_key=settings.SECRET_KEY, expires_in=3600 * 24)
    try:
        data = serializer.loads(token)
    except BadData as e:
        return None
    else:
        user_id = data.get("user_id")
        email = data.get("email")
        try:
            user = User.objects.get(id = user_id, email=email)
        except User.DoesNotExist as e:
            return None
        else:
            return user