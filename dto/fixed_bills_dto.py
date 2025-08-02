from datetime import datetime
from typing import Optional, List, Dict
import uuid


def fixed_bill_to_dto(bill: dict) -> dict:
    """Converte uma conta fixa do banco para DTO"""
    return {
        "billId": bill.get("billId"),
        "name": bill.get("name"),
        "description": bill.get("description", ""),
        "amount": bill.get("amount"),
        "dueDay": bill.get("dueDay"),  # Dia do mês para vencimento (1-31)
        "category": bill.get("category", "OTHER"),
        "status": bill.get("status", "ACTIVE"),  # ACTIVE, PAUSED, CANCELLED
        "autopay": bill.get("autopay", False),  # Se é débito automático
        "reminder": bill.get("reminder", True),  # Se deve lembrar
        "paymentHistory": bill.get("paymentHistory", []),  # Histórico de pagamentos
        "createdAt": (
            bill.get("createdAt").isoformat() if bill.get("createdAt") else None
        ),
        "updatedAt": (
            bill.get("updatedAt").isoformat() if bill.get("updatedAt") else None
        ),
    }


def create_fixed_bill_dict(
    name: str,
    amount: float,
    due_day: int,
    description: str = "",
    category: str = "OTHER",
    autopay: bool = False,
    reminder: bool = True,
) -> dict:
    """Cria um novo dicionário de conta fixa"""
    now = datetime.utcnow()

    return {
        "billId": str(uuid.uuid4()),
        "name": name,
        "description": description,
        "amount": amount,
        "dueDay": due_day,
        "category": category,
        "status": "ACTIVE",
        "autopay": autopay,
        "reminder": reminder,
        "paymentHistory": [],
        "createdAt": now,
        "updatedAt": now,
    }


def create_payment_record(
    bill_id: str, amount: float, month: str, paid_date: Optional[datetime] = None
) -> dict:
    """Cria um registro de pagamento para o histórico"""
    return {
        "paymentId": str(uuid.uuid4()),
        "billId": bill_id,
        "month": month,  # Formato: "2025-06"
        "amount": amount,
        "paid": paid_date is not None,
        "paidDate": paid_date.isoformat() if paid_date else None,
        "createdAt": datetime.utcnow(),
    }


def get_bill_status_for_month(bill: dict, year_month: str) -> dict:
    """Retorna o status de pagamento de uma conta para um mês específico"""
    payment = next(
        (p for p in bill.get("paymentHistory", []) if p.get("month") == year_month),
        None,
    )

    if payment:
        return {
            "paid": payment.get("paid", False),
            "paidDate": payment.get("paidDate"),
            "amount": payment.get("amount"),
        }

    return {"paid": False, "paidDate": None, "amount": bill.get("amount")}
