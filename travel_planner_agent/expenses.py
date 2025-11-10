from typing import Dict, List


class BudgetTracker:
    def __init__(self, budget_plan: Dict):
        self.budget_plan = budget_plan
        self.records: List[Dict] = []

    def add_record(self, category: str, amount_cny: int, note: str = ""):
        self.records.append({
            "category": category,
            "amount_cny": amount_cny,
            "note": note,
        })

    def summary(self) -> Dict:
        used = {}
        for r in self.records:
            used[r["category"]] = used.get(r["category"], 0) + r["amount_cny"]
        allocations = self.budget_plan.get("allocations", {})
        warning = []
        for cat, limit in allocations.items():
            if used.get(cat, 0) > limit:
                warning.append(f"{cat} 超支 {used.get(cat, 0) - limit} 元")
        return {"used": used, "warning": warning}