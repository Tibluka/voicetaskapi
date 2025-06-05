
from pymongo import DESCENDING, ASCENDING
from flask import g
from utils.date_utils import get_date_range
from datetime import datetime
from dateutil.relativedelta import relativedelta

class SpendingService:
    def __init__(self, collection):
        self.collection = collection

    def insert_spending(self, data: dict):
        logged_user = g.logged_user
        user_id = logged_user.get('id')

        required_fields = ["description", "value", "type", "category", "date"]
        missing = [field for field in required_fields if not data.get(field)]

        if missing:
            raise ValueError(f"Missing fields: {', '.join(missing)}")

        installments = int(data.get("installments", 1))

        try:
            base_date = datetime.strptime(data["date"], "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in 'YYYY-MM-DD' format")

        # 🔥 Compra à vista
        if installments <= 1:
            doc = {
                "userId": user_id,
                "description": data["description"],
                "value": float(data["value"]),
                "type": data["type"],
                "category": data["category"],
                "date": base_date.strftime("%Y-%m-%d"),
            }
            self.collection.insert_one(doc)

        # 🔥 Compra parcelada
        else:
            value_per_installment = float(data["value"]) / installments

            # Documento principal
            parent_doc = {
                "userId": user_id,
                "description": data["description"],
                "value": round(value_per_installment, 2),
                "type": data["type"],
                "category": data["category"],
                "date": base_date.strftime("%Y-%m-%d"),
                "installments": installments,
                "installment_info": f"1/{installments}",
                "is_parent": True,
            }
            parent_result = self.collection.insert_one(parent_doc)
            parent_id = parent_result.inserted_id

            # Documentos das parcelas
            docs = []
            for i in range(installments - 1):
                installment_date = (base_date + relativedelta(months=i + 1)).strftime("%Y-%m-%d")
                doc = {
                    "user_id": user_id,
                    "description": data["description"],
                    "value": round(value_per_installment, 2),
                    "type": data["type"],
                    "category": data["category"],
                    "date": installment_date,
                    "installments": installments,
                    "installment_info": f"{i + 2}/{installments}",
                    "parent_id": parent_id,
                }
                docs.append(doc)

            self.collection.insert_many(docs)

    def consult_spending(self, data: dict):
        logged_user = g.logged_user
        user_id = logged_user.get('id')
        
        filters = {
            "userId": user_id  # 🔥 Filtro por usuário
        }

        # Filtros básicos
        for k in ["type", "category"]:
            if data.get(k):
                filters[k] = data[k]

        # Filtro de data (intervalo para 'YYYY-MM' ou exato para 'YYYY-MM-DD')
        if data.get("date"):
            date_val = data["date"]
            if len(date_val) == 7:  # yyyy-mm
                filters["date"] = get_date_range(date_val)
            elif len(date_val) == 10:  # yyyy-mm-dd
                filters["date"] = date_val
            else:
                raise ValueError("Date must be 'YYYY-MM' or 'YYYY-MM-DD'")

        # Se for consulta só de parcelas
        if data.get("consult_installment") is True:
            filters["installments"] = {"$gte": 1}

            if data.get("date"):
                date_val = data["date"]
                if len(date_val) == 7:  # yyyy-mm
                    filters["date"] = get_date_range(date_val)
                elif len(date_val) == 10:  # yyyy-mm-dd
                    filters["date"] = date_val
                else:
                    raise ValueError("Date must be 'YYYY-MM' or 'YYYY-MM-DD'")
            else:
                today_str = datetime.today().strftime("%Y-%m")
                filters["date"] = get_date_range(today_str)

        else:
            filters["$or"] = [
                {"is_parent": {"$exists": False}},  # compras à vista
                {"is_parent": True}                 # compras principais (parent)
            ]

        # Ordenação
        operation = data.get("operation")
        sort_order = None
        if operation == "MAX":
            sort_order = ("value", DESCENDING)
        elif operation == "MIN":
            sort_order = ("value", ASCENDING)

        # Busca no MongoDB
        if sort_order:
            results = list(self.collection.find(filters).sort([sort_order]).limit(1))
        else:
            results = list(self.collection.find(filters))

        # Converter ObjectId para string
        for r in results:
            r["_id"] = str(r["_id"])

        return results