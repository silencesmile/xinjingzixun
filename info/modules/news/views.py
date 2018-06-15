from flask import g
from flask import request
from flask import session, current_app, jsonify

from info import db
from info.models import User, News, Category, Comment, CommentLike
from info.utils.response_code import RET
from . import news_blue
from flask import render_template
from info.constants import CLICK_RANK_MAX_NEWS
from info.utils.commons import request_login

@news_blue.route("/")
def index():
    user_id = session.get("user_id")

    # 如果用户存在，向mysql请求相关信息
    user = None
    if user_id:
        try:
            user = User.query.filter_by(id=user_id).first()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(error=RET.DBERR, errmsg="redis密码错误")

    # 加载排行榜
    news_list = None
    try:
        news_list = News.query.order_by(News.clicks.desc()).limit(CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg="数据库查询新闻信息失败")

    on_click_news = []
    for news in news_list:
        on_click_news.append(news.to_dict())

    # 加载新闻分类
    try:
        categorys = Category.query.all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg = "查询分类失败")

    if not categorys:
        return jsonify(error=RET.PARAMERR, errmsg = "无查询分类")

    category_list = []
    for category in categorys:
        category_list.append(category.to_dict())

        # if user:
            #     return user.to_dict()
            # else:
            #     return None

    data = {
        # 如果user存在则user_info=user.to_dict()， 否则 user_info=None
        'user_info': user.to_dict() if user else None,
        "on_click_news":on_click_news,
        "category_list":category_list
    }

    return render_template("news/index.html", data=data,on_click_news=on_click_news, category_list = category_list)

@news_blue.route("/news_list")
def news_list():
    cid = request.args.get("cid", "1")
    page = request.args.get("page", "1")
    per_page = request.args.get("per_page", "10")

    if not cid:
        return jsonify(error=RET.PARAMERR, errmsg = "新闻展示失败")

    cid, page, per_page = int(cid), int(page), int(per_page)

    if cid > 1:
        newsC_list = News.query.filter_by(category_id=cid).order_by(News.create_time.desc()).paginate(page,per_page, False)
    else:
        newsC_list = News.query.filter_by().order_by(News.create_time.desc()).paginate(page,per_page, False)

    paginates = newsC_list.items
    currentPage = newsC_list.page
    total_page = newsC_list.pages

    if not newsC_list:
        return jsonify(error=RET.DBERR, errmsg="查询分类新闻失败")

    newsC_listC = []
    for news in paginates:
        newsC_listC.append(news.to_dict())

    data = {
        "cid":cid,
        "currentPage":currentPage,
        "total_page":total_page,
        "error":0,
        "errmsg":"数据查询失败",
        "newsC_listC":newsC_listC
    }
    return jsonify(error = RET.OK, errmsg = "数据查询失败", data=data)

@news_blue.route("/<int:args>")
@request_login
def news_detail(args):
    user = g.user


    try:
        news = News.query.filter_by(id=args).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error = RET.DBERR, errmsg = "查询新闻详情失败")

    if not news:
        return jsonify(error = RET.DBERR, errmsg = "新闻详情不存在")

    # 如果news存在，点击次数加1
    news.clicks += 1
    # SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    try:
        db.session.add(news)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg='保存数据失败')

    coll = ""
    if user:
        try:
            coll_news = user.collection_news
        except Exception as e:
            current_app.logger.error(e)

        if coll_news:
            if news in coll_news:
                # print("用户已收藏")
                coll = "coll"

                # 评论
    comments = []
    try:
        comments = Comment.query.filter(Comment.news_id == news_id).order_by(Comment.create_time.desc()).all()
    except Exception as e:
        current_app.logger.error(e)
    comment_like_ids = []
    # 获取当前登录用户的所有评论的id，
    if user:
        try:
            comment_ids = [comment.id for comment in comments]
            # 再查询点赞了哪些评论
            comment_likes = CommentLike.query.filter(CommentLike.comment_id.in_(comment_ids),
                                                     CommentLike.user_id == g.user.id).all()
            # 遍历点赞的评论数据,获取
            comment_like_ids = [comment_like.comment_id for comment_like in comment_likes]
        except Exception as e:
            current_app.logger.error(e)
    comment_dict_li = []
    for comment in comments:
        comment_dict = comment.to_dict()
        # 如果未点赞
        comment_dict['is_like'] = False
        # 如果点赞
        if comment.id in comment_like_ids:
            comment_dict['is_list'] = True
        comment_dict_li.append(comment_dict)

    # 关注
    is_followed = False
    # 用户关注新闻的发布者，即登录用户关注作者。，
    if news.user and user:
        if news.user in user.followers:
            is_followed = True
    # 项目首页的点击排行：默认按照新闻点击次数进行排序，limit6条
    try:
        news_list = News.query.order_by(News.clicks.desc()).limit(6)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询数据库失败')
    # 判断查询结果
    if not news_list:
        return jsonify(errno=RET.NODATA, errmsg='无新闻数据')
    # 定义容器，存储查询结果对象转成的字典数据
    news_dict_list = []
    for index in news_list:
        news_dict_list.append(index.to_dict())

    data = {
        "user":user,
        "news":news.to_dict(),
        'news_dict_list': news_dict_list,
        "coll":coll,
        'comments': comment_dict_li
    }

    return render_template("/news/detail.html", data = data)

# 收藏新闻
@news_blue.route("/news_collect", methods=["POST"])
@request_login
def news_collect():
    user = g.user
    if not user:
        return jsonify(error=RET.SESSIONERR, errmsg='用户未登录')

    news_id = request.json.get("news_id")
    onclick = request.json.get("action")
    print(news_id, onclick)

    if not all([news_id, onclick]):
        return jsonify(error=RET.PARAMERR, errmsg='参数不全')

    try:
        news = News.query.filter_by(id = news_id).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg='查询news失败')

    if not news:
        return jsonify(error=RET.DBERR, errmsg='该新闻不存在')

    # 定义返回结果
    data = { }

    coll_news = user.collection_news
    if news in coll_news:
        print("取消馆收藏")
        user.collection_news.remove(news)
        data = {
            "error": "0",
            "coll": "cancellColl"
        }
    else:
        print("添加收藏")
        user.collection_news.append(news)
        data = {
            "error": "0",
            "coll": "coll"
        }
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(error=RET.DBERR, errmsg='收藏操作失败')
    # 返回结果
    return jsonify(data)

# 评论模块
@news_blue.route("/news_comment", methods=["POST"])
@request_login
def news_comment():
    user = g.user
    if not user:
        return jsonify(error=RET.SESSIONERR, errmsg='用户未登录')
    print('test111')
    news_id = request.json.get('news_id')
    parent_id = request.json.get('parent_id')
    content = request.json.get('comment')

    print(news_id, content)

    if not all([news_id, content]):
        return jsonify(error=RET.PARAMERR, errmsg='参数缺失111')

    news_id = int(news_id)
    if news_id:
        if parent_id:
            parent_id = int(parent_id)
    try:
        news = News.query.filter_by(id = news_id).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg='查询新闻出错')

    if not news:
        return jsonify(error=RET.DBERR, errmsg='该news不存在')

    comment = Comment()
    comment.news_id = news_id
    comment.user_id = user.id
    comment.content = content
    if parent_id:
        comment.parent_id = parent_id

    try:
        db.session.add(comment)
        db.session.commit()

    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()

        return jsonify(error=RET.DBERR, errmsg='插入评论出错')

    return jsonify(error=RET.OK,errmsg='OK',data=comment.to_dict())


@news_blue.route("/followed_user", methods = ["POST"])
@request_login
def followed_use():
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg='用户未登录')
    user_id = request.json.get('user_id')
    action = request.json.get('action')

    print(user_id, action)

    if not all([user_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不完整')

    try:
        news_user = User.query.filter_by(id = user_id).first()
    except Exception as e:
        current_app.logger.error(e)

    data = {}

    if news_user not in user.followed:
        print("添加粉丝")
        user.followed.append(news_user)
        db.session.commit()
        data = {
            "error":"0",
            "errmsg":"关注成功"
        }
    else:
        print("取消粉丝")
        user.followed.remove(news_user)
        db.session.commit()
        data = {
            "error": "0",
            "errmsg": "取消关注"
        }

    return jsonify(data)


# 关注用户


# 点赞

# 加载项目浏览器小图标
@news_blue.route("/favicon.ico")
#静态路径访问的默认实现
# 把静态文件发给浏览器
def favicon():
    print("加载小图标")
    return current_app.send_static_file("news/favicon.ico")

