# routes/notifications_route.py
from flask import Blueprint, request, jsonify, g
from utils.auth_decorator import token_required
from websocket_server import (
    send_custom_notification,
    notify_spending_limit_reached,
    notify_project_milestone,
    check_and_send_reminders,
)
from services.profile_config_service import ProfileConfigService
from db.mongo import profile_config_collection

notifications_bp = Blueprint("notifications", __name__)
profile_config_service = ProfileConfigService(profile_config_collection)


@notifications_bp.route("/notifications/test", methods=["POST"])
@token_required
def test_notification():
    """Envia uma notificação de teste para o usuário"""
    try:
        data = request.get_json()
        user_id = g.logged_user.get("id")

        title = data.get("title", "Notificação de Teste")
        message = data.get("message", "Esta é uma notificação de teste do VoiceTask")

        send_custom_notification(user_id, "TEST_NOTIFICATION", title, message)

        return (
            jsonify(
                {"message": "Test notification sent successfully", "userId": user_id}
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@notifications_bp.route("/notifications/check-reminders", methods=["POST"])
@token_required
def trigger_reminder_check():
    """Força uma verificação imediata de lembretes (útil para testes)"""
    try:
        check_and_send_reminders()
        return jsonify({"message": "Reminder check triggered successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@notifications_bp.route("/notifications/spending-alert", methods=["POST"])
@token_required
def send_spending_alert():
    """Envia alerta de limite de gastos"""
    try:
        user_id = g.logged_user.get("id")

        # Buscar configuração do usuário
        config = profile_config_service.collection.find_one({"userId": user_id})
        if not config:
            return jsonify({"error": "User configuration not found"}), 404

        monthly_limit = config.get("monthlyLimit", 0)
        if monthly_limit <= 0:
            return jsonify({"error": "No monthly limit set"}), 400

        # Aqui você pode calcular os gastos reais do mês atual
        # Por enquanto, vamos usar um valor de exemplo
        data = request.get_json()
        current_spending = data.get("currentSpending", 0)

        notify_spending_limit_reached(user_id, current_spending, monthly_limit)

        return (
            jsonify(
                {
                    "message": "Spending alert sent successfully",
                    "currentSpending": current_spending,
                    "limit": monthly_limit,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@notifications_bp.route("/notifications/settings", methods=["GET"])
@token_required
def get_notification_settings():
    """Obtém configurações de notificação do usuário"""
    try:
        user_id = g.logged_user.get("id")
        config = profile_config_service.collection.find_one({"userId": user_id})

        if not config:
            return jsonify({"error": "User configuration not found"}), 404

        # Extrair configurações de notificação
        notification_settings = {
            "billReminders": True,  # Por padrão, sempre ativo
            "spendingAlerts": config.get("enableSpendingAlerts", True),
            "projectMilestones": config.get("enableProjectAlerts", True),
            "reminderDays": config.get(
                "reminderDays", [3, 0, -1]
            ),  # 3 dias antes, no dia, 1 dia após
        }

        return jsonify(notification_settings), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@notifications_bp.route("/notifications/settings", methods=["PUT"])
@token_required
def update_notification_settings():
    """Atualiza configurações de notificação do usuário"""
    try:
        user_id = g.logged_user.get("id")
        data = request.get_json()

        update_fields = {}

        if "spendingAlerts" in data:
            update_fields["enableSpendingAlerts"] = bool(data["spendingAlerts"])

        if "projectMilestones" in data:
            update_fields["enableProjectAlerts"] = bool(data["projectMilestones"])

        if "reminderDays" in data:
            # Validar que são números
            reminder_days = data["reminderDays"]
            if not isinstance(reminder_days, list) or not all(
                isinstance(d, int) for d in reminder_days
            ):
                return (
                    jsonify({"error": "reminderDays must be a list of integers"}),
                    400,
                )
            update_fields["reminderDays"] = reminder_days

        if update_fields:
            profile_config_service.collection.update_one(
                {"userId": user_id}, {"$set": update_fields}
            )

        return (
            jsonify(
                {
                    "message": "Notification settings updated successfully",
                    "settings": update_fields,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
