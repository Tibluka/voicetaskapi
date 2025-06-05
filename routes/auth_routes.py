from flask import Blueprint, request, jsonify
from services.auth_service import AuthService
from services.token_service import TokenService
from db.mongo import user_collection

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

    token = TokenService.generate_token({"email": user["email"]})

    return jsonify({
        "message": "Login successful",
        "token": token
    })
    
    
@auth_bp.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        result = auth_service.create_user(email, password)
        return jsonify(result), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400