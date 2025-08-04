from flask import g
from pymongo.collection import Collection
from typing import Dict, Any, List, Optional
from zoneinfo import ZoneInfo
from datetime import datetime
from dto.project_dto import create_project_dict, project_to_dto
from dto.fixed_bills_dto import (
    create_fixed_bill_dict,
    fixed_bill_to_dto,
    create_payment_record,
    get_bill_status_for_month,
)


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
                raise ValueError(
                    "Nome do projeto não especificado para project_consulting."
                )

            project = self.get_project_by_name(project_name)
            return {"config_field": config_field, "project": project}

        # Se for consulta de contas fixas
        if config_field == "fixed_bills":
            bills_status = data.get("bills_status", "ALL")
            month = data.get("date", datetime.now().strftime("%Y-%m"))

            # Busca o resumo das contas fixas
            summary = self.get_fixed_bills_summary(month)

            # Filtra as contas baseado no status solicitado
            if bills_status == "PAID":
                filtered_bills = [b for b in summary["bills"] if b["paid"]]
            elif bills_status == "PENDING":
                filtered_bills = [b for b in summary["bills"] if not b["paid"]]
            else:  # ALL
                filtered_bills = summary["bills"]

            return {
                "config_field": config_field,
                "fixed_bills_summary": {
                    "month": month,
                    "bills": filtered_bills,
                    "totalAmount": summary["totalAmount"],
                    "paidAmount": summary["paidAmount"],
                    "pendingAmount": summary["pendingAmount"],
                    "requestedStatus": bills_status,
                },
            }

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
                "goals": [],
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

    def create_project(
        self, name: str, description: str = "", target_value: Optional[float] = None
    ) -> Dict[str, Any]:
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
                "$set": {"updatedAt": datetime.now(ZoneInfo("America/Sao_Paulo"))},
            },
        )

        return project_to_dto(new_project)

    def get_project_by_id(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Busca um projeto específico pelo ID"""
        logged_user = g.logged_user
        user_id = logged_user.get("id")

        profile_config = self.collection.find_one(
            {"userId": user_id, "projects.projectId": project_id}, {"projects.$": 1}
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
            return self.create_project(
                project_name
            )

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
                "$set": {"projects.$.dateHourUpdated": now, "updatedAt": now},
            },
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

    # ===== MÉTODOS PARA CONTAS FIXAS =====

    def create_fixed_bill(
        self,
        name: str,
        amount: float,
        due_day: int,
        description: str = "",
        category: str = "OTHER",
        autopay: bool = False,
        reminder: bool = True,
    ) -> Dict[str, Any]:
        """Cria uma nova conta fixa"""
        logged_user = g.logged_user
        user_id = logged_user.get("id")

        # Valida o dia de vencimento
        if not 1 <= due_day <= 31:
            raise ValueError("Due day must be between 1 and 31")

        # Busca o profile config
        profile_config = self.collection.find_one({"userId": user_id})

        # Se não existir, cria um novo
        if not profile_config:
            self.create_default_profile_config()
            profile_config = self.collection.find_one({"userId": user_id})

        # Se o array fixedBills não existir, inicializa
        if not profile_config.get("fixedBills"):
            self.collection.update_one(
                {"userId": user_id}, {"$set": {"fixedBills": []}}
            )

        # Cria a nova conta fixa
        new_bill = create_fixed_bill_dict(
            name, amount, due_day, description, category, autopay, reminder
        )

        # Adiciona ao array de contas fixas
        result = self.collection.update_one(
            {"userId": user_id},
            {
                "$push": {"fixedBills": new_bill},
                "$set": {"updatedAt": datetime.now(ZoneInfo("America/Sao_Paulo"))},
            },
        )

        if result.modified_count == 0:
            raise ValueError("Failed to create fixed bill")

        return fixed_bill_to_dto(new_bill)

    def get_fixed_bill_by_id(self, bill_id: str) -> Optional[Dict[str, Any]]:
        """Busca uma conta fixa específica pelo ID"""
        logged_user = g.logged_user
        user_id = logged_user.get("id")

        profile_config = self.collection.find_one(
            {"userId": user_id, "fixedBills.billId": bill_id}, {"fixedBills.$": 1}
        )

        if profile_config and profile_config.get("fixedBills"):
            return profile_config["fixedBills"][0]
        return None

    def mark_bill_as_paid(
        self, bill_id: str, year_month: str, amount: Optional[float] = None
    ) -> bool:
        """Marca uma conta como paga para um mês específico"""
        logged_user = g.logged_user
        user_id = logged_user.get("id")

        # Busca a conta
        bill = self.get_fixed_bill_by_id(bill_id)
        if not bill:
            raise ValueError("Bill not found")

        # Usa o valor da conta se não foi especificado
        if amount is None:
            amount = bill["amount"]

        # Cria o registro de pagamento
        payment_record = create_payment_record(
            bill_id=bill_id,
            amount=amount,
            month=year_month,
            paid_date=datetime.now(ZoneInfo("America/Sao_Paulo")),
        )

        # Remove pagamento anterior do mesmo mês se existir
        self.collection.update_one(
            {"userId": user_id, "fixedBills.billId": bill_id},
            {"$pull": {"fixedBills.$.paymentHistory": {"month": year_month}}},
        )

        # Adiciona o novo registro de pagamento
        result = self.collection.update_one(
            {"userId": user_id, "fixedBills.billId": bill_id},
            {
                "$push": {"fixedBills.$.paymentHistory": payment_record},
                "$set": {
                    "fixedBills.$.updatedAt": datetime.now(
                        ZoneInfo("America/Sao_Paulo")
                    ),
                    "updatedAt": datetime.now(ZoneInfo("America/Sao_Paulo")),
                },
            },
        )

        return result.modified_count > 0

    def mark_bill_as_unpaid(self, bill_id: str, year_month: str) -> bool:
        """Remove o pagamento de uma conta para um mês específico"""
        logged_user = g.logged_user
        user_id = logged_user.get("id")

        # Remove o registro de pagamento
        result = self.collection.update_one(
            {"userId": user_id, "fixedBills.billId": bill_id},
            {
                "$pull": {"fixedBills.$.paymentHistory": {"month": year_month}},
                "$set": {
                    "fixedBills.$.updatedAt": datetime.now(
                        ZoneInfo("America/Sao_Paulo")
                    ),
                    "updatedAt": datetime.now(ZoneInfo("America/Sao_Paulo")),
                },
            },
        )

        return result.modified_count > 0

    def list_fixed_bills(
        self, status: Optional[str] = None, include_payment_status: bool = True
    ) -> List[Dict[str, Any]]:
        """Lista todas as contas fixas do usuário com status de pagamento do mês atual"""
        logged_user = g.logged_user
        user_id = logged_user.get("id")

        profile_config = self.collection.find_one({"userId": user_id})
        if not profile_config:
            return []

        bills = profile_config.get("fixedBills", [])

        # Filtra por status se especificado
        if status:
            bills = [b for b in bills if b.get("status") == status]

        # Adiciona status de pagamento do mês atual se solicitado
        if include_payment_status:
            current_month = datetime.now().strftime("%Y-%m")
            bills_with_status = []

            for bill in bills:
                bill_dto = fixed_bill_to_dto(bill)
                payment_status = get_bill_status_for_month(bill, current_month)
                bill_dto["currentMonthStatus"] = payment_status
                bills_with_status.append(bill_dto)

            return bills_with_status

        return [fixed_bill_to_dto(b) for b in bills]

    def get_fixed_bills_summary(self, year_month: str) -> Dict[str, Any]:
        """Retorna um resumo das contas fixas para um mês específico"""
        bills = self.list_fixed_bills(status="ACTIVE", include_payment_status=False)

        total_amount = 0
        paid_amount = 0
        pending_amount = 0
        bills_status = []

        for bill in bills:
            bill_data = self.get_fixed_bill_by_id(bill["billId"])
            if bill_data:
                status = get_bill_status_for_month(bill_data, year_month)
                amount = bill_data["amount"]

                total_amount += amount

                if status["paid"]:
                    paid_amount += amount
                else:
                    pending_amount += amount

                bills_status.append(
                    {
                        "billId": bill["billId"],
                        "name": bill["name"],
                        "amount": amount,
                        "dueDay": bill["dueDay"],
                        "paid": status["paid"],
                        "paidDate": status["paidDate"],
                    }
                )

        return {
            "month": year_month,
            "totalAmount": total_amount,
            "paidAmount": paid_amount,
            "pendingAmount": pending_amount,
            "paidPercentage": (
                (paid_amount / total_amount * 100) if total_amount > 0 else 0
            ),
            "billsCount": len(bills_status),
            "paidCount": sum(1 for b in bills_status if b["paid"]),
            "bills": sorted(bills_status, key=lambda x: (not x["paid"], x["dueDay"])),
        }
