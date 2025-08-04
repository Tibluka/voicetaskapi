from flask import Blueprint, jsonify, g
from utils.auth_decorator import token_required
from services.spending_service import SpendingService
from db.mongo import spending_collection
from datetime import datetime

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


@spending_bp.route("/spendings/month/<string:user_id>", methods=["GET"])
@token_required
def list_spendings_current_month(user_id):
    try:
        now = datetime.now()
        current_month = now.strftime("%Y-%m")
        date_prefix = current_month  # e.g., "2024-06"

        # Busca todos os registros do usuário no mês atual, sem projectId
        spendings = list(spending_service.collection.find({
            "userId": user_id,
            "projectId": {"$exists": False},
            "date": {"$regex": f"^{date_prefix}"}
        }))

        total_spent = 0.0
        predicted_total = 0.0

        for spending in spendings:
            installments = spending.get("installments", 0)
            is_parent = spending.get("is_parent", False)
            # Se for registro pai OU não houver installments, conta em totalSpent
            if is_parent or not installments:
                total_spent += spending.get("value", 0.0)
            # predictedTotal sempre soma todos os registros do mês
            predicted_total += spending.get("value", 0.0)

        return jsonify({
            "totalSpent": total_spent,
            "predictedTotal": predicted_total
        }), 200
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500