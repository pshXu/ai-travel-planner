from typing import Dict, List


DEFAULT_ALLOCATION = {
    "交通": 0.30,
    "住宿": 0.35,
    "餐饮": 0.20,
    "景点门票": 0.10,
    "其他": 0.05,
}


def _per_person_factor(people: Dict) -> float:
    # 儿童费用按成人的 0.5 估算
    adults = people.get("adults", 1)
    children = people.get("children", 0)
    return adults + children * 0.5


def make_budget_plan(parsed: Dict, itinerary: Dict) -> Dict:
    total = parsed.get("budget_cny")
    days = itinerary.get("days", 3)
    people = itinerary.get("people", {"adults": 1, "children": 0})
    pp_factor = _per_person_factor(people)

    # 若未给出预算，则给出建议区间（按天/人）
    if not total:
        # 经济/舒适/豪华人均天预算（RMB）：300/500/900
        econ = int(pp_factor * days * 300)
        comfort = int(pp_factor * days * 500)
        luxury = int(pp_factor * days * 900)
        total = comfort
        suggestion = {"经济": econ, "舒适": comfort, "豪华": luxury}
    else:
        suggestion = {
            "经济": int(total * 0.8),
            "舒适": int(total),
            "豪华": int(total * 1.5),
        }

    allocations = {}
    for k, p in DEFAULT_ALLOCATION.items():
        allocations[k] = int(total * p)

    # 简易估算各日餐饮与门票：
    # 餐饮：成人 150/天，儿童 100/天；门票：依据景点静态票价汇总
    daily_meal = int(days * (people["adults"] * 150 + people["children"] * 100))
    ticket_sum = 0
    for d in itinerary.get("plan", []):
        for node in [d.get("morning"), d.get("afternoon")]:
            if node and node.get("ticket_cny", 0) > 0:
                ticket_sum += node.get("ticket_cny", 0)

    estimate = {
        "餐饮总计": daily_meal,
        "门票总计": ticket_sum,
        "交通总计": allocations["交通"],
        "住宿总计": allocations["住宿"],
        "其他总计": allocations["其他"],
    }

    return {
        "total_budget_cny": total,
        "suggestion": suggestion,
        "allocations": allocations,
        "estimate": estimate,
    }