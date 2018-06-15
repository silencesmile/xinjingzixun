import datetime, time
from datetime import datetime, timedelta

from flask import current_app
from flask import g, render_template
from flask import request, redirect, jsonify
from flask import session
from flask import url_for

from info.models import User
from info.utils.response_code import RET
from . import admin_blu
from info.utils.commons import request_login

@admin_blu.route("/index")
@request_login
def index():
    print("BBBB")
    user = g.user
    return render_template("admin/index.html",user=user.to_dict())


@admin_blu.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "GET":
        print("AAAA")

        user_id = session.get("user_id", None)
        is_admin = session.get("is_admin", False)
        if user_id and is_admin:
            return redirect(url_for("admin.index"))
        return render_template("admin/login.html")

    print("qqqq")
    user_name = request.form.get("username")
    password  = request.form.get("password")

    print(user_name, password)

    if not all([user_name, password]):
        return jsonify(error = RET.PARAMERR, errmsg = "参数不全")

    try:
        user = User.query.filter(User.mobile == user_name and User.is_admin == True).first()
    except Exception as e:
        return render_template('admin/login.html', errmsg='数据库查询错误')

    if  not user.check_password(password):
        return render_template('admin/login.html', errmsg='账号或密码错误')

    session["mobile"] = user.mobile
    session["user_id"] = user.id
    session["nick_name"] = user.nick_name
    session["is_admin"] = user.is_admin

    return redirect(url_for('admin.index'))

@admin_blu.route("/user_count")
def user_count():
    """
       用户数据统计
       1、统计总人数：不含管理员，is_admin=False
       2、统计月人数：User.create_time > mon_begin_date(每月的开始日期2018-06-01)
       3、统计日人数：User.create_time > day_begin_date(每天的开始时间2018-06-09)
       :return:
       """
    # 定义总人数
    total_count = 0
    try:
        total_count = User.query.filter(User.is_admin == False).count()
    except Exception as e:
        current_app.logger.error(e)
    # 月新增人数'2018-06-09' 2018-06-09 tm_year=2018, tm_mon=6, tm_mday=9,
    mon_count = 0
    t = time.localtime()
    # 生成月份开始日期的字符串
    mon_begin_date_str = '%d-%02d-01' % (t.tm_year, t.tm_mon)
    # 把日期字符串转成日期对象
    mon_begin_date = datetime.strptime(mon_begin_date_str, '%Y-%m-%d')
    # 查询每月新增的人数
    try:
        mon_count = User.query.filter(User.is_admin == False, User.create_time > mon_begin_date).count()
    except Exception as e:
        current_app.logger.error(e)
    # 日新增人数
    day_count = 0
    day_begin_date_str = '%d-%02d-%02d' % (t.tm_year, t.tm_mon, t.tm_mday)
    day_begin_date = datetime.strptime(day_begin_date_str, '%Y-%m-%d')
    try:
        day_count = User.query.filter(User.is_admin == False, User.create_time > day_begin_date).count()
    except Exception as e:
        current_app.logger.error(e)
    # 定义活跃的人数和活跃的时间
    active_time = []
    active_count = []
    # 默认按照31天往前推
    active_begin_date_str = '%d-%02d-%02d' % (t.tm_year, t.tm_mon, t.tm_mday)
    active_begin_date = datetime.strptime(active_begin_date_str, '%Y-%m-%d')
    for x in range(0, 31):
        # 今天的0时0分
        # 6月9日 - 6月9日 = 6月9日
        begin_date = active_begin_date - timedelta(days=x)
        # 今天的24时,明天的0时0分
        end_date = active_begin_date - timedelta(days=(x - 1))
        # 把日期对象转成字符串
        begin_date_str = datetime.strftime(begin_date, '%Y-%m-%d')
        count = 0
        try:
            count = User.query.filter(User.is_admin == False, User.last_login >= begin_date,
                                      User.last_login < end_date).count()
        except Exception as e:
            current_app.logger.error(e)
        # 添加日期和查询结果
        active_time.append(begin_date_str)
        active_count.append(count)
    # 反转列表
    active_time.reverse()
    active_count.reverse()

    data = {
        'total_count': total_count,
        'mon_count': mon_count,
        'day_count': day_count,
        'active_time': active_time,
        'active_count': active_count
    }

    return render_template('admin/user_count.html', data=data)

