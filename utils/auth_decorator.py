from functools import wraps
from flask import request, jsonify, g
from services.token_service import TokenService  # importe seu serviço aqui


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]

        if not token:
            return jsonify({"error": "Token is missing!"}), 401

        try:
            decoded_payload = TokenService.verify_token(token)
            g.logged_user = decoded_payload.get("user")
            if g.logged_user is None:
                return jsonify({"error": "User ID not found in token"}), 401
        except ValueError as e:
            return jsonify({"error": str(e)}), 401

        return f(*args, **kwargs)

    return decorated
