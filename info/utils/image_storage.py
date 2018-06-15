from qiniu import Auth, put_data

access_key = 'IIP7_OBrxfjAyDGSNHIuqtnPpE9dqW4r54xJZGmf'
secret_key = 'F0hKWkWJhBj4kGnKx5ScznaUpdq_J3ahDxGZV1Fm'

bucket_name = 'newsinfo'


def storage(data):
    try:
        q = Auth(access_key, secret_key)
        token = q.upload_token(bucket_name)
        ret, info = put_data(token, None, data)
        print(ret, info)
    except Exception as e:
        raise e;

    if info.status_code != 200:
        raise Exception("上传图片失败")
    return ret["key"]


if __name__ == '__main__':
    file = input('newsInfo/info/static/news/favicon.ico')
    with open(file, 'rb') as f:
       storage(f.read())
