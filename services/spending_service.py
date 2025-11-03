from bson import ObjectId
from pymongo import DESCENDING, ASCENDING
from flask import g
from utils.date_utils import get_date_range
from datetime import datetime
from dateutil.relativedelta import relativedelta
from services.profile_config_service import ProfileConfigService
from db.mongo import profile_config_collection


class SpendingService:
    def __init__(self, collection):
        self.collection = collection
        self.profile_service = ProfileConfigService(profile_config_collection)

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

        # Verifica se há projectId e atualiza o projeto
        project_id = data.get("projectId")
        if project_id:
            # Verifica se o projeto existe
            project = self.profile_service.get_project_by_id(project_id)
            if not project:
                raise ValueError(f"Project with id {project_id} not found")

        # 🔥 Compra à vista
        if installments == None or installments == 1:
            doc = {
                "userId": user_id,
                "description": data["description"],
                "value": float(data["value"]),
                "type": data["type"],
                "category": data["category"],
                "date": base_date.strftime("%Y-%m-%d"),
            }

            # Adiciona projectId se existir
            if project_id:
                doc["projectId"] = project_id

            self.collection.insert_one(doc)

            # Atualiza o valor total do projeto e adiciona ao histórico
            if project_id:
                self.profile_service.update_project_spending(
                    project_id=project_id,
                    value=float(data["value"]),
                    spending_id=str(doc["_id"]),
                    description=data["description"],
                    category=data["category"],
                    date=base_date.strftime("%Y-%m-%d"),
                    installments=1,
                    installment_info="1/1",
                )
            return doc
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

            # Adiciona projectId se existir
            if project_id:
                parent_doc["projectId"] = project_id

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

                # Adiciona projectId se existir
                if project_id:
                    doc["projectId"] = project_id

                docs.append(doc)

            self.collection.insert_many(docs)

            # Atualiza o valor total do projeto (valor total da compra) e adiciona ao histórico
            if project_id:
                self.profile_service.update_project_spending(
                    project_id=project_id,
                    value=float(data["value"]),
                    spending_id=str(parent_id),
                    description=data["description"],
                    category=data["category"],
                    date=base_date.strftime("%Y-%m-%d"),
                    installments=installments,
                    installment_info=f"1/{installments}",
                )
            return docs[0]

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

        # Se tiver projectId, precisamos descontar o valor do projeto
        if spending.get("projectId"):
            project_id = spending["projectId"]
            # Calcula o valor total a ser descontado
            if spending.get("is_parent"):
                # Se for pai, precisa calcular o valor total (todas as parcelas)
                total_value = spending["value"] * spending.get("installments", 1)
            else:
                # Se for parcela única ou gasto simples
                total_value = spending["value"]

            # Desconta do projeto (valor negativo) - não adiciona ao histórico pois é remoção
            self.profile_service.update_project_spending(project_id, -total_value)

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

        operation = data.get("operation")

        # 🆕 Consulta de projeto específico
        if operation == "CONSULT_PROJECT":
            project_name = data.get("projectName")
            if not project_name:
                raise ValueError(
                    "Project name is required for CONSULT_PROJECT operation"
                )

            # Busca o projeto pelo nome
            project = self.profile_service.get_project_by_name(project_name)
            if not project:
                return []  # Retorna lista vazia se projeto não existir

            # Adiciona o projectId ao filtro
            filters["projectId"] = project["projectId"]
            filters["type"] = "SPENDING"

            # Aplica filtro de data se fornecido
            if data.get("date"):
                date_val = data["date"]
                if len(date_val) == 7:  # yyyy-mm
                    filters["date"] = get_date_range(date_val)
                elif len(date_val) == 10:  # yyyy-mm-dd
                    filters["date"] = date_val

            # Busca todos os gastos do projeto
            results = list(self.collection.find(filters).sort("date", DESCENDING))
            for r in results:
                r["_id"] = str(r["_id"])
            return results

        # Para outras operações, exclui gastos com projectId se não for especificado
        if not data.get("projectId") and operation != "CONSULT_PROJECT":
            filters["projectId"] = {"$exists": False}

        # Filtros básicos
        for k in ["type", "category", "projectId"]:
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
