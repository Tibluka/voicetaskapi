def config_to_dto(cfg: dict) -> dict:
    return {
        "id": str(cfg["_id"]),
        "userId": cfg["userId"],
        "budgetStrategy": cfg["budgetStrategy"],
        "customPercentages": cfg.get("customPercentages"),
        "monthlyIncome": cfg.get("monthlyIncome"),
        "monthLimit": cfg.get("monthLimit"),
        "currentSpent": cfg.get("currentSpent", 0),
        "fixedBills": cfg.get("fixedBills", []),
        "goals": cfg.get("goals", []),
        "createdAt": cfg["createdAt"].isoformat(),
        "updatedAt": cfg["updatedAt"].isoformat(),
    }
