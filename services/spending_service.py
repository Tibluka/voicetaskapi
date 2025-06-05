
from pymongo import DESCENDING, ASCENDING
from bson import ObjectId
from utils.date_utils import get_date_range
from datetime import datetime
from dateutil.relativedelta import relativedelta

class SpendingService:
    def __init__(self, collection):
        self.collection = collection

    def insert_spending(self, data: dict):
        required_fields = ["description", "value", "type", "category", "date"]
        missing = [field for field in required_fields if not data.get(field)]

        if missing:
            raise ValueError(f"Missing fields: {', '.join(missing)}")

        installments = int(data.get("installments", 1))

        try:
            # Força o formato YYYY-MM-DD
            base_date = datetime.strptime(data["date"], "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in 'YYYY-MM-DD' format")

        # 🔥 Compra à vista
        if installments <= 1:
            doc = {
                "description": data["description"],
                "value": float(data["value"]),
                "type": data["type"],
                "category": data["category"],
                "date": base_date.strftime("%Y-%m-%d"),  # Salva sempre como YYYY-MM-DD
            }
            self.collection.insert_one(doc)

        # 🔥 Compra parcelada
        else:
            value_per_installment = float(data["value"]) / installments

            # Documento principal
            parent_doc = {
                "description": data["description"],
                "value": float(data["value"]),
                "type": data["type"],
                "category": data["category"],
                "date": base_date.strftime("%Y-%m-%d"),
                "installments": installments,
                "is_parent": True,
            }
            parent_result = self.collection.insert_one(parent_doc)
            parent_id = parent_result.inserted_id

            # Documentos das parcelas
            docs = []
            for i in range(installments):
                installment_date = (base_date + relativedelta(months=i)).strftime("%Y-%m-%d")
                doc = {
                    "description": data["description"],
                    "value": round(value_per_installment, 2),
                    "type": data["type"],
                    "category": data["category"],
                    "date": installment_date,
                    "installment_info": f"{i + 1}/{installments}",
                    "parent_id": parent_id,
                }
                docs.append(doc)

            self.collection.insert_many(docs)

    def consult_spending(self, data: dict):
        filters = {k: data[k] for k in ["type", "category"] if data.get(k)}

        # 🔥 Filtro por mês (aceita YYYY-MM ou YYYY-MM-DD)
        if data.get("date"):
            try:
                date_str = data["date"]
                base_date = datetime.strptime(date_str, "%Y-%m-%d" if len(date_str) == 10 else "%Y-%m")
                filters["date"] = base_date.strftime("%Y-%m")
            except ValueError:
                raise ValueError("Date must be in 'YYYY-MM' or 'YYYY-MM-DD' format")

        # 🔥 Consultar apenas parcelas do mês atual
        if data.get("consult_installment"):
            filters["installment_info"] = {"$exists": True}
            filters["date"] = datetime.now().strftime("%Y-%m")  # mês atual
            filters["is_parent"] = False

        # 🔥 Consultar apenas compras principais
        if data.get("consult_parent"):
            filters["is_parent"] = True

        # 🔥 Operações de valor máximo/mínimo
        operation = data.get("operation")
        sort_order = None

        if operation == "MAX":
            sort_order = ("value", DESCENDING)
        elif operation == "MIN":
            sort_order = ("value", ASCENDING)

        # 🔍 Faz a consulta
        if sort_order:
            results = list(self.collection.find(filters).sort([sort_order]).limit(1))
        else:
            results = list(self.collection.find(filters))

        # 🔧 Converte ObjectId para string
        for r in results:
            r["_id"] = str(r["_id"])
            if r.get("parent_id"):
                r["parent_id"] = str(r["parent_id"])

        return results