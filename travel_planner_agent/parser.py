import os
import re
from typing import Dict, List, Optional
from .llm import parse_input_llm, _llm_client_ok


PREFERENCE_KEYWORDS = [
    "美食", "文化", "冒险", "购物", "亲子", "动漫", "自然", "海岛", "博物馆", "历史",
]

SPECIAL_NEEDS_KEYWORDS = [
    "无障碍", "轮椅", "婴儿车", "饮食限制", "清真", "素食", "无麸质",
]


def _extract_destination(text: str) -> Optional[str]:
    # 常见模式："去日本"、"想去东京"、"目的地是京都"
    m = re.search(r"去([\u4e00-\u9fa5A-Za-z]+)", text)
    if m:
        return m.group(1)
    m = re.search(r"目的地[是为:]?([\u4e00-\u9fa5A-Za-z]+)", text)
    if m:
        return m.group(1)
    return None


def _extract_days(text: str) -> Optional[int]:
    m = re.search(r"(\d+)[天日]", text)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None


def _extract_budget_cny(text: str) -> Optional[int]:
    # 识别：1万元、10000元、1万、1W、1w
    m = re.search(r"(\d+[\.]?\d*)\s*(万|万元|W|w|元|块)", text)
    if not m:
        return None
    amount = float(m.group(1))
    unit = m.group(2)
    if unit in ["万", "万元", "W", "w"]:
        return int(amount * 10000)
    return int(amount)


def _extract_people(text: str) -> Dict[str, int]:
    adults = 2 if re.search(r"(情侣|夫妻|两人|双人)", text) else 1
    # 明确人数：3人、2位成人
    m = re.search(r"(\d+)\s*(人|位)", text)
    if m:
        try:
            adults = int(m.group(1))
        except Exception:
            pass
    children = 1 if re.search(r"(带孩子|小孩|儿童|亲子)", text) else 0
    # 明确儿童数：1个孩子、2名儿童
    mc = re.search(r"(\d+)\s*(个|名)?(孩子|儿童|小孩)", text)
    if mc:
        try:
            children = int(mc.group(1))
        except Exception:
            pass
    return {"adults": max(adults, 1), "children": max(children, 0)}


def _extract_preferences(text: str) -> List[str]:
    prefs = []
    for k in PREFERENCE_KEYWORDS:
        if k in text:
            prefs.append(k)
    return prefs


def _extract_special_needs(text: str) -> List[str]:
    needs = []
    for k in SPECIAL_NEEDS_KEYWORDS:
        if k in text:
            needs.append(k)
    return needs


def parse_input(text: str) -> Dict:
    """解析自然语言输入为结构化参数。若LLM不可用或失败，则抛出异常。"""
    use_llm = os.environ.get("LLM_PARSE", "1") == "1" and _llm_client_ok()
    if not use_llm:
        raise RuntimeError("无法调用LLM：未配置或不可用")
    try:
        return parse_input_llm(text)
    except Exception as e:
        raise RuntimeError(f"LLM解析失败：{e}")