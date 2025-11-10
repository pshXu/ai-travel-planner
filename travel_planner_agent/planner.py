from typing import Dict, List
import os
from .providers import get_static_city_bundle
from .llm import generate_itinerary_llm, _llm_client_ok


def _pick_items(items: List[Dict], types: List[str], limit: int) -> List[Dict]:
    if not items:
        return []
    selected = []
    for t in types:
        for it in items:
            if it.get("type") == t and it not in selected:
                selected.append(it)
                if len(selected) >= limit:
                    return selected
    # 填充不足
    for it in items:
        if it not in selected:
            selected.append(it)
            if len(selected) >= limit:
                break
    return selected


def _meal_suggestion(restaurants: List[Dict], preference: List[str]) -> List[Dict]:
    # 简单策略：美食偏好优先海鲜/拉面；动漫偏好推荐秋叶原周边餐馆
    picks = []
    for r in restaurants:
        if "美食" in preference and r["cuisine"] in ("海鲜", "拉面"):
            picks.append(r)
        elif "动漫" in preference and ("秋叶原" in r["area"] or "多区域" in r["area"]):
            picks.append(r)
    # 回填其他
    for r in restaurants:
        if r not in picks:
            picks.append(r)
    return picks[:3]


def _hotel_suggestion(hotels: List[Dict], people: Dict, preference: List[str]) -> Dict:
    # 亲子优先：上野/浅草区域，步行与公园便利
    for h in hotels:
        if "亲子" in preference and ("上野" in h["area"] or "浅草" in h["area"]):
            return h
    # 默认选择新宿，餐饮选择多
    return hotels[0] if hotels else {"name": "市中心酒店(示例)", "area": "中心区", "price_range_cny": [600, 900]}


def generate_itinerary(parsed: Dict) -> Dict:
    """默认使用DeepSeek生成行程；失败时回退静态策略。"""
    use_llm = os.environ.get("LLM_PLAN", "1") == "1" and _llm_client_ok()
    if use_llm:
        try:
            return generate_itinerary_llm(parsed)
        except Exception:
            pass

    # 回退：静态策略
    destination = parsed.get("destination")
    city = parsed.get("city") or ("东京" if destination == "日本" else None)
    days = parsed.get("days", 3)
    people = parsed.get("people", {"adults": 1, "children": 0})
    preference = parsed.get("preferences", [])

    data = get_static_city_bundle(city or "东京")
    attractions = data.get("attractions", [])
    restaurants = data.get("restaurants", [])
    hotels = data.get("hotels", [])
    transport = data.get("transport", {})

    hotel = _hotel_suggestion(hotels, people, preference)
    meals = _meal_suggestion(restaurants, preference)

    day_plans: List[Dict] = []
    base_routes = [
        ["浅草寺", "东京晴空塔"],
        ["秋叶原电器街", "台场海滨公园与商圈"],
        ["上野动物园", "teamLab Planets"],
        ["明治神宫", "涩谷十字路口与天空平台(免费)"]
    ]

    if "亲子" in preference:
        base_routes.insert(0, ["上野动物园", "浅草寺"])  # 优先亲子与轻松文化
    if "动漫" in preference:
        base_routes.insert(0, ["秋叶原电器街"])  # 动漫偏好优先秋叶原

    seen = set()
    final_routes = []
    for r in base_routes:
        fr = []
        for name in r:
            if name not in seen:
                seen.add(name)
                fr.append(name)
        if fr:
            final_routes.append(fr)
        if len(final_routes) >= days:
            break

    def find_attr(name: str) -> Dict:
        for a in attractions:
            if a["name"] == name:
                return a
        return {"name": name, "type": "景点", "open_time": "请查询", "ticket_cny": 0, "duration_hours": 2, "area": "市区"}

    for i in range(days):
        today = final_routes[i] if i < len(final_routes) else []
        picks = [find_attr(n) for n in today]
        morning = picks[0] if len(picks) > 0 else None
        afternoon = picks[1] if len(picks) > 1 else None
        evening = meals[i % len(meals)] if meals else None

        day_plans.append({
            "day": i + 1,
            "theme": "轻松亲子文化" if "亲子" in preference else ("动漫与城市地标" if "动漫" in preference else "城市精选"),
            "morning": morning,
            "afternoon": afternoon,
            "evening_meal": evening,
            "notes": "按区域安排，步行+地铁优先，避免折返",
        })

    return {
        "destination": destination or "日本",
        "city": city or "东京",
        "hotel": hotel,
        "transport": transport,
        "days": days,
        "plan": day_plans,
        "people": people,
        "preferences": preference,
    }