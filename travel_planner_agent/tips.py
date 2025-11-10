from typing import Dict


def build_tips(parsed: Dict) -> Dict:
    prefs = parsed.get("preferences", [])
    special = parsed.get("special_needs", [])
    destination = parsed.get("destination", "目的地")

    # 通用天气提示，不再硬编码特定地区
    weather = f"出行前请查看{destination}当地天气预报，准备合适的衣物和防护用品。"
    
    # 通用交通提示
    transit = [
        "建议提前了解当地交通卡或优惠票券",
        "可考虑购买当地公共交通通票以节省费用",
    ]
    
    # 通用注意事项
    notes = [
        "建议携带现金和银行卡，以备不同支付场景",
        "热门景点建议提前预约或购票",
        "注意当地的文化习俗和礼仪",
    ]

    if "亲子" in prefs:
        notes.append("亲子出行注意安排合理的休息时间，选择适合儿童的路线和设施")
    if special:
        notes.append("根据特殊需求提前确认酒店与景点的无障碍设施与餐饮选择")

    return {
        "weather_tip": weather,
        "transit_tip": transit,
        "notes": notes,
    }