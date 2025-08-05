# websocket_server.py
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask import request
from functools import wraps
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from db.mongo import profile_config_collection
from services.profile_config_service import ProfileConfigService
from utils.auth_decorator import decode_token
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar SocketIO (será configurado no api.py)
socketio = None

# Dicionário para armazenar conexões ativas
active_connections = {}

# Scheduler para tarefas agendadas
scheduler = BackgroundScheduler()
scheduler.start()


def init_socketio(app):
    """Inicializa o SocketIO com a aplicação Flask"""
    global socketio
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

    # Registrar event handlers
    socketio.on_event("connect", handle_connect)
    socketio.on_event("disconnect", handle_disconnect)
    socketio.on_event("authenticate", handle_authenticate)
    socketio.on_event("subscribe_notifications", handle_subscribe)
    socketio.on_event("unsubscribe_notifications", handle_unsubscribe)

    # Agendar verificação de lembretes
    scheduler.add_job(
        func=check_and_send_reminders,
        trigger="interval",
        hours=1,  # Verifica a cada hora
        id="check_reminders",
        replace_existing=True,
    )

    return socketio


def require_auth(f):
    """Decorator para verificar autenticação em eventos do WebSocket"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.sid not in active_connections:
            emit("error", {"message": "Not authenticated"})
            return False
        return f(*args, **kwargs)

    return decorated_function


def handle_connect():
    """Manipula nova conexão WebSocket"""
    logger.info(f"Client connected: {request.sid}")
    emit("connected", {"message": "Connected to notification service"})


def handle_disconnect():
    """Manipula desconexão WebSocket"""
    if request.sid in active_connections:
        user_id = active_connections[request.sid]["user_id"]
        leave_room(f"user_{user_id}")
        del active_connections[request.sid]
        logger.info(f"Client disconnected: {request.sid}")


def handle_authenticate(data):
    """Autentica o usuário via token JWT"""
    token = data.get("token")
    if not token:
        emit("auth_error", {"message": "Token required"})
        return

    try:
        # Decodificar token
        payload = decode_token(token)
        user_id = payload.get("user_id")

        # Armazenar conexão
        active_connections[request.sid] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow(),
        }

        # Adicionar usuário à sala específica
        join_room(f"user_{user_id}")

        emit("authenticated", {"message": "Authentication successful"})
        logger.info(f"User {user_id} authenticated on connection {request.sid}")

    except Exception as e:
        emit("auth_error", {"message": str(e)})
        logger.error(f"Authentication error: {e}")


@require_auth
def handle_subscribe(data):
    """Inscreve o usuário em notificações específicas"""
    notification_type = data.get("type", "all")
    user_data = active_connections[request.sid]

    if "subscriptions" not in user_data:
        user_data["subscriptions"] = set()

    user_data["subscriptions"].add(notification_type)
    emit("subscribed", {"type": notification_type})


@require_auth
def handle_unsubscribe(data):
    """Remove inscrição de notificações"""
    notification_type = data.get("type")
    user_data = active_connections[request.sid]

    if "subscriptions" in user_data and notification_type in user_data["subscriptions"]:
        user_data["subscriptions"].remove(notification_type)
        emit("unsubscribed", {"type": notification_type})


def send_notification_to_user(user_id, notification):
    """Envia notificação para um usuário específico"""
    if socketio:
        socketio.emit("notification", notification, room=f"user_{user_id}")
        logger.info(f"Notification sent to user {user_id}: {notification['type']}")


def check_and_send_reminders():
    """Verifica e envia lembretes de contas fixas"""
    try:
        profile_service = ProfileConfigService(profile_config_collection)
        current_date = datetime.now()
        current_day = current_date.day

        # Buscar todos os usuários com contas fixas ativas
        configs = profile_config_collection.find(
            {"fixedBills": {"$exists": True, "$ne": []}}
        )

        for config in configs:
            user_id = config.get("userId")
            bills = config.get("fixedBills", [])

            for bill in bills:
                # Verificar apenas contas ativas com lembrete habilitado
                if bill.get("status") != "ACTIVE" or not bill.get("reminder", True):
                    continue

                due_day = bill.get("dueDay")
                bill_name = bill.get("name")
                amount = bill.get("amount")

                # Verificar se a conta já foi paga este mês
                year_month = current_date.strftime("%Y-%m")
                payment_status = profile_service.get_bill_status_for_month(
                    bill, year_month
                )

                if payment_status.get("paid"):
                    continue

                # Enviar lembretes em diferentes momentos
                days_until_due = calculate_days_until_due(current_day, due_day)

                # Lembrete 3 dias antes
                if days_until_due == 3:
                    send_notification_to_user(
                        user_id,
                        {
                            "type": "BILL_REMINDER",
                            "title": "Conta a vencer em 3 dias",
                            "message": f'A conta "{bill_name}" de R$ {amount:.2f} vence em 3 dias (dia {due_day})',
                            "billId": bill.get("billId"),
                            "daysUntilDue": 3,
                            "severity": "medium",
                        },
                    )

                # Lembrete no dia do vencimento
                elif days_until_due == 0:
                    send_notification_to_user(
                        user_id,
                        {
                            "type": "BILL_DUE_TODAY",
                            "title": "Conta vence hoje!",
                            "message": f'A conta "{bill_name}" de R$ {amount:.2f} vence hoje!',
                            "billId": bill.get("billId"),
                            "daysUntilDue": 0,
                            "severity": "high",
                        },
                    )

                # Lembrete de atraso
                elif days_until_due < 0 and days_until_due >= -3:
                    send_notification_to_user(
                        user_id,
                        {
                            "type": "BILL_OVERDUE",
                            "title": "Conta em atraso!",
                            "message": f'A conta "{bill_name}" de R$ {amount:.2f} está {abs(days_until_due)} dia(s) em atraso',
                            "billId": bill.get("billId"),
                            "daysOverdue": abs(days_until_due),
                            "severity": "critical",
                        },
                    )

    except Exception as e:
        logger.error(f"Error checking reminders: {e}")


def calculate_days_until_due(current_day, due_day):
    """Calcula quantos dias faltam para o vencimento"""
    if due_day >= current_day:
        return due_day - current_day
    else:
        # Conta já venceu este mês
        return due_day - current_day


def send_custom_notification(user_id, notification_type, title, message, data=None):
    """Envia notificação customizada para um usuário"""
    notification = {
        "type": notification_type,
        "title": title,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data or {},
    }
    send_notification_to_user(user_id, notification)


# Funções auxiliares para enviar notificações específicas


def notify_spending_limit_reached(user_id, current_spending, limit):
    """Notifica quando o limite de gastos é atingido"""
    percentage = (current_spending / limit) * 100
    send_custom_notification(
        user_id,
        "SPENDING_LIMIT_WARNING",
        "Limite de gastos atingido!",
        f"Você já gastou R$ {current_spending:.2f} ({percentage:.1f}%) do seu limite de R$ {limit:.2f}",
        {"currentSpending": current_spending, "limit": limit, "percentage": percentage},
    )


def notify_project_milestone(user_id, project_name, current_value, target_value):
    """Notifica marcos em projetos"""
    percentage = (current_value / target_value) * 100

    if percentage >= 100:
        title = "Meta do projeto atingida! 🎉"
        message = f'Parabéns! Você atingiu a meta de R$ {target_value:.2f} para o projeto "{project_name}"'
    elif percentage >= 75:
        title = "Projeto quase completo!"
        message = f'O projeto "{project_name}" está {percentage:.1f}% completo'
    elif percentage >= 50:
        title = "Meio caminho andado!"
        message = f'O projeto "{project_name}" atingiu 50% da meta'
    else:
        return

    send_custom_notification(
        user_id,
        "PROJECT_MILESTONE",
        title,
        message,
        {
            "projectName": project_name,
            "currentValue": current_value,
            "targetValue": target_value,
            "percentage": percentage,
        },
    )
