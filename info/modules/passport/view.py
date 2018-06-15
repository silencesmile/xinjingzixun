import random

from flask import current_app
from flask import make_response
from flask import request, jsonify
from flask import session

from info.libs.yuntongxun.sms import CCP
from info.models import User
from info.utils.response_code import RET

from . import passport_blu
from flask import render_template
from info.utils.captcha.captcha import captcha
from info import redis, db
from info import constants
import re, hashlib

@passport_blu.route("/passport")
def passport():
    """
      生成图片验证码
      1、获取参数，前端生成图片验证码的后缀名，uuid
      request.args.get()
      2、校验参数是否存在；
      3、调用扩展包，生成图片验证码，name,text,image
      4、在redis数据库中保存图片验证码的内容；
      5、使用响应对象,来返回图片，修改默认响应的数据类型
      response = make_response(image)
      response.headers['Content-Type'] = 'image/jpg'
      6、返回结果
      return response
      :return:
      """

    # 获取前台传来的UUID image_code_uuid
    uuid = request.args.get("image_code_uuid")

    # 判断是否获取成功
    if not uuid:
        return jsonify(errno = RET.PARAMERR, errmsg = "获取UUID失败")

    # 生成验证码
    name, text, codeImage =  captcha.generate_captcha()

    # 拼接存储到redis使用的key
    redis_key = "image" + uuid
    try:
        redis.setex(redis_key, constants.IMAGE_CODE_REDIS_EXPIRES, text)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error= RET.DATAERR, errmsg = "存储到redis失败")
    else:
        response = make_response(codeImage)
        response.headers["Content-type"] = "application/jpg"

        return response

# 发送验证码

@passport_blu.route("/sendSMSCode", methods=["POST"])
def sendSMSCode():
    """
        发送短信
        1、获取参数，mobile,image_code,image_code_id
        2、判断参数的完整性
        3、验证手机号格式，正则
        4、校验图片验证码，从redis读取真实的图片验证码
        real_image_code = redis_store.get(key)
        5、判断获取结果是否存在，如果不存在，表示已过期
        6、如果图片验证码存在，需要删除图片验证码，本质是任意一个图片验证码，只能读取一次；
        7、比较图片验证码内容是否一致；
        8、查询mysql数据库，确认手机号是否已经注册；
        9、生成短信随机数；六位
        10、把短信随机数保存到redis数据库中，设置有效期
        11、调用云通讯扩展，来发送短信，保存发送结果
        12、判断发送结果是否成功。
        :return:
        """
    mobile = request.json.get("mobile")
    userCode = request.json.get("userCode")
    uuid = request.json.get("uuid")

    if not all([mobile, userCode, uuid]):
        return jsonify(error= RET.DATAERR, errmsg = "获取用户输入的验证码失败")

    # # 手机号码长度验证，
    # if len(mobile) != 11:
    #     return jsonify(error=RET.DATAERR, errmsg="手机有误")

    # 验证手机号，re.match()只匹配符合相关，并没有长度匹配校验
    # 例如：这个匹配如果写了大于11位，他会匹配符合11的内容
    result = re.match(r"1[3456789]\d{9}$", mobile)
    if not result:
        return jsonify(error=RET.PARAMERR, errmsg="手机号不规范")

    # 获取真是验证码
    redis_key = "image" + uuid
    try:
        real_code =  redis.get(redis_key)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg="获取用户输入的验证码失败")

    if not real_code:
        return jsonify(error=RET.DATAERR, errmsg="获取redis的图片验证码失败")

    try:
        # 删除验证码
        redis.delete(redis_key)
    except Exception as e:
        current_app.logger.error(e)

    if real_code.lower() != userCode.lower():
        return jsonify(error=RET.DATAERR, errmsg="验证码输入有误")

    # 验证用户是否已注册
    try:
        result2 = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg="查询mysql数据库失败")
    else:
        if result2 is not None:
            return jsonify(error=RET.DATAEXIST, errmsg="用户已注册")

    # 发送验证码
    # 构造六位数的短信随机数
    sms_code = '%06d' % random.randint(0, 999999)

    try:
        redis.setex("Mobile" + mobile, constants.IMAGE_CODE_REDIS_EXPIRES, sms_code)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DATAERR, errmsg="存入短信验证码失败")

    try:
        ccp = CCP()
        # 注意： 测试的短信模板编号为1
        result3 = ccp.send_template_sms(mobile, [sms_code, constants.IMAGE_CODE_REDIS_EXPIRES /60], 1)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.THIRDERR, errmsg="第三方错误")

    # 将验证码存入redis
    if result3 == 0:
        # 发送成功
        return jsonify(error=RET.OK, errmsg='发送成功')
    else:
        # 发送失败
        return jsonify(error=RET.THIRDERR, errmsg='发送失败')

# 验证信息
'''
注册：
先进行短信验证，如果验证失败，则注册失败
如果验证成功，则注册成功，将手机号，密码(加密后)的数据保存到mysql，并将手机号，密码注册到redis中

   """
    用户注册
    1、获取参数，mobile/sms_code/password
    2、校验参数的完整性
    3、检查手机号的格式
    4、短信验证码进行比较
    5、尝试从redis数据库中获取真实的短信验证码
    6、判断获取结果是否有数据
    7、比较短信验证码是否正确
    8、如果短信验证码正确，删除redis中的短信验证码
    9、验证手机号是否注册
    10、构造模型类对象，准备存储用户信息
    user = User()
    user.mobile = mobile
    user.nick_name = mobile
    11、需要对密码进行加密存储，
    user.password = password
    12、保存数据到mysql数据库中
    13、把用户信息缓存到redis数据库中
    session['user_id'] = user.id
    14、返回结果
    :return:
    """
'''
@passport_blu.route("/checkSMSCode", methods=["POST"])
def checkSMSCode():
    mobile = request.json.get("mobile")
    smscode = request.json.get("smscode")
    password = request.json.get("password")

    if not all([mobile, smscode, password]):
        return jsonify(error=RET.DATAERR, errmsg="获取用户注册信息失败")

    # 验证手机号
    result = re.match(r"1[3456789]\d{9}$", mobile)
    if not result:
        return jsonify(error=RET.DATAERR, errmsg="用户手机号有误")

    # 获取redis的验证码
    '''
    漏洞：先用真实手机号进行收取验证码，当收到验证码时，将手机号进行更改，
    在进行注册操作，这时手机号的号码可以使任意数字(薅羊毛)
    这里通过手机号
    '''

    try:
        mobileCode = redis.get("Mobile" + mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DATAERR, errmsg="获取redis用户验证码失败")

    # 比较验证码
    if str(mobileCode) != smscode:
        print("验证码错了", smscode, mobileCode)
        return jsonify(error=RET.DATAERR, errmsg="验证码错误")

    # 验证码对了， 删除内存的验证码
        # 如果短信验证码输入正确，删除redis中的短信验证码
    try:
        redis.delete('Mobile' + mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg="验证码错误")

    # 验证数据库，查看是否已注册
    us3 = User.query.filter_by(mobile=mobile).first()
    if us3:
        return jsonify(error=RET.DBERR, errmsg="已注册")

    # 注册成功 存入数据库
    try:
        # 给密码加密处理
        us4 = User()
        us4.nick_name = mobile
        us4.mobile = mobile
        us4.password = password
        # 读取存储的密码hash值
        print(us4.id, us4.password_hash, password)

        db.session.add(us4)
        db.session.commit()

        print(us4.id)
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(error=RET.DATAERR, errmsg="注册失败")
    else:
        # redis.set("user" + mobile, us4.password_hash)
        # 使用session缓存用户信息到redis数据库中
        session['user_id'] = us4.id
        session['mobile'] = mobile
        session['nick_name'] = mobile
        return jsonify(error=RET.OK, errmsg="注册成功")

# 登录功能
'''
先从redis中匹配，如果存在则直接校验
如果不存在，去mysql数据库查找，并保存在redis中，再做校验
'''
@passport_blu.route("/userLogin", methods=["POST"])
def userLogin():
    mobile = request.json.get("mobile")
    password = request.json.get("password")
    print(mobile, password)

    # 验证数据完整性
    if not all([mobile, password]):
        return jsonify(error=RET.DATAERR, errmsg="注册信息不完整")

    # 验证手机号
    result = re.match(r"1[3456789]\d{9}$", mobile)
    if not result:
        return jsonify(error=RET.DATAERR, errmsg="用户手机号有误")

    # 只将用户的密码存于mysql，根据手机号来查询mysql数据库，确认用户已注册
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg='查询数据失败')
    # # 判断查询结果
    # if not user:
    #     return jsonify(errno=RET.NODATA,errmsg='用户名或密码错误')
    # # 判断密码是否正确
    # if not user.check_password(password):
    #     return jsonify(errno=RET.DATAERR,errmsg='用户名或密码错误')
    # 判断用户是否注册，以及密码是否正确
    if user is None or not user.check_password(password):
        return jsonify(error=RET.DATAERR, errmsg='用户名或密码错误')
    # 缓存用户信息
    session['user_id'] = user.id
    session['mobile'] = user.mobile
    # 需要修改默认的昵称，因为用户可以登录多次，可能会在某次登录的过程中修改了昵称
    session['nick_name'] = user.nick_name
    # 返回结果
    return jsonify(error=RET.OK, errmsg='OK')



    # # 获取redis的密码校验 不存在再去数据库查找，并存储一份与redis
    # try:
    #     redisPwd = str(redis.get("user" + mobile))
    # except Exception as e:
    #     current_app.logger.error(e)
    #     return jsonify(error=RET.DATAERR, errmsg="获取redis用户密码失败")
    #
    # if not redisPwd:
    #     try:
    #         user5 = User.query.filter_by(mobile=mobile).first()
    #     except Exception as e:
    #         current_app.logger.error(e)
    #         return jsonify(error=RET.DATAERR, errmsg="获取mysql用户信息失败")
    #     else:
    #         if user5:
    #             redis.set("user" + mobile, user5.password_hash)
    #             if user5.check_password(password):
    #                 return jsonify(error=RET.OK, errmsg="登陆成功")
    #             else:
    #                 return jsonify(error=RET.DATAERR, errmsg="mysql密码错误")
    #         else:
    #             return jsonify(error=RET.DATAERR, errmsg="该用户未注册")
    #
    # else:
    #     user6 = User()
    #     user6.password_hash = redisPwd
    #     if user6.check_password(password):
    #         # 缓存用户信息
    #         session['user_id'] = user.id
    #         session['mobile'] = user.mobile
    #         # 需要修改默认的昵称，因为用户可以登录多次，可能会在某次登录的过程中修改了昵称
    #         session['nick_name'] = user.nick_name
    #
    #         return jsonify(error=RET.OK, errmsg="登陆成功")
    #     else:
    #         return jsonify(error=RET.DATAERR, errmsg="redis密码错误")


@passport_blu.route('/logout')
def logout():
    """
    用户退出
    1、退出的本质是把缓存的用户信息进行清除
    :return:
    """
    # session.clear()会把用户信息全部清空
    session.pop("user_id")
    session.pop("nick_name")
    session.pop("mobile")
    return jsonify(errno=RET.OK,errmsg='OK')




















