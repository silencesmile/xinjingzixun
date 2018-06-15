


# 过滤器
import functools

from flask import current_app
from flask import g
from flask import session

from info.models import User


def index_class(index):
    if index == 0:
        return "first"
    elif index == 1:
        return "second"
    elif index == 2:
        return "third"
    else:
        return ""

# 定义装饰器获取登陆状态
def request_login(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        user = None
        if user_id:
            try:
                user = User.query.filter_by(id=user_id).first()
            except Exception as e:
                current_app.logger.error(e)

        g.user = user
        return f(*args, **kwargs)

    return wrapper


