from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from tempfile import NamedTemporaryFile
from typing import Optional, List
from datetime import datetime
import re
import os
import json

from travel_planner_agent import plan_trip, export_json, export_csv
from travel_planner_agent import config as tp_config
from travel_planner_agent.providers import transcribe_wav16_xfyun_ws
from travel_planner_agent.db import (
    init_db,
    create_user,
    verify_user,
    get_user_by_id,
    # we will implement password update in db module
    # function name: update_user_password
    # for Supabase: use auth.update_user; for SQLite: update hash & salt
    # import here; will add implementation in db.py
    
    create_plan,
    list_plans,
    get_plan,
    delete_plan,
)


app = FastAPI(title="AI旅行规划师")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 会话中间件，用于登录状态
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET", "change-me-please"))


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/")
def index(request: Request):
    uid = request.session.get("user_id")
    if not uid:
        # 未登录时，引导登录后进入“我的计划”页
        return RedirectResponse(url="/login?next=/plans", status_code=302)
    # 优先从会话读取邮箱，以适配 Supabase Auth
    email = request.session.get("user_email")
    user = {"id": uid, "username": email} if email else get_user_by_id(uid)
    # 高德地图 Key（优先配置文件，回退环境变量）
    amap_key = getattr(tp_config, "AMAP_WEB_KEY", None) or os.getenv("AMAP_WEB_KEY") or ""
    # 高德地图 Web JS 安全密钥（优先配置文件，回退环境变量）
    amap_js_sec_code = getattr(tp_config, "AMAP_SECURITY_JS_CODE", None) or os.getenv("AMAP_SECURITY_JS_CODE") or ""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "result": None,
            "text": "",
            "title": "",
            "destination": "",
            "start_date": "",
            "end_date": "",
            "days": None,
            "budget_cny": None,
            "adults": 1,
            "children": 0,
            "preferences": [],
            "cities_text": "",
            "extra_info": "",
            "error": None,
            "user": user,
            "travel_mode": "driving",
            "amap_key": amap_key,
            "amap_js_sec_code": amap_js_sec_code,
        },
    )


@app.post("/plan")
def plan(
    request: Request,
    title: str = Form(""),
    destination: str = Form("") ,
    start_date: str = Form("") ,
    end_date: str = Form("") ,
    days: Optional[int] = Form(None),
    budget_cny: Optional[int] = Form(None),
    adults: int = Form(1),
    children: int = Form(0),
    preferences: List[str] = Form(default=[]),
    cities_text: str = Form(""),
    extra_info: str = Form(""),
    travel_mode: str = Form("driving"),
):
    # 访问规划功能前必须登录
    redirect = _require_login(request, "/")
    if redirect:
        return redirect
    # 计算天数（若提供了日期范围）
    computed_days = days
    if not computed_days and start_date and end_date:
        try:
            d1 = datetime.fromisoformat(start_date)
            d2 = datetime.fromisoformat(end_date)
            delta = (d2 - d1).days + 1
            if delta > 0:
                computed_days = delta
        except Exception:
            computed_days = days

    # 组合自然语言文本供解析/规划
    parts = []
    if destination:
        parts.append(f"我想去{destination}")
    if start_date and end_date and computed_days:
        parts.append(f"从{start_date}到{end_date}共{computed_days}天")
    elif computed_days:
        parts.append(f"{computed_days}天")
    if budget_cny:
        parts.append(f"预算{budget_cny}元")
    if adults is not None or children is not None:
        parts.append(f"成人{adults}，儿童{children}")
    if preferences:
        parts.append("喜欢" + ",".join(preferences))
    # 城市列表（可多个）
    cities_list: List[str] = []
    if cities_text:
        for raw in re.split(r"[，,\s]+", cities_text.strip()):
            if raw:
                cities_list.append(raw)
    if cities_list:
        parts.append("城市包括" + "、".join(cities_list))
    if extra_info:
        parts.append("补充信息：" + extra_info)
    text = "，".join(parts) if parts else ""

    try:
        data = plan_trip(text)
        uid = request.session.get("user_id")
        email = request.session.get("user_email")
        user = {"id": uid, "username": email} if uid else None
        # 高德地图 Key（优先配置文件，回退环境变量）
        amap_key = getattr(tp_config, "AMAP_WEB_KEY", None) or os.getenv("AMAP_WEB_KEY") or ""
        return templates.TemplateResponse(
            "result.html",
            {
                "request": request,
                "result": data,
                "text": text,
                "title": title,
                "destination": destination,
                "start_date": start_date,
                "end_date": end_date,
                "days": computed_days,
                "budget_cny": budget_cny,
                "adults": adults,
                "children": children,
                "preferences": preferences,
                "cities_text": cities_text,
                "extra_info": extra_info,
                "error": None,
                "user": user,
                "amap_key": amap_key,
                "travel_mode": travel_mode,
                "render_for_plan": True,
                "result_json_str": json.dumps(data, ensure_ascii=False),
                "params_json_str": json.dumps(
                    {
                        "title": title,
                        "destination": destination,
                        "start_date": start_date,
                        "end_date": end_date,
                        "days": computed_days,
                        "budget_cny": budget_cny,
                        "adults": adults,
                        "children": children,
                        "preferences": preferences,
                        "cities_text": cities_text,
                        "extra_info": extra_info,
                        "travel_mode": travel_mode,
                    },
                    ensure_ascii=False,
                ),
            },
        )
    except Exception as e:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "result": None,
                "text": text,
                "title": title,
                "destination": destination,
                "start_date": start_date,
                "end_date": end_date,
                "days": computed_days,
                "budget_cny": budget_cny,
                "adults": adults,
                "children": children,
                "preferences": preferences,
                "cities_text": cities_text,
                "extra_info": extra_info,
                "error": f"无法调用LLM：{e}",
                "user": (
                    {"id": request.session.get("user_id"), "username": request.session.get("user_email")}
                    if request.session.get("user_id") else None
                ),
                "travel_mode": travel_mode,
            },
        )


@app.post("/export/json")
def export_json_route(
    destination: str = Form("") ,
    start_date: str = Form("") ,
    end_date: str = Form("") ,
    days: Optional[int] = Form(None),
    budget_cny: Optional[int] = Form(None),
    adults: int = Form(1),
    children: int = Form(0),
    preferences: List[str] = Form(default=[]),
    cities_text: str = Form(""),
    extra_info: str = Form(""),
):
    # 与/plan保持一致的文本拼接
    computed_days = days
    if not computed_days and start_date and end_date:
        try:
            d1 = datetime.fromisoformat(start_date)
            d2 = datetime.fromisoformat(end_date)
            delta = (d2 - d1).days + 1
            if delta > 0:
                computed_days = delta
        except Exception:
            computed_days = days
    parts = []
    if destination:
        parts.append(f"我想去{destination}")
    if start_date and end_date and computed_days:
        parts.append(f"从{start_date}到{end_date}共{computed_days}天")
    elif computed_days:
        parts.append(f"{computed_days}天")
    if budget_cny:
        parts.append(f"预算{budget_cny}元")
    parts.append(f"成人{adults}，儿童{children}")
    if preferences:
        parts.append("喜欢" + ",".join(preferences))
    if cities_text:
        cities_list = [c for c in re.split(r"[，,\s]+", cities_text.strip()) if c]
        if cities_list:
            parts.append("城市包括" + "、".join(cities_list))
    if extra_info:
        parts.append("补充信息：" + extra_info)
    text = "，".join(parts) if parts else ""
    try:
        data = plan_trip(text)
    except Exception as e:
        # 返回简单文本错误
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(f"无法调用LLM：{e}", status_code=400)
    with NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        export_json(data, tmp.name)
        return FileResponse(tmp.name, media_type="application/json", filename="trip_plan.json")


@app.post("/export/csv")
def export_csv_route(
    destination: str = Form("") ,
    start_date: str = Form("") ,
    end_date: str = Form("") ,
    days: Optional[int] = Form(None),
    budget_cny: Optional[int] = Form(None),
    adults: int = Form(1),
    children: int = Form(0),
    preferences: List[str] = Form(default=[]),
    cities_text: str = Form(""),
    extra_info: str = Form(""),
):
    # 与/plan保持一致的文本拼接
    computed_days = days
    if not computed_days and start_date and end_date:
        try:
            d1 = datetime.fromisoformat(start_date)
            d2 = datetime.fromisoformat(end_date)
            delta = (d2 - d1).days + 1
            if delta > 0:
                computed_days = delta
        except Exception:
            computed_days = days
    parts = []
    if destination:
        parts.append(f"我想去{destination}")
    if start_date and end_date and computed_days:
        parts.append(f"从{start_date}到{end_date}共{computed_days}天")
    elif computed_days:
        parts.append(f"{computed_days}天")
    if budget_cny:
        parts.append(f"预算{budget_cny}元")
    parts.append(f"成人{adults}，儿童{children}")
    if preferences:
        parts.append("喜欢" + ",".join(preferences))
    if cities_text:
        cities_list = [c for c in re.split(r"[，,\s]+", cities_text.strip()) if c]
        if cities_list:
            parts.append("城市包括" + "、".join(cities_list))
    if extra_info:
        parts.append("补充信息：" + extra_info)
    text = "，".join(parts) if parts else ""
    try:
        data = plan_trip(text)
    except Exception as e:
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(f"无法调用LLM：{e}", status_code=400)
    with NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        export_csv(data, tmp.name)
        return FileResponse(tmp.name, media_type="text/csv", filename="budget.csv")


@app.post("/api/asr")
async def api_asr(file: UploadFile = File(...)):
    """语音识别接口：接收 16k PCM WAV，返回 {text} 字段供前端填充。"""
    # 读取文件字节
    wav_bytes = await file.read()
    try:
        text = await transcribe_wav16_xfyun_ws(wav_bytes)
        return {"text": text}
    except Exception as e:
        # 与前端约定：返回空文本并携带错误信息，避免打断交互
        return {"text": "", "error": f"ASR失败：{e}"}


# =============== 用户注册登录 ===============
@app.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "error": None})


@app.post("/register")
def register_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    err = create_user(username, password)
    if err:
        return templates.TemplateResponse("register.html", {"request": request, "error": err})
    # 注册成功后不自动登录，跳转至登录页
    return RedirectResponse(url="/login?next=/plans", status_code=302)


@app.get("/login")
def login_page(request: Request, next: str = ""):
    return templates.TemplateResponse("login.html", {"request": request, "error": None, "next": next})


@app.post("/login")
def login_submit(request: Request, username: str = Form(...), password: str = Form(...), next: str = Form("")):
    user = verify_user(username, password)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "error": "用户名或密码错误", "next": next})
    request.session["user_id"] = user["id"]
    # 不保存邮箱或访问令牌在会话中，满足“不要保存登录我的账号”要求
    return RedirectResponse(url=(next or "/plans"), status_code=302)


@app.get("/logout")
def logout(request: Request):
    request.session.pop("user_id", None)
    request.session.pop("user_email", None)
    request.session.pop("access_token", None)
    return RedirectResponse(url="/", status_code=302)


# =============== 旅行计划管理 ===============
def _require_login(request: Request, next_path: str = "/"):
    if not request.session.get("user_id"):
        return RedirectResponse(url=f"/login?next={next_path}", status_code=302)
    return None


@app.get("/plans")
def plans_page(request: Request):
    redirect = _require_login(request, "/plans")
    if redirect:
        return redirect
    uid = request.session.get("user_id")
    email = request.session.get("user_email")
    user = {"id": uid, "username": email} if email else get_user_by_id(uid)
    plans = list_plans(uid)
    return templates.TemplateResponse("plans.html", {"request": request, "user": user, "plans": plans})


@app.post("/plans/save")
def save_plan(request: Request, title: str = Form("我的旅行计划"), data_json: str = Form(...), params_json: str = Form(None)):
    redirect = _require_login(request, "/plans")
    if redirect:
        return redirect
    uid = request.session.get("user_id")
    new_id = create_plan(uid, title, data_json, params_json)
    return RedirectResponse(url=f"/plans/{new_id}", status_code=302)


@app.get("/plans/{plan_id}")
def view_plan(request: Request, plan_id: str):
    redirect = _require_login(request, f"/plans/{plan_id}")
    if redirect:
        return redirect
    uid = request.session.get("user_id")
    email = request.session.get("user_email")
    user = {"id": uid, "username": email} if email else get_user_by_id(uid)
    p = get_plan(plan_id, uid)
    if not p:
        return templates.TemplateResponse("plans.html", {"request": request, "user": user, "plans": list_plans(uid), "error": "未找到该计划"})
    result = json.loads(p["data_json"]) if p.get("data_json") else None
    # 高德地图 Key（优先配置文件，回退环境变量）
    amap_key = getattr(tp_config, "AMAP_WEB_KEY", None) or os.getenv("AMAP_WEB_KEY") or ""
    # 高德地图 Web JS 安全密钥（securityJsCode）：用于前端 SDK 安全校验
    amap_js_sec_code = getattr(tp_config, "AMAP_SECURITY_JS_CODE", None) or os.getenv("AMAP_SECURITY_JS_CODE") or ""

    # 从保存的参数中提取出行方式
    travel_mode = "driving"
    try:
        if p.get("params_json"):
            params_obj = json.loads(p.get("params_json"))
            tm = params_obj.get("travel_mode")
            if tm:
                travel_mode = tm
    except Exception:
        pass
    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "result": result,
            "user": user,
            "saved_title": p["title"],
            "text": None,
            "result_json_str": p["data_json"],
            "params_json_str": p.get("params_json"),
            "amap_key": amap_key,
            "amap_js_sec_code": amap_js_sec_code,
            "travel_mode": travel_mode,
        },
    )


@app.post("/plans/{plan_id}/delete")
def delete_plan_route(request: Request, plan_id: str):
    redirect = _require_login(request, f"/plans/{plan_id}")
    if redirect:
        return redirect
    uid = request.session.get("user_id")
    delete_plan(plan_id, uid)
    return RedirectResponse(url="/plans", status_code=302)


# =============== 用户管理 ===============
@app.get("/account")
def account_page(request: Request):
    redirect = _require_login(request, "/account")
    if redirect:
        return redirect
    uid = request.session.get("user_id")
    email = request.session.get("user_email")
    user = {"id": uid, "username": email} if email else get_user_by_id(uid)
    return templates.TemplateResponse("account.html", {"request": request, "user": user, "message": None, "error": None})


@app.post("/account/password")
def account_change_password(request: Request, old_password: str = Form(...), new_password: str = Form(...), confirm_password: str = Form(...)):
    redirect = _require_login(request, "/account")
    if redirect:
        return redirect
    uid = request.session.get("user_id")
    email = request.session.get("user_email")
    user = {"id": uid, "username": email} if email else get_user_by_id(uid)
    if new_password != confirm_password:
        return templates.TemplateResponse("account.html", {"request": request, "user": user, "message": None, "error": "两次输入的新密码不一致"})

    # 先校验当前密码
    uname = email or (user and user.get("username"))
    if not uname:
        return templates.TemplateResponse("account.html", {"request": request, "user": user, "message": None, "error": "无法获取用户名，请重新登录后重试"})
    v = verify_user(uname, old_password)
    if not v:
        return templates.TemplateResponse("account.html", {"request": request, "user": user, "message": None, "error": "当前密码错误"})

    # 更新密码
    try:
        from travel_planner_agent.db import update_user_password
        ok = update_user_password(uid, new_password)
        if not ok:
            return templates.TemplateResponse("account.html", {"request": request, "user": user, "message": None, "error": "修改密码失败"})
    except Exception as e:
        return templates.TemplateResponse("account.html", {"request": request, "user": user, "message": None, "error": f"修改密码失败：{e}"})

    return templates.TemplateResponse("account.html", {"request": request, "user": user, "message": "密码已更新", "error": None})


@app.post("/api/plan")
def api_plan(
    destination: str = Form("") ,
    start_date: str = Form("") ,
    end_date: str = Form("") ,
    days: Optional[int] = Form(None),
    budget_cny: Optional[int] = Form(None),
    adults: int = Form(1),
    children: int = Form(0),
    preferences: List[str] = Form(default=[]),
    cities_text: str = Form(""),
    extra_info: str = Form(""),
):
    # 组合文本，与/plan一致
    computed_days = days
    if not computed_days and start_date and end_date:
        try:
            d1 = datetime.fromisoformat(start_date)
            d2 = datetime.fromisoformat(end_date)
            delta = (d2 - d1).days + 1
            if delta > 0:
                computed_days = delta
        except Exception:
            computed_days = days
    parts = []
    if destination:
        parts.append(f"我想去{destination}")
    if start_date and end_date and computed_days:
        parts.append(f"从{start_date}到{end_date}共{computed_days}天")
    elif computed_days:
        parts.append(f"{computed_days}天")
    if budget_cny:
        parts.append(f"预算{budget_cny}元")
    parts.append(f"成人{adults}，儿童{children}")
    if preferences:
        parts.append("喜欢" + ",".join(preferences))
    if cities_text:
        cities_list = [c for c in re.split(r"[，,\s]+", cities_text.strip()) if c]
        if cities_list:
            parts.append("城市包括" + "、".join(cities_list))
    if extra_info:
        parts.append("补充信息：" + extra_info)
    text = "，".join(parts) if parts else ""
    try:
        return plan_trip(text)
    except Exception as e:
        return {"error": f"无法调用LLM：{e}"}