from flask import g
from pymongo.collection import Collection
from typing import Dict, Any, List, Optional
from zoneinfo import ZoneInfo
from datetime import datetime
from bson import ObjectId
from dto.project_dto import create_project_dict, project_to_dto


class ProfileConfigService:
    def __init__(self, collection: Collection):
        self.collection = collection

    def consult_profile_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        logged_user = g.logged_user
        user_id = logged_user.get("id")

        config_field = data.get("config_field")
        if not config_field:
            raise ValueError("Campo 'config_field' não especificado.")

        # Se for consulta de projeto, retorna o projeto específico
        if config_field == "project_consulting":
            project_name = data.get("projectName")
            if not project_name:
                raise ValueError("Nome do projeto não especificado para project_consulting.")
            
            project = self.get_project_by_name(project_name)
            return {"config_field": config_field, "project": project}

        # Para outros campos, retorna o documento completo
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
                "projects": [],  # Novo campo para projetos
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

    def create_project(self, name: str, description: str = "", target_value: Optional[float] = None) -> Dict[str, Any]:
        """Cria um novo projeto para o usuário logado"""
        logged_user = g.logged_user
        user_id = logged_user.get("id")
        
        # Busca ou cria o profile config
        profile_config = self.collection.find_one({"userId": user_id})
        if not profile_config:
            profile_config = self.create_default_profile_config()
            profile_config = self.collection.find_one({"userId": user_id})
        
        # Cria o novo projeto
        new_project = create_project_dict(name, description, target_value)
        
        # Adiciona ao array de projetos
        self.collection.update_one(
            {"userId": user_id},
            {
                "$push": {"projects": new_project},
                "$set": {"updatedAt": datetime.now(ZoneInfo("America/Sao_Paulo"))}
            }
        )
        
        return project_to_dto(new_project)

    def get_project_by_id(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Busca um projeto específico pelo ID"""
        logged_user = g.logged_user
        user_id = logged_user.get("id")
        
        profile_config = self.collection.find_one(
            {"userId": user_id, "projects.projectId": project_id},
            {"projects.$": 1}
        )
        
        if profile_config and profile_config.get("projects"):
            return profile_config["projects"][0]
        return None

    def get_project_by_name(self, project_name: str) -> Optional[Dict[str, Any]]:
        """Busca um projeto pelo nome (case insensitive)"""
        logged_user = g.logged_user
        user_id = logged_user.get("id")
        
        profile_config = self.collection.find_one({"userId": user_id})
        if not profile_config or not profile_config.get("projects"):
            return None
        
        # Busca case insensitive
        for project in profile_config.get("projects", []):
            if project["projectName"].lower() == project_name.lower():
                return project
        return None

    def update_project_spending(self, project_id: str, value: float) -> bool:
        """Atualiza o valor total gasto em um projeto"""
        logged_user = g.logged_user
        user_id = logged_user.get("id")
        
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        
        result = self.collection.update_one(
            {"userId": user_id, "projects.projectId": project_id},
            {
                "$inc": {"projects.$.totalValueRegistered": value},
                "$set": {
                    "projects.$.dateHourUpdated": now,
                    "updatedAt": now
                }
            }
        )
        
        return result.modified_count > 0

    def list_user_projects(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista todos os projetos do usuário"""
        logged_user = g.logged_user
        user_id = logged_user.get("id")
        
        profile_config = self.collection.find_one({"userId": user_id})
        if not profile_config:
            return []
        
        projects = profile_config.get("projects", [])
        
        # Filtra por status se especificado
        if status:
            projects = [p for p in projects if p.get("status") == status]
        
        return [project_to_dto(p) for p in projects]