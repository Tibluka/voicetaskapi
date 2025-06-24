from bson import ObjectId
from flask import Blueprint, request, jsonify, g, render_template_string
from services.auth_service import AuthService
from services.token_service import TokenService
from db.mongo import user_collection, password_resets
from dto.user_dto import user_to_dto
from utils.auth_decorator import token_required

auth_bp = Blueprint("auth", __name__)
auth_service = AuthService(user_collection, password_resets)

@auth_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        user = auth_service.authenticate(email, password)
    except ValueError as e:
        if str(e) == "Usuário está pendente de ativação.":
            return jsonify({"error": str(e)}), 403
        return jsonify({"error": str(e)}), 400

    if not user:
        return jsonify({"error": "Invalid email or password"}), 401

    token = TokenService.generate_token({"user": user_to_dto(user)})

    return jsonify({
        "message": "Login successful",
        "token": token
    })
    
    
@auth_bp.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    name = data.get("name")
    phone = data.get("phone")

    if not email or not password or not name or not phone:
        return jsonify({"error": "Email, password, name and phone are required"}), 400

    try:
        result = auth_service.create_user(email, password, name, phone)
        return jsonify(result), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
    
@auth_bp.route("/auth/me", methods=["GET"])
@token_required
def get_current_user():
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Authorization header missing or invalid"}), 401

    token = auth_header.split(" ", 1)[1]

    try:
        payload = TokenService.verify_token(token)          # ajuste o método se o nome for diferente
        user_payload = payload.get("user")

        if not user_payload:
            return jsonify({"error": "Invalid token payload"}), 401

        user_db = user_collection.find_one({"_id": ObjectId(user_payload["id"])})
        if not user_db:
            return jsonify({"error": "User not found"}), 404

        return jsonify(user_to_dto(user_db)), 200

    except Exception as e:
        return jsonify({"error": "Authentication failed"}), 401
    
@auth_bp.route("/auth/change-password", methods=["POST"])
@token_required
def change_password():
    data = request.get_json()
    current_password = data.get("currentPassword")
    new_password = data.get("newPassword")

    if not current_password or not new_password:
        return jsonify({"error": "Current and new passwords are required."}), 400

    try:
        user_id = g.logged_user.get("id")
        result = auth_service.change_user_password(user_id, current_password, new_password)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Failed to change password."}), 500
    
@auth_bp.route("/auth/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json()
    email = data.get("email")

    force_send = request.args.get('force', 'false').lower() == 'true'

    if not email:
        return jsonify({"error": "Email é obrigatório."}), 400

    try:
        result = auth_service.initiate_reset(email, force_send)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/auth/validate-reset-code", methods=["POST"])
def validate_reset_code():
    data = request.get_json()
    email = data.get("email")
    code = data.get("code")

    if not email or not code:
        return jsonify({"error": "Email e code são obrigatórios."}), 400

    try:
        auth_service.validate_token(email, code)
        return jsonify({"message": "Código válido."}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Erro ao validar token."}), 500


@auth_bp.route("/auth/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json()
    email = data.get("email")
    code = data.get("code")
    new_password = data.get("newPassword")

    if not email or not code or not new_password:
        return jsonify({"error": "Email, code e nova senha são obrigatórios."}), 400

    try:
        result = auth_service.reset_password(email, code, new_password)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Erro ao resetar senha."}), 500

@auth_bp.route("/auth/activate", methods=["GET"])
def activate_account():
    email = request.args.get("email")
    code = request.args.get("code")

    if not email or not code:
        return render_template_string("<h2>Erro: Email e código são obrigatórios.</h2>"), 400

    try:
        pr = auth_service.validate_token(email, code)
        # Ativa o usuário
        user_collection.update_one(
            {"_id": pr["userId"]},
            {"$set": {"status": "ACTIVE"}}
        )
        # Marca o token como usado
        auth_service.password_resets.update_one(
            {"_id": pr["_id"]},
            {"$set": {"used": True}}
        )
        return render_template_string("""
            <html>
            <head><title>Conta ativada</title></head>
            <body style='font-family:sans-serif;text-align:center;margin-top:10%'>
                <h1>Conta ativada com sucesso!</h1>
                <p>Você já pode fazer login normalmente.</p>
            </body>
            </html>
        """), 200
    except ValueError as e:
        return render_template_string(f"<h2>Erro: {str(e)}</h2>"), 400
    except Exception as e:
        return render_template_string("<h2>Erro ao ativar conta.</h2>"), 500