from flask import Blueprint, jsonify, g
from utils.auth_decorator import token_required
from services.spending_service import SpendingService
from db.mongo import spending_collection

spending_bp = Blueprint("spendings", __name__)
spending_service = SpendingService(spending_collection)


@spending_bp.route("/spendings/DELETE/<string:spending_id>", methods=["DELETE"])
@token_required
def delete_spending(spending_id):
    try:
        result = spending_service.remove_spending(spending_id)
        return jsonify(result), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500
