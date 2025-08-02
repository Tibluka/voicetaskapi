from typing import Dict, Any
from datetime import datetime
from services.spending_service import SpendingService
from services.profile_config_service import ProfileConfigService
from db.mongo import spending_collection, profile_config_collection


class MonthlySummaryService:
    def __init__(self):
        self.spending_service = SpendingService(spending_collection)
        self.profile_config_service = ProfileConfigService(profile_config_collection)

    def get_monthly_summary(self, user_id: str, year_month: str) -> Dict[str, Any]:
        """
        Retorna um resumo completo dos gastos do mês incluindo:
        - Gastos variáveis (spendings)
        - Contas fixas (fixed bills)
        - Total geral
        - Comparação com limite mensal
        """

        # 1. Busca gastos variáveis do mês
        spending_query = {"type": "SPENDING", "date": year_month, "consult": True}

        spendings = self.spending_service.consult_spending(spending_query)
        total_variable_spending = sum(s.get("value", 0) for s in spendings)

        # 2. Busca resumo das contas fixas
        fixed_bills_summary = self.profile_config_service.get_fixed_bills_summary(
            year_month
        )
        total_fixed_bills = fixed_bills_summary.get("totalAmount", 0)
        paid_fixed_bills = fixed_bills_summary.get("paidAmount", 0)

        # 3. Calcula totais
        total_spent = total_variable_spending + paid_fixed_bills
        total_planned = total_variable_spending + total_fixed_bills

        # 4. Busca limite mensal
        profile_config = self.profile_config_service.collection.find_one(
            {"userId": user_id}
        )
        monthly_limit = profile_config.get("monthLimit", 0) if profile_config else 0

        # 5. Calcula percentuais
        percentage_of_limit = (
            (total_spent / monthly_limit * 100) if monthly_limit > 0 else 0
        )
        percentage_planned_of_limit = (
            (total_planned / monthly_limit * 100) if monthly_limit > 0 else 0
        )

        # 6. Agrupa gastos por categoria
        categories_breakdown = {}

        # Adiciona gastos variáveis por categoria
        for spending in spendings:
            category = spending.get("category", "OTHER")
            if category not in categories_breakdown:
                categories_breakdown[category] = {"variable": 0, "fixed": 0, "total": 0}
            categories_breakdown[category]["variable"] += spending.get("value", 0)

        # Adiciona contas fixas por categoria
        for bill in fixed_bills_summary.get("bills", []):
            # Busca a conta completa para pegar a categoria
            bill_data = self.profile_config_service.get_fixed_bill_by_id(bill["billId"])
            if bill_data:
                category = bill_data.get("category", "OTHER")
                if category not in categories_breakdown:
                    categories_breakdown[category] = {
                        "variable": 0,
                        "fixed": 0,
                        "total": 0,
                    }
                categories_breakdown[category]["fixed"] += bill["amount"]

        # Calcula totais por categoria
        for category in categories_breakdown:
            categories_breakdown[category]["total"] = (
                categories_breakdown[category]["variable"]
                + categories_breakdown[category]["fixed"]
            )

        return {
            "month": year_month,
            "monthlyLimit": monthly_limit,
            "totalSpent": total_spent,  # Apenas o que foi efetivamente gasto/pago
            "totalPlanned": total_planned,  # Total incluindo contas fixas não pagas
            "remainingLimit": (
                monthly_limit - total_spent if monthly_limit > 0 else None
            ),
            "percentageOfLimit": round(percentage_of_limit, 2),
            "percentagePlannedOfLimit": round(percentage_planned_of_limit, 2),
            "breakdown": {
                "variableSpending": {
                    "total": total_variable_spending,
                    "count": len(spendings),
                    "percentage": (
                        round((total_variable_spending / total_spent * 100), 2)
                        if total_spent > 0
                        else 0
                    ),
                },
                "fixedBills": {
                    "total": total_fixed_bills,
                    "paid": paid_fixed_bills,
                    "pending": total_fixed_bills - paid_fixed_bills,
                    "count": fixed_bills_summary.get("billsCount", 0),
                    "paidCount": fixed_bills_summary.get("paidCount", 0),
                    "percentage": (
                        round((paid_fixed_bills / total_spent * 100), 2)
                        if total_spent > 0
                        else 0
                    ),
                },
            },
            "categoriesBreakdown": categories_breakdown,
            "alerts": self._generate_alerts(
                total_spent=total_spent,
                total_planned=total_planned,
                monthly_limit=monthly_limit,
                percentage_of_limit=percentage_of_limit,
                fixed_bills_summary=fixed_bills_summary,
            ),
        }

    def _generate_alerts(
        self,
        total_spent: float,
        total_planned: float,
        monthly_limit: float,
        percentage_of_limit: float,
        fixed_bills_summary: Dict[str, Any],
    ) -> list:
        """Gera alertas baseados nos gastos e limites"""
        alerts = []

        # Alerta de limite próximo
        if monthly_limit > 0:
            if percentage_of_limit >= 90:
                alerts.append(
                    {
                        "type": "LIMIT_CRITICAL",
                        "message": f"Você já gastou {percentage_of_limit:.1f}% do seu limite mensal!",
                        "severity": "high",
                    }
                )
            elif percentage_of_limit >= 75:
                alerts.append(
                    {
                        "type": "LIMIT_WARNING",
                        "message": f"Atenção! Você já gastou {percentage_of_limit:.1f}% do seu limite mensal.",
                        "severity": "medium",
                    }
                )

        # Alerta de contas fixas pendentes
        pending_bills = fixed_bills_summary.get(
            "billsCount", 0
        ) - fixed_bills_summary.get("paidCount", 0)
        if pending_bills > 0:
            pending_amount = fixed_bills_summary.get("pendingAmount", 0)
            alerts.append(
                {
                    "type": "PENDING_BILLS",
                    "message": f"Você tem {pending_bills} conta(s) fixa(s) pendente(s) totalizando R$ {pending_amount:.2f}",
                    "severity": "medium",
                }
            )

        # Alerta se o total planejado excede o limite
        if monthly_limit > 0 and total_planned > monthly_limit:
            excess = total_planned - monthly_limit
            alerts.append(
                {
                    "type": "BUDGET_EXCEEDED",
                    "message": f"Seus gastos planejados excedem o limite em R$ {excess:.2f}",
                    "severity": "high",
                }
            )

        return alerts
