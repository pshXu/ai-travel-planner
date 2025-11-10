from travel_planner_agent import plan_trip, export_json, export_csv


def demo():
    text = "我想去日本,5天,预算1万元,喜欢美食和动漫,带孩子"
    result = plan_trip(text)
    print("==== 行程概览 ====")
    print(result["行程概览"])
    print("\n==== 详细日程 (前2天预览) ====")
    for day in result["详细日程"][:2]:
        print(day)
    print("\n==== 费用明细表 ====")
    print(result["费用明细表"])
    print("\n==== 实用信息 ====")
    print(result["实用信息"])

    export_json(result, "output_trip.json")
    export_csv(result, "output_budget.csv")
    print("\n已导出: output_trip.json, output_budget.csv")


if __name__ == "__main__":
    demo()