#!/usr/bin/env python3
# tu_debug_improved.py
import os
import sys
import time
import json
import traceback
from datetime import datetime, timezone
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

TU_USERNAME = os.getenv("TU_USERNAME")
TU_PASSWORD = os.getenv("TU_PASSWORD")
BASE = os.getenv("TU_BASE", "https://zw.lib.tju.edu.cn").strip()
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

if not TU_USERNAME or not TU_PASSWORD:
    print("[ERROR] 请在 .env 中设置 TU_USERNAME 与 TU_PASSWORD（或导出环境变量）", file=sys.stderr)
    sys.exit(1)

session = requests.Session()
session.headers.update({
    "User-Agent": UA,
    "Accept": "application/json, text/plain, */*",
})

CANDIDATE_LOGIN_PATHS = [
    "/api/login",
    "/api/auth/login",
    "/auth/login",
    "/login",
    "/dd-api/login",
    "/dd-api/auth/login",
    "/cas/login",
    "/oauth/token",
]

def probe_paths(timeout=8):
    print("→ 探测常见路径（GET）...")
    results = {}
    for p in CANDIDATE_LOGIN_PATHS:
        url = urljoin(BASE, p)
        try:
            r = session.get(url, allow_redirects=True, timeout=timeout)
            ct = r.headers.get("Content-Type", "")
            info = {
                "status": r.status_code,
                "final_url": r.url,
                "content_type": ct,
                "snippet": r.text[:1000]
            }
            print(f"[{r.status_code}] {url}  -> final {r.url}  Content-Type:{ct}")
            results[url] = info
        except Exception as e:
            print(f"[ERR] {url} -> {e}")
            results[url] = {"status": "ERR", "error": str(e)}
    return results

def try_json_login(url, username=TU_USERNAME, password=TU_PASSWORD, timeout=10):
    payload_candidates = [
        {"username": username, "password": password},
        {"account": username, "password": password},
        {"cardNo": username, "password": password},
        {"user": username, "pass": password},
        {"username": username, "pwd": password},
    ]
    headers = {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": BASE + "/"
    }
    for payload in payload_candidates:
        try:
            r = session.post(url, json=payload, headers=headers, allow_redirects=True, timeout=timeout)
            print(f"尝试 JSON POST -> {url}  payload keys: {list(payload.keys())}  status: {r.status_code}")
            # 尝试解析 JSON（若返回 token 请记录）
            try:
                j = r.json()
                print("返回 JSON keys:", list(j.keys())[:10])
                # 如果返回包含 token 或 success，直接返回
                if r.status_code in (200,201) and (j.get("token") or j.get("access_token") or j.get("success") or j.get("code")==0):
                    print("[INFO] JSON 登录很可能成功，响应示例（不显示完整敏感字段）:")
                    # 仅打印 keys 和部分值长度
                    for k,v in j.items():
                        if k.lower() in ("token","access_token","authorization","auth"):
                            print(f" * {k}: <present, len={len(str(v))}>")
                        else:
                            print(f" * {k}: {str(v)[:80]}")
                    return r
            except Exception:
                print("非 JSON 响应，前200字符：", r.text[:200])
            # 如果返回 cookie 且含 session id，也可视为成功的候选
            if r.status_code in (200,201) and session.cookies:
                print("[INFO] POST 返回且 session.cookies 非空，可能登录成功。")
                return r
        except Exception as e:
            print("JSON POST 错误：", e)
    return None

def try_form_login(login_page_url, username=TU_USERNAME, password=TU_PASSWORD, timeout=10):
    print("GET 登录页：", login_page_url)
    try:
        r = session.get(login_page_url, timeout=timeout)
    except Exception as e:
        print("GET 登录页失败：", e)
        return None
    if r.status_code != 200:
        print("登录页非 200：", r.status_code)
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    form = soup.find("form")
    if not form:
        print("未发现 <form>，无法自动提交表单")
        return None
    action = form.get("action") or login_page_url
    post_url = urljoin(r.url, action)
    form_data = {}
    for inp in form.find_all("input"):
        name = inp.get("name")
        if not name:
            continue
        # value 可能为空
        form_data[name] = inp.get("value","")
    # 尝试匹配常见字段名覆盖或新增
    username_candidates = ("username","user","account","login","cardNo","cardNoHidden","cardno","acct")
    password_candidates = ("password","pass","passwd","pwd")
    placed_user = False
    placed_pass = False
    for k in list(form_data.keys()):
        kl = k.lower()
        if not placed_user and any(c.lower() == kl for c in username_candidates):
            form_data[k] = username
            placed_user = True
        if not placed_pass and any(c.lower() == kl for c in password_candidates):
            form_data[k] = password
            placed_pass = True
    if not placed_user:
        # 追加一个可能的字段（后端可能接受）
        form_data["username"] = username
    if not placed_pass:
        form_data["password"] = password

    print("将提交到:", post_url, "提交字段示例 keys:", list(form_data.keys())[:20])
    headers = {"Referer": login_page_url, "User-Agent": UA}
    try:
        r2 = session.post(post_url, data=form_data, headers=headers, allow_redirects=True, timeout=timeout)
        print("表单提交状态：", r2.status_code, "最终URL:", r2.url)
        try:
            print("返回 JSON keys:", list(r2.json().keys())[:10])
        except Exception:
            print("返回文本前300:", r2.text[:300])
        return r2
    except Exception as e:
        print("表单提交异常：", e)
        return None

def login_probe_flow():
    results = probe_paths()
    # 优先尝试探测到的 JSON 接口
    for url, info in results.items():
        if info.get("status") == 200:
            ct = info.get("content_type","")
            if "json" in ct or "/api/" in url:
                print("尝试 JSON 登录（探测到的 API）：", url)
                r = try_json_login(url)
                if r and r.status_code in (200,201):
                    return r
            if isinstance(info.get("snippet",""), str) and "<form" in info["snippet"].lower():
                print("发现表单页面，尝试表单登录：", url)
                r = try_form_login(url)
                if r and r.status_code in (200,302):
                    return r
    # 兜底逐个尝试 post
    for p in CANDIDATE_LOGIN_PATHS:
        url = urljoin(BASE, p)
        print("兜底尝试 JSON POST ->", url)
        r = try_json_login(url)
        if r and r.status_code in (200,201):
            return r
    print("所有自动尝试已完成，若仍失败请在浏览器 Network 里 Copy as cURL 并把请求头/请求体贴上来分析。")
    return None

# 示例：登录成功后尝试预约（使用预订接口）
def attempt_preorder(cardNo, pre_minutes=30, costPoints=0):
    preorder_url = urljoin(BASE, "/dd-api/seats/pre-order")
    # 如果登录返回 token 在 JSON 或 header，需要从那里拿 Authorization
    # 优先从 session cookies 再从 session.headers 查找 token
    auth_header = None
    # 常见 cookie 名称或 header 名
    cookie_dict = session.cookies.get_dict()
    if cookie_dict:
        print("[INFO] session cookies:", cookie_dict)
    # 如果登录时服务器返回 JSON token，可能需要你在 try_json_login 中提取并设置
    # 这里我们优先尝试直接用 session（cookie-based auth）
    payload = {
        "cardNo": cardNo,
        "costPoints": costPoints,
        "defaultPreOrderMinutes": pre_minutes,
        "preOrderMinutes": pre_minutes,
        "t": int(datetime.now(timezone.utc).timestamp() * 1000)
    }
    headers = {
        "Content-Type": "application/json",
        "Referer": BASE + "/",
        "Origin": BASE,
        "User-Agent": UA
    }
    # 如果你已经有 Authorization token，可以放到 headers["Authorization"] = "Bearer xxxx"
    print("尝试发起预约请求（不一定成功）:", preorder_url)
    try:
        r = session.post(preorder_url, json=payload, headers=headers, timeout=10)
        print("预约响应状态：", r.status_code)
        try:
            print("预约返回 JSON:", json.dumps(r.json(), ensure_ascii=False, indent=2)[:2000])
        except Exception:
            print("预约返回文本前500:", r.text[:500])
        return r
    except Exception as e:
        print("发起预约异常：", e)
        return None

if __name__ == "__main__":
    try:
        r = login_probe_flow()
        if r:
            print("[DONE] 登录尝试结束，检查 session.cookies 与响应判断是否登录成功。")
            # 如果你已知道 cardNo，可在此处调用预约尝试（演示）
            card_no_demo = os.getenv("TU_CARDNO")
            if card_no_demo:
                attempt_preorder(card_no_demo)
            else:
                print("未设置 TU_CARDNO，跳过预约示例。若要测试预约，请在 .env 设置 TU_CARDNO。")
        else:
            print("[WARN] 登录尝试未成功，请在浏览器抓包并将 curl/headers 内容发来以便进一步解析。")
    except Exception:
        print("主流程异常：")
        traceback.print_exc()
