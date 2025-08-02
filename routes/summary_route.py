from flask import Blueprint, jsonify, g
from utils.auth_decorator import token_required
from services.monthly_summary_service import MonthlySummaryService
from datetime import datetime

summary_bp = Blueprint("summary", __name__)
summary_service = MonthlySummaryService()


@summary_bp.route("/summary/<year_month>", methods=["GET"])
@token_required
def get_monthly_summary(year_month):
    """
    Obtém resumo completo dos gastos do mês incluindo gastos variáveis e contas fixas

    Formato do year_month: YYYY-MM (ex: 2025-06)
    """
    try:
        # Valida formato do mês
        try:
            datetime.strptime(year_month, "%Y-%m")
        except ValueError:
            return jsonify({"error": "Invalid yearMonth format. Use YYYY-MM"}), 400

        user_id = g.logged_user.get("id")
        summary = summary_service.get_monthly_summary(user_id, year_month)

        return jsonify(summary), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@summary_bp.route("/summary/current", methods=["GET"])
@token_required
def get_current_month_summary():
    """Obtém resumo do mês atual"""
    try:
        current_month = datetime.now().strftime("%Y-%m")
        user_id = g.logged_user.get("id")

        summary = summary_service.get_monthly_summary(user_id, current_month)

        return jsonify(summary), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
