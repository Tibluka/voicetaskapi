from datetime import datetime
from pymongo.collection import Collection
from bson import Decimal128


def sum_recent_spending(user_id: str, collection: Collection = None) -> float:
    now = datetime.now()
    year_month = now.strftime("%Y-%m")  # ex: '2025-06'

    date_range = {
        "$gte": f"{year_month}-01",
        "$lte": f"{year_month}-31",  # MongoDB faz comparação lexicográfica com strings
    }

    pipeline = [
        {"$match": {"userId": user_id, "type": "SPENDING", "date": date_range}},
        {"$group": {"_id": None, "total": {"$sum": "$value"}}},
    ]

    result = list(collection.aggregate(pipeline))
    if result:
        total = result[0]["total"]
        return float(total.to_decimal() if isinstance(total, Decimal128) else total)
    return 0.0
