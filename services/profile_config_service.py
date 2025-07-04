from flask import g
from pymongo.collection import Collection
from typing import Dict, Any
from zoneinfo import ZoneInfo
from datetime import datetime


class ProfileConfigService:
    def __init__(self, collection: Collection):
        self.collection = collection

    def consult_profile_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        logged_user = g.logged_user
        user_id = logged_user.get("id")

        config_field = data.get("config_field")
        if not config_field:
            raise ValueError("Campo 'config_field' não especificado.")

        strategy_doc = self.collection.find_one({"userId": user_id})
        return {"config_field": config_field, "profile-config": strategy_doc}

    def create_default_profile_config(
        self, income: float = None, limit: float = None
    ) -> Dict[str, Any]:
        try:
            """
            Cria uma nova configuração de perfil com estratégia padrão 50-30-20 e sem contas fixas.

            :param collection: Coleção MongoDB onde a configuração será inserida (ex: db.settings)
            :param income: Renda mensal opcional
            :param limit: Limite mensal opcional
            :return: Objeto de configuração criada
            """
            logged_user = g.logged_user
            user_id = logged_user.get("id")

            now = datetime.now(ZoneInfo("America/Sao_Paulo"))

            config = {
                "userId": user_id,
                "budgetStrategy": "50-30-20",
                "customPercentages": {"needs": 50, "wants": 30, "investments": 20},
                "fixedBills": [],
                "createdAt": now,
                "updatedAt": now,
            }

            if income is not None:
                config["monthlyIncome"] = income
            if limit is not None:
                config["monthLimit"] = limit

            result = self.collection.insert_one(config)
            config["id"] = str(result.inserted_id)
            return config
        except Exception as e:
            return None
