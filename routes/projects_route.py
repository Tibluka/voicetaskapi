from flask import Blueprint, request, jsonify, g
from utils.auth_decorator import token_required
from services.profile_config_service import ProfileConfigService
from services.spending_service import SpendingService
from db.mongo import profile_config_collection, spending_collection
from utils.convert_utils import convert_object_ids

projects_bp = Blueprint("projects", __name__)
profile_config_service = ProfileConfigService(profile_config_collection)
spending_service = SpendingService(spending_collection)


@projects_bp.route("/projects", methods=["GET"])
@token_required
def list_projects():
    """Lista todos os projetos do usuário"""
    try:
        status_filter = request.args.get("status")  # ACTIVE, COMPLETED, PAUSED
        projects = profile_config_service.list_user_projects(status_filter)
        return jsonify({"projects": projects}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@projects_bp.route("/projects", methods=["POST"])
@token_required
def create_project():
    """Cria um novo projeto"""
    try:
        data = request.get_json()
        project_name = data.get("projectName")
        description = data.get("description", "")
        target_value = data.get("targetValue")

        if not project_name:
            return jsonify({"error": "Project name is required"}), 400

        # Verifica se já existe um projeto com esse nome
        existing = profile_config_service.get_project_by_name(project_name)
        if existing:
            return jsonify({"error": f"Project '{project_name}' already exists"}), 400

        project = profile_config_service.create_project(
            name=project_name, description=description, target_value=target_value
        )

        return (
            jsonify(
                {
                    "message": f"Project '{project_name}' created successfully",
                    "project": project,
                }
            ),
            201,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@projects_bp.route("/projects/<project_id>", methods=["GET"])
@token_required
def get_project_details(project_id):
    """Obtém detalhes de um projeto específico incluindo gastos"""
    try:
        # Busca o projeto
        project = profile_config_service.get_project_by_id(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        # Busca os gastos do projeto
        query_data = {"type": "SPENDING", "projectId": project_id, "consult": True}

        spendings = spending_service.consult_spending(query_data)

        # Calcula estatísticas
        total_spent = sum(s.get("value", 0) for s in spendings)
        spending_count = len(spendings)

        # Agrupa por categoria
        category_breakdown = {}
        for spending in spendings:
            category = spending.get("category", "OTHER")
            if category not in category_breakdown:
                category_breakdown[category] = 0
            category_breakdown[category] += spending.get("value", 0)

        response = {
            "project": convert_object_ids(project),
            "statistics": {
                "totalSpent": total_spent,
                "spendingCount": spending_count,
                "categoryBreakdown": category_breakdown,
                "targetValue": project.get("targetValue"),
                "percentageComplete": (
                    (total_spent / project["targetValue"] * 100)
                    if project.get("targetValue") and project["targetValue"] > 0
                    else None
                ),
            },
            "recentSpendings": convert_object_ids(spendings[:10]),  # Últimos 10 gastos
        }

        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@projects_bp.route("/projects/<project_id>", methods=["PUT"])
@token_required
def update_project(project_id):
    """Atualiza informações de um projeto"""
    try:
        data = request.get_json()
        logged_user = g.logged_user
        user_id = logged_user.get("id")

        # Campos que podem ser atualizados
        update_fields = {}

        if "projectName" in data:
            # Verifica se o novo nome já existe em outro projeto
            existing = profile_config_service.get_project_by_name(data["projectName"])
            if existing and existing["projectId"] != project_id:
                return jsonify({"error": "Project name already exists"}), 400
            update_fields["projects.$.projectName"] = data["projectName"]

        if "description" in data:
            update_fields["projects.$.description"] = data["description"]

        if "targetValue" in data:
            update_fields["projects.$.targetValue"] = float(data["targetValue"])

        if "status" in data:
            if data["status"] not in ["ACTIVE", "COMPLETED", "PAUSED"]:
                return jsonify({"error": "Invalid status"}), 400
            update_fields["projects.$.status"] = data["status"]

            # Se estiver marcando como concluído, adiciona data de conclusão
            if data["status"] == "COMPLETED":
                from datetime import datetime
                from zoneinfo import ZoneInfo

                update_fields["projects.$.completedAt"] = datetime.now(
                    ZoneInfo("America/Sao_Paulo")
                )

        if not update_fields:
            return jsonify({"error": "No fields to update"}), 400

        # Adiciona campo de atualização
        from datetime import datetime
        from zoneinfo import ZoneInfo

        update_fields["projects.$.dateHourUpdated"] = datetime.now(
            ZoneInfo("America/Sao_Paulo")
        )

        # Atualiza o projeto
        result = profile_config_service.collection.update_one(
            {"userId": user_id, "projects.projectId": project_id},
            {"$set": update_fields},
        )

        if result.modified_count == 0:
            return jsonify({"error": "Project not found or no changes made"}), 404

        # Busca o projeto atualizado
        updated_project = profile_config_service.get_project_by_id(project_id)

        return (
            jsonify(
                {
                    "message": "Project updated successfully",
                    "project": convert_object_ids(updated_project),
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@projects_bp.route("/projects/<project_id>", methods=["DELETE"])
@token_required
def delete_project(project_id):
    """Remove um projeto (não remove os gastos associados)"""
    try:
        logged_user = g.logged_user
        user_id = logged_user.get("id")

        # Verifica se o projeto existe
        project = profile_config_service.get_project_by_id(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        # Remove o projeto do array
        result = profile_config_service.collection.update_one(
            {"userId": user_id}, {"$pull": {"projects": {"projectId": project_id}}}
        )

        if result.modified_count == 0:
            return jsonify({"error": "Failed to delete project"}), 500

        return (
            jsonify(
                {
                    "message": f"Project '{project['projectName']}' deleted successfully",
                    "note": "Associated spendings were not deleted and remain in your history",
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
