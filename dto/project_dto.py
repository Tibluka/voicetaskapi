from datetime import datetime
from typing import Optional


def project_to_dto(project: dict) -> dict:
    """Converte um projeto do banco para DTO"""
    return {
        "projectId": project.get("projectId"),
        "projectName": project.get("projectName"),
        "totalValueRegistered": project.get("totalValueRegistered", 0),
        "description": project.get("description", ""),
        "status": project.get("status", "ACTIVE"),  # ACTIVE, COMPLETED, PAUSED
        "targetValue": project.get("targetValue"),  # Meta de valor total do projeto
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
    import uuid

    now = datetime.utcnow()

    return {
        "projectId": str(uuid.uuid4()),
        "projectName": name,
        "description": description,
        "totalValueRegistered": 0,
        "targetValue": target_value,
        "status": "ACTIVE",
        "dateHourCreated": now,
        "dateHourUpdated": now,
        "completedAt": None,
    }
