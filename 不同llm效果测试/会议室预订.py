import hashlib
import json
import time
import random
import requests
import re

room_id_dict = {
  "A305-网安专用": "961a6119-87f9-4dba-86ca-611deae2126b",
  "A311-软件专用": "ec5a6b88-7c48-4d1b-a4f4-1ddd975884cf",
  "B202-计算机专用": "8bf9bbfb-3753-458c-aba3-6d95ea4f7089",
  "B114-人工智能专业": "867381c3-ee40-40a2-b7d9-705f5233efc4",
  "B204": "dd0610e5-c968-4518-9909-9ec7c7aae5cf",
  "B205贵宾室": "017eba75-4941-4bdd-affb-b29826f59d9c",
  "B206 学部展厅": "2098ff5f-fae5-406d-95bc-71879c07e9f0",
  "B215": "cad5961d-38bb-48e9-83b8-2401d7393e1d",
  "B217": "7b347d37-9e95-484c-9d03-73c7d0a9089a",
  "B218智能微缩仿真模型室": "62f8ba8d-2edd-4feb-b3c4-ce16947dba5b",
  "B219": "d0589a1f-43bf-4c7c-815e-cb67a4646b2a",
  "B221": "211a08b6-6392-4e43-9fa6-a42f5531b571",
  "B222": "b69c5ee2-f7ca-4c85-aaf0-f9f510531400",
  "B223": "af4cee47-c086-4caf-805d-2c809e51f768",
  "B224": "8cc97155-bfb0-4291-bc57-76d07e023694"
}

def check_login(username, password, session=None, verifycode="", autologin=0, verifymark=0, language="zh-CN", checkMode=""):
    """
    登录检查函数
    
    Args:
        username: 用户名
        password: 密码（明文，函数内部会进行MD5加密）
        session: requests.Session对象，可选
        verifycode: 验证码，默认为空
        autologin: 自动登录标志，默认为0
        verifymark: 验证标记，默认为0
        language: 语言，默认为zh-CN
        checkMode: 检查模式，默认为空
    
    Returns:
        tuple: (session, response) - session对象和响应对象
    """
    # 如果没有提供session，创建一个新的
    s = session or requests.Session()
    
    # 生成时间戳（毫秒）
    timestamp = int(time.time() * 1000)
    
    # 生成vctag（与文件中的逻辑一致）
    vctag_timestamp = int(time.time() * 10000)  # 15位时间戳
    random_num = random.random()  # 0-1的随机数
    random_num = str(random_num).split(".")[1]
    vctag = f"{vctag_timestamp}.{random_num}"
    
    # 对密码进行MD5加密
    password_md5 = hashlib.md5(password.encode()).hexdigest()


    # 构建URL（包含查询参数）
    url = f"http://211.81.55.151:10086/Login/CheckLogin?t={timestamp}&VOrigin=Web&VAccountSet="
    
    # 请求头
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'http://211.81.55.151:10087',
        'Pragma': 'no-cache',
        'Referer': 'http://211.81.55.151:10087/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
    }
    
    # 请求数据
    data = {
        'username': username,
        'password': password_md5,
        'verifycode': verifycode,
        'autologin': autologin,
        'verifymark': verifymark,
        'language': language,
        'vctag': vctag,
        'checkMode': checkMode
    }
    
    # 发送POST请求（verify=False对应curl的--insecure）
    response = s.post(url, headers=headers, data=data, verify=False, timeout=10)
    
    return s, response

def access_admin_ums(session):
    """
    使用登录后的session访问AdminUMS页面
    
    Args:
        session: requests.Session对象（已登录的session）
    
    Returns:
        requests.Response: 响应对象
    """
    url = "http://211.81.55.151:10087/Home/AdminUMS"
    
    # 请求头
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Pragma': 'no-cache',
        'Referer': 'http://211.81.55.151:10087/',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
    }
    
    # 使用session发送GET请求（verify=False对应curl的--insecure）
    response = session.get(url, headers=headers, verify=False, timeout=10)
    
    return response

def access_person_center(session):
    """
    使用登录后的session访问PersonCenter/Index页面
    
    Args:
        session: requests.Session对象（已登录的session）
    
    Returns:
        requests.Response: 响应对象
    """
    url = "http://211.81.55.151:10087/PersonCenter/Index"
    
    # 请求头（从curl命令中提取）
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Pragma': 'no-cache',
        'Referer': 'http://211.81.55.151:10087/Home/AdminUMS',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36'
    }
    
    # 使用session发送GET请求（verify=False对应curl的--insecure）
    # session会自动携带登录后的cookies
    response = session.get(url, headers=headers, verify=False, timeout=10)
    
    return response

def access_meeting_form(session, st, et, meet_room, p_flag=1):
    """
    使用登录后的session访问会议表单页面并提取__RequestVerificationToken
    
    Args:
        session: requests.Session对象（已登录的session）
        st: 开始时间，格式：2025-11-09 14:00
        et: 结束时间，格式：2025-11-09 14:30
        meet_room: 会议室ID，格式：dd0610e5-c968-4518-9909-9ec7c7aae5cf
        p_flag: 标志，默认为1
    
    Returns:
        tuple: (response, token) - 响应对象和__RequestVerificationToken值
    """
    from urllib.parse import quote
    
    # 构建URL（需要对参数进行URL编码）
    url = f"http://211.81.55.151:10087/OA/Meeting/page/Form?st={quote(st)}&et={quote(et)}&meetRoom={meet_room}&pFlag={p_flag}"
    
    # 请求头（从curl命令中提取）
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Pragma': 'no-cache',
        'Referer': 'http://211.81.55.151:10087/Home/AdminUMS',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
    }
    
    # 使用session发送GET请求（verify=False对应curl的--insecure）
    # session会自动携带登录后的cookies
    response = session.get(url, headers=headers, verify=False, timeout=10)
    
    # 从响应内容中提取__RequestVerificationToken
    token = extract_request_verification_token(response.text)
    
    return response, token

def extract_request_verification_token(html_content):
    """
    从HTML内容中提取__RequestVerificationToken的值
    
    Args:
        html_content: HTML内容字符串
    
    Returns:
        str: __RequestVerificationToken的值，如果未找到则返回None
    """
    # 方法1: 使用正则表达式匹配input标签
    pattern1 = r'<input[^>]*name=["\']__RequestVerificationToken["\'][^>]*value=["\']([^"\']+)["\']'
    match1 = re.search(pattern1, html_content, re.IGNORECASE)
    if match1:
        return match1.group(1)
    
    # 方法2: 匹配隐藏的input字段（更宽松的匹配）
    pattern2 = r'__RequestVerificationToken["\']?\s*[=:]\s*["\']?([A-Za-z0-9_\-]+)'
    match2 = re.search(pattern2, html_content, re.IGNORECASE)
    if match2:
        return match2.group(1)
    
    # 方法3: 在script标签中查找（有些网站会在JS中设置）
    pattern3 = r'__RequestVerificationToken["\']?\s*[:=]\s*["\']([^"\']+)["\']'
    match3 = re.search(pattern3, html_content, re.IGNORECASE)
    if match3:
        return match3.group(1)
    
    return None

def get_request_verification_token_by_key(session, key_value, copy_flag=0, p_flag=""):
    """
    根据keyValue参数获取表单页面的__RequestVerificationToken，获取修改页面的__RequestVerificationToken
    
    Args:
        session: requests.Session对象（已登录的session）
        key_value: 关键字值，例如：072f2306-8914-4ebb-90f7-0efcfb335255
        copy_flag: 复制标志，默认为0
        p_flag: 标志，默认为空字符串
    
    Returns:
        str: __RequestVerificationToken的值，如果未找到则返回None
    """
    from urllib.parse import quote
    
    # 构建URL（根据curl命令）
    url = f"http://211.81.55.151:10087/OA/Meeting/page/Form?keyValue={quote(key_value)}&copyFlag={copy_flag}&pFlag={p_flag}"
    
    # 请求头（从curl命令中提取）
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Pragma': 'no-cache',
        'Referer': 'http://211.81.55.151:10087/Home/AdminUMS',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
    }
    
    # 使用session发送GET请求（verify=False对应curl的--insecure）
    # session会自动携带登录后的cookies
    response = session.get(url, headers=headers, verify=False, timeout=10)
    
    # 从响应内容中提取__RequestVerificationToken
    token = extract_request_verification_token(response.text)
    
    return token

def get_free_room(session, st, et, v_token, v_account_set, key_value=""):
    """
    获取空闲会议室列表
    
    Args:
        session: requests.Session对象（已登录的session）
        st: 开始时间，格式：2025-11-09 14:00
        et: 结束时间，格式：2025-11-09 14:30
        v_token: VToken值（从cookies中的ums_token获取）
        v_account_set: VAccountSet值（从cookies中的VAccountSet获取）
        key_value: 关键字值，默认为空字符串
    
    Returns:
        requests.Response: 响应对象
    """
    from urllib.parse import quote
    
    # 生成时间戳（毫秒）
    timestamp1 = int(time.time() * 1000)  # 用于 _v 参数
    # 第二个时间戳比第一个小400毫秒
    timestamp2 = int(time.time() * 1000) - 400  # 用于 _ 参数
    
    # 对时间进行URL编码（空格变成+，冒号变成%3A）
    st_encoded = quote(st, safe='').replace('%20', '+')
    et_encoded = quote(et, safe='').replace('%20', '+')
    
    # 构建URL（包含查询参数）
    url = (f"http://211.81.55.151:10086/API/OA/Meeting/Connector/MeetingEvent/GetFreeRoom"
           f"?VOrigin=Web"
           f"&VToken={v_token}"
           f"&VAccountSet={v_account_set}"
           f"&_v={timestamp1}"
           f"&st={st_encoded}"
           f"&et={et_encoded}"
           f"&keyValue={key_value}"
           f"&_={timestamp2}")
    
    # 请求头（从curl命令中提取）
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Origin': 'http://211.81.55.151:10087',
        'Pragma': 'no-cache',
        'Referer': 'http://211.81.55.151:10087/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
    }
    
    # 使用session发送GET请求（verify=False对应curl的--insecure）
    # session会自动携带登录后的cookies
    response = session.get(url, headers=headers, verify=False, timeout=10)
    
    return response

def save_meeting_form(session, v_token, v_account_set, meeting_start_time, meeting_end_time, 
                      meeting_title, meeting_compere_name, compere_mobile, user_id, user_name, 
                      user_account, create_user_mobile, room_id, request_verification_token,
                      copy_flag="", origin_id="", key_value="", meeting_compere="", room_other="", 
                      meeting_recurrence=0):
    """
    保存会议表单
    
    Args:
        session: requests.Session对象（已登录的session）
        v_token: VToken值
        v_account_set: VAccountSet值
        meeting_start_time: 会议开始时间，格式：2025-11-09 14:00
        meeting_end_time: 会议结束时间，格式：2025-11-09 14:30
        meeting_title: 会议标题
        meeting_compere_name: 主持人姓名
        compere_mobile: 主持人手机号
        user_id: 用户ID
        user_name: 用户姓名
        user_account: 用户账号
        create_user_mobile: 创建用户手机号
        room_id: 会议室ID
        request_verification_token: __RequestVerificationToken值
        copy_flag: 复制标志，默认为空
        origin_id: 原始ID，默认为空
        key_value: 关键字值，默认为空
        meeting_compere: 会议主持人，默认为空
        room_other: 其他会议室，默认为空
        meeting_recurrence: 会议重复，默认为0
    
    Returns:
        requests.Response: 响应对象
    """
    from urllib.parse import quote
    
    # 构建URL（包含查询参数）
    url = (f"http://211.81.55.151:10086/API/OA/Meeting/xbypass/MeetingEvent/SaveForm"
           f"?VOrigin=Web"
           f"&VToken={v_token}"
           f"&VAccountSet={v_account_set}")
    
    # 对时间进行URL编码（空格变成+，冒号变成%3A）
    # 标准格式：2025-11-09 14:00 -> 2025-11-09+14%3A00
    st_encoded = meeting_start_time.replace(' ', '+').replace(':', '%3A')
    et_encoded = meeting_end_time.replace(' ', '+').replace(':', '%3A')
    
    # 手动构建URL编码的表单数据字符串，确保格式正确
    # 时间格式已经处理好（空格->+，冒号->%3A），直接使用
    # 其他字段需要URL编码（中文字段会被正确编码）
    
    def encode_value(value):
        """对值进行URL编码"""
        if value is None:
            return ''
        return quote(str(value), safe='')
    
    # 构建表单数据列表
    form_parts = []
    form_parts.append(f"MeetingStartTime={st_encoded}")  # 时间格式已处理好
    form_parts.append(f"MeetingEndTime={et_encoded}")  # 时间格式已处理好
    form_parts.append(f"CopyFlag={encode_value(copy_flag)}")
    form_parts.append(f"originId={encode_value(origin_id)}")
    form_parts.append(f"keyValue={encode_value(key_value)}")
    form_parts.append(f"MeetingTitle={encode_value(meeting_title)}")
    form_parts.append(f"MeetingCompere={encode_value(meeting_compere)}")
    form_parts.append(f"MeetingCompereName={encode_value(meeting_compere_name)}")
    form_parts.append(f"CompereMobile={encode_value(compere_mobile)}")
    form_parts.append(f"UserId={encode_value(user_id)}")
    form_parts.append(f"UserName={encode_value(user_name)}")
    form_parts.append(f"UserAccount={encode_value(user_account)}")
    form_parts.append(f"CreateUserMobile={encode_value(create_user_mobile)}")
    form_parts.append(f"RoomId={encode_value(room_id)}")
    form_parts.append(f"RoomOther={encode_value(room_other)}")
    form_parts.append(f"MeetingRecurrence={encode_value(meeting_recurrence)}")
    form_parts.append(f"__RequestVerificationToken={encode_value(request_verification_token)}")
    
    # 组合成完整的表单数据字符串
    data_str = '&'.join(form_parts)

    # 请求头（从curl命令中提取）
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'http://211.81.55.151:10087',
        'Pragma': 'no-cache',
        'Referer': 'http://211.81.55.151:10087/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
    }
    
    # 使用session发送POST请求（verify=False对应curl的--insecure）
    # session会自动携带登录后的cookies
    # 注意：使用data_str字符串而不是字典，避免requests再次编码
    response = session.post(url, headers=headers, data=data_str, verify=False, timeout=10)
    
    return response

def update_meeting_form(session, v_token, v_account_set, key_value, meeting_start_time, meeting_end_time, 
                       meeting_title, meeting_compere_name, compere_mobile, user_id, user_name, 
                       user_account, create_user_mobile, room_id, copy_flag="", meeting_compere="", 
                       room_other="&nbsp;", meeting_recurrence=0):
    """
    修改会议表单（使用keyValue获取__RequestVerificationToken）
    
    Args:
        session: requests.Session对象（已登录的session）
        v_token: VToken值
        v_account_set: VAccountSet值
        key_value: 关键字值（会议ID），用于获取token和标识要修改的会议
        meeting_start_time: 会议开始时间，格式：2025-11-09 14:00
        meeting_end_time: 会议结束时间，格式：2025-11-09 14:30
        meeting_title: 会议标题
        meeting_compere_name: 主持人姓名
        compere_mobile: 主持人手机号
        user_id: 用户ID
        user_name: 用户姓名
        user_account: 用户账号
        create_user_mobile: 创建用户手机号
        room_id: 会议室ID
        copy_flag: 复制标志，默认为空
        meeting_compere: 会议主持人，默认为空
        room_other: 其他会议室，默认为"&nbsp;"
        meeting_recurrence: 会议重复，默认为0
    
    Returns:
        tuple: (success: bool, response: Response) - 是否成功、响应对象
    """
    # 使用keyValue获取__RequestVerificationToken
    # copy_flag为空字符串时传0，否则传原值
    copy_flag_for_token = 0 if copy_flag == "" else copy_flag
    request_verification_token = get_request_verification_token_by_key(
        session=session,
        key_value=key_value,
        copy_flag=copy_flag_for_token,
        p_flag=""
    )
    
    if not request_verification_token:
        print(f"无法获取验证token，修改失败")
        return False, None
    
    # 调用save_meeting_form函数，传入origin_id和key_value用于修改
    response = save_meeting_form(
        session=session,
        v_token=v_token,
        v_account_set=v_account_set,
        meeting_start_time=meeting_start_time,
        meeting_end_time=meeting_end_time,
        meeting_title=meeting_title,
        meeting_compere_name=meeting_compere_name,
        compere_mobile=compere_mobile,
        user_id=user_id,
        user_name=user_name,
        user_account=user_account,
        create_user_mobile=create_user_mobile,
        room_id=room_id,
        request_verification_token=request_verification_token,
        copy_flag=copy_flag,
        origin_id=key_value,  # 使用key_value作为origin_id
        key_value=key_value,   # 使用key_value作为key_value
        meeting_compere=meeting_compere,
        room_other=room_other,
        meeting_recurrence=meeting_recurrence
    )
    
    # 检查是否成功
    try:
        response_json = json.loads(response.text)
        if response.status_code == 200:
            errorcode = response_json.get("errorcode", -1)
            if errorcode == 0:
                return True, response
            else:
                message = response_json.get("message", "未知错误")
                print(f"修改失败: {message}")
                return False, response
        else:
            print(f"修改失败: HTTP状态码 {response.status_code}")
            return False, response
    except:
        if response.status_code == 200:
            print(f"修改响应: {response.text[:200]}")
            return True, response
        else:
            print(f"修改失败: HTTP状态码 {response.status_code}")
            return False, response

def try_reserve_meeting(session, st, et, room_id, v_token, v_account_set, 
                       meeting_title, meeting_compere_name, compere_mobile,
                       user_id, user_name, user_account, create_user_mobile):
    """
    尝试预订会议室
    
    Args:
        session: 已登录的session
        st: 开始时间
        et: 结束时间
        room_id: 会议室ID
        v_token: VToken
        v_account_set: VAccountSet
        meeting_title: 会议标题
        meeting_compere_name: 主持人姓名
        compere_mobile: 主持人手机号
        user_id: 用户ID
        user_name: 用户姓名
        user_account: 用户账号
        create_user_mobile: 创建用户手机号
    
    Returns:
        tuple: (success: bool, response: Response, meeting_id: str) - 是否成功、响应对象、会议ID
    """
    # 访问会议表单页面获取验证token
    meeting_form_response, __RequestVerificationToken = access_meeting_form(session, st, et, room_id)
    
    if not __RequestVerificationToken:
        print(f"  无法获取验证token，跳过该会议室")
        return False, meeting_form_response, None
    
    # 尝试保存会议表单
    save_response = save_meeting_form(
        session=session,
        v_token=v_token,
        v_account_set=v_account_set,
        meeting_start_time=st,
        meeting_end_time=et,
        meeting_title=meeting_title,
        meeting_compere_name=meeting_compere_name,
        compere_mobile=compere_mobile,
        user_id=user_id,
        user_name=user_name,
        user_account=user_account,
        create_user_mobile=create_user_mobile,
        room_id=room_id,
        request_verification_token=__RequestVerificationToken
    )
    
    # 检查是否成功（通常成功时返回200状态码，且响应中包含成功信息）
    try:
        save_response_json = json.loads(save_response.text)
        # 根据实际API响应格式判断是否成功
        # 这里假设errorcode为0表示成功，或者有特定的成功标识
        if save_response.status_code == 200:
            # {"type":1,"errorcode":0,"message":"操作成功。","format":null,"args":null,"resultdata":{"MeetingId":"072f2306-8914-4ebb-90f7-0efcfb335255","MeetingCode":"Ew2fdSVx"}}
            errorcode = save_response_json.get("errorcode", -1)
            if errorcode == 0:
                # 提取MeetingId
                meeting_id = save_response_json.get("resultdata").get("MeetingId")
                return True, save_response, meeting_id
            else:
                message = save_response_json.get("message", "未知错误")
                print(f"  预订失败: {message}")
                return False, save_response, __RequestVerificationToken
        else:
            print(f"  预订失败: HTTP状态码 {save_response.status_code}")
            return False, save_response, __RequestVerificationToken
    except:
        # 如果不是JSON格式，检查状态码
        if save_response.status_code == 200:
            print(f"  预订响应: {save_response.text[:200]}")
            return True, save_response, __RequestVerificationToken
        else:
            print(f"  预订失败: HTTP状态码 {save_response.status_code}")
            return False, save_response, __RequestVerificationToken

# 示例用法
if __name__ == "__main__":


    # # 自填会议信息
    # meeting_title = "测试" # 会议标题
    # st = "2025-11-09 15:00" # 开始时间格式：2025-11-09 15:00
    # et = "2025-11-09 15:30" # 结束时间格式：2025-11-09 15:30
    # room_size = "小会议室" # 大会议室/小会议室
    # # 大会议室优先级：B217 → B224 → B215 → B204（若都没有参考下面优先级）
    # # 小会议室优先级：B221 → B222 → B223 → B219（若都没有参考上面优先级）
    # big_room_list = ["B217", "B224", "B215", "B204"]
    # small_room_list = ["B221", "B222", "B223", "B219"]
    
    # # 默认数据（无需修改）
    # username = "216178"
    # password = "XXXX"
    # # 会议信息
    # meeting_compere_name = "胡一涛"
    # compere_mobile = "16600641268"
    # user_id = "F7FBDA33-CF1D-4DAE-8361-360395178B16"  
    # user_name = "胡一涛"  
    # user_account = username
    # create_user_mobile = "16600641268" 
    
    # # 登录并获取session
    # session, login_response = check_login(username, password)
    # login_response_json = json.loads(login_response.text)
    # # {"type":1,"errorcode":0,"message":"登录成功","format":null,"args":null,"resultdata":{"account":"216178","token":"6ABF03D4F7B04EDE0C3E5DF58B57395D7C978C0F057076C3A50338FCDA149B8BD924BC9EDCE57048","accountset":"e6472d26-2e88-8674-76ed-3a0d750103a1","language":"zh-CN"}}
    # VToken = login_response_json.get("resultdata").get("token")
    # VAccountSet = login_response_json.get("resultdata").get("accountset")
    
    # # 使用登录后的session获取空闲会议室列表
    # free_room_response = get_free_room(session, st, et, VToken, VAccountSet)
    
    # # 解析空闲会议室列表，构建room_id_dict
    # try:
    #     free_rooms = json.loads(free_room_response.text)
    #     room_id_dict = {}
    #     for room in free_rooms:
    #         room_id_dict[room["RoomName"]] = room["MeetingRoomId"]
    #     print(f"\n可用会议室映射: {room_id_dict}")
    # except:
    #     print("无法解析空闲会议室列表")
    #     room_id_dict = {}
    
    # # 根据room_size确定首选列表和备选列表
    # if room_size == "大会议室":
    #     primary_list = big_room_list
    #     fallback_list = small_room_list
    # else:  # 小会议室
    #     primary_list = small_room_list
    #     fallback_list = big_room_list
    
    # # 尝试预订会议室
    # success = False
    # reserved_room = None
    
    # # 首先尝试首选列表中的会议室
    # print(f"\n开始尝试预订{room_size}...")
    # for room_name in primary_list:
    #     if room_name not in room_id_dict:
    #         print(f"  会议室 {room_name} 不在可用列表中，跳过")
    #         continue
        
    #     room_id = room_id_dict[room_name]
    #     print(f"\n尝试预订会议室: {room_name} (ID: {room_id})")
    #     success, response, meeting_id = try_reserve_meeting(
    #         session=session,
    #         st=st,
    #         et=et,
    #         room_id=room_id,
    #         v_token=VToken,
    #         v_account_set=VAccountSet,
    #         meeting_title=meeting_title,
    #         meeting_compere_name=meeting_compere_name,
    #         compere_mobile=compere_mobile,
    #         user_id=user_id,
    #         user_name=user_name,
    #         user_account=user_account,
    #         create_user_mobile=create_user_mobile
    #     )
        
    #     if success:
    #         reserved_room = room_name
    #         print(f"\n✓ 成功预订会议室: {room_name}")
    #         print(f"响应: {response.text}")
    #         break
    
    # # 如果首选列表都失败，尝试备选列表
    # if not success:
    #     print(f"\n{room_size}列表中的会议室都预订失败，尝试备选列表...")
    #     for room_name in fallback_list:
    #         if room_name not in room_id_dict:
    #             print(f"  会议室 {room_name} 不在可用列表中，跳过")
    #             continue
            
    #         room_id = room_id_dict[room_name]
    #         print(f"\n尝试预订会议室: {room_name} (ID: {room_id})")
    #         success, response, meeting_id = try_reserve_meeting(
    #             session=session,
    #             st=st,
    #             et=et,
    #             room_id=room_id,
    #             v_token=VToken,
    #             v_account_set=VAccountSet,
    #             meeting_title=meeting_title,
    #             meeting_compere_name=meeting_compere_name,
    #             compere_mobile=compere_mobile,
    #             user_id=user_id,
    #             user_name=user_name,
    #             user_account=user_account,
    #             create_user_mobile=create_user_mobile
    #         )
            
    #         if success:
    #             reserved_room = room_name
    #             print(f"\n✓ 成功预订会议室: {room_name}")
    #             print(f"响应: {response.text}")
    #             break
    
    # if not success:
    #     print(f"\n✗ 所有会议室预订都失败了")
    # else:
    #     print(f"\n最终预订结果: {reserved_room}")

    #### 修改会议时间 ####

    username = "216178"
    password = "XXXX"
    session, login_response = check_login(username, password)
    print(login_response.text)
    # login_response_json = json.loads(login_response.text)
    # VToken = login_response_json.get("resultdata").get("token")
    # VAccountSet = login_response_json.get("resultdata").get("accountset")

    # success, response = update_meeting_form(
    #     session=session,
    #     v_token=VToken,
    #     v_account_set=VAccountSet,
    #     key_value="072f2306-8914-4ebb-90f7-0efcfb335255",  # 要修改的会议ID
    #     meeting_start_time="2025-11-11 08:00",
    #     meeting_end_time="2025-11-11 09:00",
    #     meeting_title="测试",
    #     meeting_compere_name="胡一涛",
    #     compere_mobile="16600641268",
    #     user_id="F7FBDA33-CF1D-4DAE-8361-360395178B16",
    #     user_name="胡一涛",
    #     user_account="216178",
    #     create_user_mobile="16600641268",
    #     room_id="7b347d37-9e95-484c-9d03-73c7d0a9089a"
    # )

    # if success:
    #     print("修改成功！")
    # else:
    #     print("修改失败")