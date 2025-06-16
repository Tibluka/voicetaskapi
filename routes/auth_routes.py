from bson import ObjectId
from flask import Blueprint, request, jsonify
from services.auth_service import AuthService
from services.token_service import TokenService
from db.mongo import user_collection
from dto.user_dto import user_to_dto
from utils.auth_decorator import token_required

auth_bp = Blueprint("auth", __name__)
auth_service = AuthService(user_collection)

@auth_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = auth_service.authenticate(email, password)
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

    except TokenService.ExpiredTokenError:
        return jsonify({"error": "Token expired"}), 401
    except TokenService.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"error": "Authentication failed"}), 401