VERSION = "0.1.0"

from .parser import parse_input
from .planner import generate_itinerary
from .budget import make_budget_plan
from .output import build_structured_output, export_json, export_csv
from .expenses import BudgetTracker
from .tips import build_tips


def plan_trip(natural_text: str):
    parsed = parse_input(natural_text)
    itinerary = generate_itinerary(parsed)
    budget_plan = make_budget_plan(parsed, itinerary)
    tips = build_tips(parsed)
    tracker = BudgetTracker(budget_plan)
    output = build_structured_output(parsed, itinerary, budget_plan, tips, tracker)
    return output