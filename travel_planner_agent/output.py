import json
from typing import Dict


def build_structured_output(parsed: Dict, itinerary: Dict, budget_plan: Dict, tips: Dict, tracker) -> Dict:
    overview = {
        "目的地": itinerary.get("destination"),
        "城市": itinerary.get("city"),
        "天数": itinerary.get("days"),
        "人数": itinerary.get("people"),
        "总预算": budget_plan.get("total_budget_cny"),
        "旅行主题": itinerary.get("preferences"),
    }

    detail_days = []
    aggregated_daily_notes = []
    for d in itinerary.get("plan", []):
        items = []
        for part_key in ["morning", "afternoon"]:
            node = d.get(part_key)
            if node:
                items.append({
                    "地点": node.get("name"),
                    "类型": node.get("type"),
                    "开放时间": node.get("open_time"),
                    "门票(¥)": node.get("ticket_cny"),
                    "游玩时长(h)": node.get("duration_hours"),
                    "适合人群": node.get("suitable"),
                    "区域": node.get("area"),
                })
        if d.get("evening_meal"):
            meal = d["evening_meal"]
            items.append({
                "餐厅": meal.get("name"),
                "美食类型": meal.get("cuisine"),
                "人均(¥)": meal.get("avg_spend_cny"),
                "位置": meal.get("area"),
                "特色": meal.get("features"),
            })
        note_text = d.get("notes")
        if note_text:
            aggregated_daily_notes.append(str(note_text))
        detail_days.append({
            "日期": f"第{d.get('day')}天",
            "主题": d.get("theme"),
            "安排": items,
            "备注": d.get("notes"),
        })

    fee_table = {
        "预算分配": budget_plan.get("allocations"),
        "估算费用": budget_plan.get("estimate"),
        "建议档位": budget_plan.get("suggestion"),
        "实际支出": tracker.summary(),
    }

    # 将每日备注汇总到“实用信息/注意事项”中（去重，保序）
    base_notes = tips.get("notes") or []
    merged_notes = list(base_notes)
    seen = set()
    for n in merged_notes:
        if isinstance(n, str):
            seen.add(n)
    for n in aggregated_daily_notes:
        if n and n not in seen:
            merged_notes.append(n)
            seen.add(n)

    useful = {
        "天气提示": tips.get("weather_tip"),
        "交通卡/优惠": tips.get("transit_tip") or [],
        "注意事项": merged_notes,
    }

    return {
        "行程概览": overview,
        "详细日程": detail_days,
        "费用明细表": fee_table,
        "实用信息": useful,
        "住宿推荐": itinerary.get("hotel"),
        "交通建议": itinerary.get("transport"),
    }


def export_json(data: Dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def export_csv(data: Dict, path: str):
    # 简易 CSV 导出：导出预算表与概览关键字段
    import csv
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        overview = data.get("行程概览", {})
        w.writerow(["目的地", overview.get("目的地"), "城市", overview.get("城市")])
        w.writerow(["天数", overview.get("天数"), "总预算", overview.get("总预算")])
        w.writerow(["人数", overview.get("人数")])
        w.writerow(["主题", ",".join(overview.get("旅行主题") or [])])
        w.writerow([])
        w.writerow(["预算分配"])
        for k, v in (data.get("费用明细表", {}).get("预算分配", {}) or {}).items():
            w.writerow([k, v])