import os
import json
from typing import Dict, Any, List, Optional


# DeepSeek（OpenAI兼容）
_DEEPSEEK_AVAILABLE = True
try:
    from openai import OpenAI
except Exception:
    _DEEPSEEK_AVAILABLE = False

try:
    from . import config as _cfg
except Exception:
    _cfg = None


def _cfg_get(name: str, default=None):
    # 优先读取本地配置文件；为空则回退到环境变量
    if _cfg and hasattr(_cfg, name):
        val = getattr(_cfg, name)
        if isinstance(val, str):
            if val.strip():
                return val.strip()
        elif val is not None:
            return val
    return os.environ.get(name, default)


def _llm_client_ok() -> bool:
    return _DEEPSEEK_AVAILABLE and bool(_cfg_get("DEEPSEEK_API_KEY"))


DEFAULT_DEEPSEEK_MODEL = _cfg_get("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_API_BASE = _cfg_get("DEEPSEEK_API_BASE", "https://api.deepseek.com")


def _get_client():
    if not _llm_client_ok():
        raise RuntimeError("DeepSeek未配置，请在 config.py 填写 DEEPSEEK_API_KEY 或设置环境变量，并安装 openai 依赖。")
    return OpenAI(api_key=_cfg_get("DEEPSEEK_API_KEY"), base_url=DEEPSEEK_API_BASE)


def ask(messages: List[Dict[str, str]], model: Optional[str] = None, temperature: float = 0.4) -> str:
    client = _get_client()
    model = model or DEFAULT_DEEPSEEK_MODEL
    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=messages,
    )
    return resp.choices[0].message.content


def parse_input_llm(text: str) -> Dict[str, Any]:
    system = {
        "role": "system",
        "content": (
            "你是专业旅行规划助手。请仅返回JSON对象，字段："
            "destination, city, days, budget_cny, people{adults,children}, preferences[], special_needs[]."
            "如无法确定，请给出合理默认值（days=3, budget_cny=null, people={adults:1,children:0}）。"
        ),
    }
    user = {"role": "user", "content": text}
    content = ask([system, user])
    try:
        data = json.loads(content)
    except Exception:
        data = {}
    days = int(data.get("days") or 3)
    budget_cny = data.get("budget_cny")
    try:
        if isinstance(budget_cny, str):
            budget_cny = int(float(budget_cny))
    except Exception:
        budget_cny = None
    people = data.get("people") or {"adults": 1, "children": 0}
    return {
        "raw_text": text,
        "destination": data.get("destination"),
        "city": data.get("city"),
        "days": days,
        "budget_cny": budget_cny,
        "people": people,
        "preferences": data.get("preferences") or [],
        "special_needs": data.get("special_needs") or [],
    }


def generate_itinerary_llm(parsed: Dict) -> Dict:
    system = {
        "role": "system",
        "content": (
            "作为专业旅行顾问，根据输入参数生成可执行的多日行程。"
            "仅返回一个JSON对象，字段：destination, city, hotel{name, area, price_range_cny:[low,high]},"
            "transport{airport_city:[{route,mode,cost_cny,duration_min}], local:[{card,pass?,benefit,cost_cny?}]},"
            "days, plan:[{day, theme, morning:{name,type,open_time,ticket_cny,duration_hours,suitable,area},"
            "afternoon:{...同结构}, evening_meal:{name,cuisine,avg_spend_cny,area,features}, notes}],"
            "people{adults,children}, preferences[]。时间安排应避免重复与不合理折返，兼顾亲子与偏好。"
        ),
    }
    user = {"role": "user", "content": json.dumps(parsed, ensure_ascii=False)}
    content = ask([system, user], temperature=0.5)
    try:
        data = json.loads(content)
    except Exception:
        data = {
            "destination": parsed.get("destination"),
            "city": parsed.get("city") or "市区",
            "hotel": {"name": "中心区酒店", "area": "中心区", "price_range_cny": [500, 900]},
            "transport": {"airport_city": [], "local": []},
            "days": parsed.get("days", 3),
            "plan": [],
            "people": parsed.get("people", {"adults": 1, "children": 0}),
            "preferences": parsed.get("preferences", []),
        }
    data.setdefault("destination", parsed.get("destination"))
    data.setdefault("city", parsed.get("city") or "市区")
    data.setdefault("days", parsed.get("days", 3))
    data.setdefault("people", parsed.get("people", {"adults": 1, "children": 0}))
    data.setdefault("preferences", parsed.get("preferences", []))
    data.setdefault("hotel", {"name": "中心区酒店", "area": "中心区", "price_range_cny": [500, 900]})
    data.setdefault("transport", {"airport_city": [], "local": []})
    data.setdefault("plan", [])
    return data


def generate_tips_llm(parsed: Dict) -> Dict:
    system = {
        "role": "system",
        "content": "为目的地生成天气提示、交通卡建议与注意事项，仅返回JSON: {weather_tip, transit_tip[], notes[]}。",
    }
    user = {"role": "user", "content": json.dumps(parsed, ensure_ascii=False)}
    content = ask([system, user])
    try:
        return json.loads(content)
    except Exception:
        return {
            "weather_tip": "目的地气候随季节变化，请携带合适衣物与防晒/保暖用品。",
            "transit_tip": ["办理当地交通卡更便捷", "关注短期地铁票是否更划算"],
            "notes": ["热门景点需预约", "亲子出行注意节奏与安全"],
        }