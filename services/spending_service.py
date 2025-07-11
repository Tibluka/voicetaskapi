from bson import ObjectId
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
        user_id = logged_user.get("id")

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
        if installments == None:
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
                installment_date = (base_date + relativedelta(months=i + 1)).strftime(
                    "%Y-%m-%d"
                )
                doc = {
                    "userId": user_id,
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

    def remove_spending(self, spending_id: str):
        logged_user = g.logged_user
        user_id = logged_user.get("id")

        try:
            obj_id = ObjectId(spending_id)
        except Exception:
            raise ValueError("Invalid spending ID format")

        # Busca o documento para verificar se existe e se pertence ao usuário
        spending = self.collection.find_one({"_id": obj_id, "userId": user_id})
        if not spending:
            raise ValueError("Spending not found or access denied")

        # Se for um gasto parcelado (pai), remover também as parcelas filhas
        if spending.get("is_parent"):
            # Remove o documento pai e os filhos que tenham parent_id igual ao id do pai
            self.collection.delete_many(
                {
                    "$or": [{"_id": obj_id}, {"parent_id": obj_id}],
                    "userId": user_id,  # garante que só remove do usuário logado
                }
            )
        else:
            # Remove apenas o documento único ou parcela (sem filhos)
            self.collection.delete_one({"_id": obj_id, "userId": user_id})

        return {"message": "Spending removed successfully"}

    def consult_spending(self, data: dict):
        logged_user = g.logged_user
        user_id = logged_user.get("id")

        filters = {"userId": user_id}  # 🔥 Filtro por usuário

        if data.get("type") == "PROFILE_CONFIG":
            data["type"] = "SPENDING"

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
            filters["$or"] = [{"installments": {"$exists": False}}, {"is_parent": True}]

        operation = data.get("operation")

        # 🆕 Agrupamento por categoria
        if operation == "CATEGORY":
            pipeline = [
                {"$match": filters},
                {
                    "$group": {
                        "_id": "$category",  # Agrupar por category
                        "total": {"$sum": "$value"},
                    }
                },
                {
                    "$project": {
                        "label": "$_id",  # Projetar category como label
                        "value": "$total",  # Projetar total como value
                        "_id": 0,
                    }
                },
                {"$sort": {"value": -1}},  # Ordenar por value decrescente
            ]
            results = list(self.collection.aggregate(pipeline))
            return results

        # 🆕 Comparativo mensal
        if operation == "COMPARATIVE":
            raw_range = data.get("date_range", "")
            try:
                from_str, to_str = [s.strip() for s in raw_range.split("a")]
                # Manter as datas como string para comparação
                date_from = from_str  # "2028-01-01"
                date_to = to_str  # "2028-12-31"
            except Exception as e:
                raise ValueError(f"Formato inválido de date_range: {raw_range}") from e

            # Filtro de data para campos string (comparação lexicográfica funciona com YYYY-MM-DD)
            filters["date"] = {"$gte": date_from, "$lte": date_to}

            pipeline = [
                {"$match": filters},
                {
                    "$group": {
                        "_id": {
                            # Extrair ano e mês da string "2028-02-05"
                            "year": {"$substr": ["$date", 0, 4]},  # "2028"
                            "month": {"$substr": ["$date", 5, 2]},  # "02"
                        },
                        "total": {"$sum": "$value"},
                    }
                },
                {
                    "$project": {
                        "month": {
                            "$concat": [
                                "$_id.month",  # Já está formatado como "02"
                                "/",
                                "$_id.year",  # "2028"
                            ]
                        },
                        "total": 1,
                        "_id": 0,
                    }
                },
                {"$sort": {"month": 1}},
            ]

            results = list(self.collection.aggregate(pipeline))
            return results

        # Ordenação simples
        sort_order = None
        if operation == "MAX":
            sort_order = ("value", DESCENDING)
        elif operation == "MIN":
            sort_order = ("value", ASCENDING)

        if sort_order:
            results = list(self.collection.find(filters).sort([sort_order]).limit(1))
        else:
            results = list(self.collection.find(filters))

        for r in results:
            r["_id"] = str(r["_id"])

        return results
