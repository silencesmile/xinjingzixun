from flask import g, jsonify, session,current_app
from flask import redirect,render_template
from flask import request

from info.models import Category, News
from info.utils.image_storage import storage
from info.utils.response_code import RET
from . import profile_blu
from info.utils.commons import request_login
from info import db
from info.constants import QINIU_DOMIN_PREFIX

@profile_blu.route("/info")
@request_login
def info():

    user = g.user
    if not user:
        return redirect("/")

    data = {
        "user":user.to_dict()
    }

    return render_template("user/user.html", data=data)

@profile_blu.route("/base_info", methods = ["POST", "GET"])
@request_login
def base_info():
    user = g.user
    if request.method == 'GET':
        data = {
            'user': user.to_dict()
        }

        return render_template('user/user_base_info.html', data=data)

    nick_name = request.json.get("nick_name")
    signature = request.json.get("signature")
    gender = request.json.get("gender")

    print(nick_name, signature, gender)

    if not all([nick_name, signature, gender]):
        return jsonify(error=RET.PARAMERR, errmsg="参数不完整")

    if gender not in ["MAN", "WOMAN"]:
        return jsonify(error=RET.PARAMERR, errmsg="参数有无")

    user.nick_name = nick_name
    user.gender = gender
    user.signature = signature

    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()

        return jsonify(error = RET.DBERR, errmsg = "存储失败")

    session["nick_name"] = user.nick_name

    return jsonify(error = RET.OK, errmsg="OK")

@profile_blu.route("/pic_info", methods=["POST", "GET"])
@request_login
def pic_info():
    user = g.user
    if request.method == "GET":
        data = {
            'user': user.to_dict()
        }

        return render_template("user/user_pic_info.html", data=data)

    avatar = request.files.get("avatar")
    if not avatar:
        return jsonify(error=RET.PARAMERR, errmsg="图片为空")

    avatar_data = avatar.read()
    try:
        image_name = storage(avatar_data)
    except Exception as e:
        return jsonify(error = RET.THIRDERR, errmsg="七牛云")

    user.avatar_url = image_name

    try:
        db.session.commit()
    except Exception as e:
        return jsonify(error=RET.THIRDERR, errmsg="mysql错误")

    # 拼接完整图片：
    avatar_url = QINIU_DOMIN_PREFIX +  user.avatar_url

    data = {
        "avatar_url":avatar_url
    }

    return jsonify(error=RET.OK, errmsg = "OK", data=data)

@profile_blu.route("/follow")
@request_login
def follow():


    return "关注列表"

@profile_blu.route("/pass_info", methods = ["POST", "GET"])
@request_login
def pass_info():
    user = g.user

    if request.method == "GET":
        print("pass---get")
        return render_template("user/user_pass_info.html")

    print("AAAAA")
    old_password = request.json.get("old_password")
    new_password = request.json.get("new_password")

    print(old_password, new_password)

    if not all([old_password, new_password]):
        return jsonify(error = RET.PARAMERR, errmsg = "参数不全")

    if not user.check_password(old_password):
        return jsonify(error=RET.PARAMERR, errmsg="原密码错误")

    user.password = new_password

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(error=RET.DBERR, errmsg="保存数据库错误")

    return jsonify(error=RET.OK, errmsg="ok")

@profile_blu.route("/collection")
@request_login
def collection():


    return "收藏列表"

@profile_blu.route("/news_release", methods = ["POST", "GET"])
@request_login
def news_release():
    user = g.user
    if request.method == "GET":
        categorys = Category.query.all()
        category_list = []
        for category in categorys:
            category_list.append(category.to_dict())

        category_list.pop(0)
        print(category_list)
        data = {
            "categories":category_list
        }

        return render_template("user/user_news_release.html", data=data)

        # 获取post请求的参数
    title = request.form.get('title')
    category_id = request.form.get('category_id')
    digest = request.form.get('digest')
    index_image = request.files.get('index_image')
    content = request.form.get('content')

    print(title)
    # 检查参数的完整性
    if not all([title, category_id, digest, index_image, content]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数缺失')
    # 把分类id转成int
    category_id = int(category_id)

    newsImg_data = index_image.read()

    try:
        newsImg_name = storage(newsImg_data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg='牛牛')

    news = News()
    news.user_id = user.id
    news.title = title
    news.category_id = category_id
    news.digest = digest
    news.index_image_url = QINIU_DOMIN_PREFIX + newsImg_name
    news.content = content
    news.source = "个人"
    news.status = 1

    # 提交数据到数据库中
    try:
        db.session.add(news)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg='保存数据失败')
    # 返回结果
    return jsonify(errno=RET.OK, errmsg='OK')

@profile_blu.route("/news_list")
@request_login
def news_list():


    return "新闻列表"