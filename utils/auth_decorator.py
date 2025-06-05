from functools import wraps
from flask import request, jsonify
from services.token_service import TokenService

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[-1]

        if not token:
            return jsonify({"error": "Token is missing"}), 401

        try:
            data = TokenService.verify_token(token)
            request.user = data  # você pode acessar o usuário depois via request.user
        except ValueError as e:
            return jsonify({"error": str(e)}), 401

        return f(*args, **kwargs)

    return decorated