from datetime import datetime
from typing import Optional, Dict, Any
import uuid


def project_to_dto(project: dict) -> dict:
    """Converte um projeto do banco para DTO"""
    return {
        "projectId": project.get("projectId"),
        "projectName": project.get("projectName"),
        "totalValueRegistered": project.get("totalValueRegistered", 0),
        "description": project.get("description", ""),
        "status": project.get("status", "ACTIVE"),  # ACTIVE, COMPLETED, PAUSED
        "targetValue": project.get("targetValue"),  # Meta de valor total do projeto
        "expenseHistory": project.get(
            "expenseHistory", []
        ),  # Histórico detalhado de gastos
        "dateHourCreated": (
            project.get("dateHourCreated").isoformat()
            if project.get("dateHourCreated")
            else None
        ),
        "dateHourUpdated": (
            project.get("dateHourUpdated").isoformat()
            if project.get("dateHourUpdated")
            else None
        ),
        "completedAt": (
            project.get("completedAt").isoformat()
            if project.get("completedAt")
            else None
        ),
    }


def create_project_dict(
    name: str, description: str = "", target_value: Optional[float] = None
) -> dict:
    """Cria um novo dicionário de projeto"""
    now = datetime.utcnow()

    return {
        "projectId": str(uuid.uuid4()),
        "projectName": name,
        "description": description,
        "totalValueRegistered": 0,
        "targetValue": target_value,
        "status": "ACTIVE",
        "expenseHistory": [],  # Inicializa histórico vazio
        "dateHourCreated": now,
        "dateHourUpdated": now,
        "completedAt": None,
    }


def create_expense_history_item(
    spending_id: str,
    value: float,
    description: str,
    category: str,
    date: str,
    installments: int = 1,
    installment_info: str = "1/1",
) -> Dict[str, Any]:
    """Cria um item do histórico de gastos para o projeto"""
    return {
        "expenseId": str(uuid.uuid4()),
        "spendingId": spending_id,  # Referência ao documento na collection spending
        "value": value,
        "description": description,
        "category": category,
        "date": date,
        "installments": installments,
        "installmentInfo": installment_info,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    }


def expense_history_item_to_dto(expense_item: Dict[str, Any]) -> Dict[str, Any]:
    """Converte um item do histórico de gastos para DTO"""
    return {
        "expenseId": expense_item.get("expenseId"),
        "spendingId": expense_item.get("spendingId"),
        "value": expense_item.get("value", 0),
        "description": expense_item.get("description", ""),
        "category": expense_item.get("category", ""),
        "date": expense_item.get("date"),
        "installments": expense_item.get("installments", 1),
        "installmentInfo": expense_item.get("installmentInfo", "1/1"),
        "createdAt": (
            expense_item.get("createdAt").isoformat()
            if expense_item.get("createdAt")
            else None
        ),
        "updatedAt": (
            expense_item.get("updatedAt").isoformat()
            if expense_item.get("updatedAt")
            else None
        ),
    }
