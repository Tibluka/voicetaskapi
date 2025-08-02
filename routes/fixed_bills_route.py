from flask import Blueprint, request, jsonify, g
from utils.auth_decorator import token_required
from services.profile_config_service import ProfileConfigService
from db.mongo import profile_config_collection
from utils.convert_utils import convert_object_ids
from datetime import datetime

fixed_bills_bp = Blueprint("fixed_bills", __name__)
profile_config_service = ProfileConfigService(profile_config_collection)


@fixed_bills_bp.route("/fixed-bills", methods=["GET"])
@token_required
def list_fixed_bills():
    """Lista todas as contas fixas com status de pagamento do mês atual"""
    try:
        status_filter = request.args.get("status")  # ACTIVE, PAUSED, CANCELLED
        include_payment = request.args.get("include_payment", "true").lower() == "true"

        bills = profile_config_service.list_fixed_bills(
            status=status_filter, include_payment_status=include_payment
        )

        return jsonify({"bills": convert_object_ids(bills)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@fixed_bills_bp.route("/fixed-bills", methods=["POST"])
@token_required
def create_fixed_bill():
    """Cria uma nova conta fixa"""
    try:
        data = request.get_json()

        # Debug
        print(f"[DEBUG] Creating fixed bill with data: {data}")
        print(f"[DEBUG] User ID: {g.logged_user.get('id')}")

        # Validações
        required_fields = ["name", "amount", "dueDay", "category"]
        missing = [field for field in required_fields if not data.get(field)]
        if missing:
            return (
                jsonify({"error": f"Missing required fields: {', '.join(missing)}"}),
                400,
            )

        bill = profile_config_service.create_fixed_bill(
            name=data["name"],
            amount=float(data["amount"]),
            due_day=int(data["dueDay"]),
            description=data.get("description", ""),
            category=data.get("category", "OTHER"),
            autopay=data.get("autopay", False),
            reminder=data.get("reminder", True),
        )

        # Debug - verifica se foi salvo
        user_id = g.logged_user.get("id")
        config = profile_config_service.collection.find_one({"userId": user_id})
        print(
            f"[DEBUG] Config after creation: {config.get('fixedBills') if config else 'No config found'}"
        )

        return (
            jsonify(
                {
                    "message": f"Fixed bill '{data['name']}' created successfully",
                    "bill": convert_object_ids(bill),
                }
            ),
            201,
        )

    except ValueError as ve:
        print(f"[DEBUG] ValueError: {ve}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        print(f"[DEBUG] Exception: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@fixed_bills_bp.route("/fixed-bills/<bill_id>", methods=["GET"])
@token_required
def get_fixed_bill(bill_id):
    """Obtém detalhes de uma conta fixa específica"""
    try:
        bill = profile_config_service.get_fixed_bill_by_id(bill_id)
        if not bill:
            return jsonify({"error": "Bill not found"}), 404

        # Adiciona status de pagamento dos últimos 6 meses
        current_date = datetime.now()
        payment_history = []

        for i in range(6):
            month_date = datetime(current_date.year, current_date.month, 1)
            # Volta i meses
            for _ in range(i):
                if month_date.month == 1:
                    month_date = month_date.replace(year=month_date.year - 1, month=12)
                else:
                    month_date = month_date.replace(month=month_date.month - 1)

            year_month = month_date.strftime("%Y-%m")
            status = profile_config_service.get_bill_status_for_month(bill, year_month)

            payment_history.append(
                {
                    "month": year_month,
                    "monthName": month_date.strftime("%B %Y"),
                    **status,
                }
            )

        response = {"bill": convert_object_ids(bill), "paymentHistory": payment_history}

        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@fixed_bills_bp.route("/fixed-bills/<bill_id>/pay", methods=["POST"])
@token_required
def pay_fixed_bill(bill_id):
    """Marca uma conta como paga para um mês específico"""
    try:
        data = request.get_json()
        year_month = data.get("yearMonth")  # Formato: "2025-06"
        amount = data.get(
            "amount"
        )  # Opcional, usa o valor padrão da conta se não informado

        if not year_month:
            return jsonify({"error": "yearMonth is required (format: YYYY-MM)"}), 400

        # Valida formato do mês
        try:
            datetime.strptime(year_month, "%Y-%m")
        except ValueError:
            return jsonify({"error": "Invalid yearMonth format. Use YYYY-MM"}), 400

        success = profile_config_service.mark_bill_as_paid(
            bill_id=bill_id,
            year_month=year_month,
            amount=float(amount) if amount else None,
        )

        if success:
            return (
                jsonify(
                    {
                        "message": f"Bill marked as paid for {year_month}",
                        "billId": bill_id,
                        "yearMonth": year_month,
                    }
                ),
                200,
            )
        else:
            return jsonify({"error": "Failed to update payment status"}), 500

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@fixed_bills_bp.route("/fixed-bills/<bill_id>/unpay", methods=["POST"])
@token_required
def unpay_fixed_bill(bill_id):
    """Remove o pagamento de uma conta para um mês específico"""
    try:
        data = request.get_json()
        year_month = data.get("yearMonth")

        if not year_month:
            return jsonify({"error": "yearMonth is required (format: YYYY-MM)"}), 400

        success = profile_config_service.mark_bill_as_unpaid(
            bill_id=bill_id, year_month=year_month
        )

        if success:
            return (
                jsonify(
                    {
                        "message": f"Payment removed for {year_month}",
                        "billId": bill_id,
                        "yearMonth": year_month,
                    }
                ),
                200,
            )
        else:
            return jsonify({"error": "Failed to update payment status"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@fixed_bills_bp.route("/fixed-bills/summary/<year_month>", methods=["GET"])
@token_required
def get_fixed_bills_summary(year_month):
    """Obtém resumo das contas fixas para um mês específico"""
    try:
        # Valida formato do mês
        try:
            datetime.strptime(year_month, "%Y-%m")
        except ValueError:
            return jsonify({"error": "Invalid yearMonth format. Use YYYY-MM"}), 400

        summary = profile_config_service.get_fixed_bills_summary(year_month)
        return jsonify(summary), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@fixed_bills_bp.route("/fixed-bills/<bill_id>", methods=["PUT"])
@token_required
def update_fixed_bill(bill_id):
    """Atualiza uma conta fixa"""
    try:
        data = request.get_json()
        logged_user = g.logged_user
        user_id = logged_user.get("id")

        # Campos que podem ser atualizados
        update_fields = {}

        if "name" in data:
            update_fields["fixedBills.$.name"] = data["name"]

        if "amount" in data:
            update_fields["fixedBills.$.amount"] = float(data["amount"])

        if "dueDay" in data:
            due_day = int(data["dueDay"])
            if not 1 <= due_day <= 31:
                return jsonify({"error": "Due day must be between 1 and 31"}), 400
            update_fields["fixedBills.$.dueDay"] = due_day

        if "description" in data:
            update_fields["fixedBills.$.description"] = data["description"]

        if "category" in data:
            update_fields["fixedBills.$.category"] = data["category"]

        if "autopay" in data:
            update_fields["fixedBills.$.autopay"] = bool(data["autopay"])

        if "reminder" in data:
            update_fields["fixedBills.$.reminder"] = bool(data["reminder"])

        if "status" in data:
            if data["status"] not in ["ACTIVE", "PAUSED", "CANCELLED"]:
                return jsonify({"error": "Invalid status"}), 400
            update_fields["fixedBills.$.status"] = data["status"]

        if not update_fields:
            return jsonify({"error": "No fields to update"}), 400

        # Adiciona campo de atualização
        from datetime import datetime
        from zoneinfo import ZoneInfo

        update_fields["fixedBills.$.updatedAt"] = datetime.now(
            ZoneInfo("America/Sao_Paulo")
        )

        # Atualiza a conta
        result = profile_config_service.collection.update_one(
            {"userId": user_id, "fixedBills.billId": bill_id}, {"$set": update_fields}
        )

        if result.modified_count == 0:
            return jsonify({"error": "Bill not found or no changes made"}), 404

        # Busca a conta atualizada
        updated_bill = profile_config_service.get_fixed_bill_by_id(bill_id)

        return (
            jsonify(
                {
                    "message": "Fixed bill updated successfully",
                    "bill": convert_object_ids(updated_bill),
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@fixed_bills_bp.route("/fixed-bills/<bill_id>", methods=["DELETE"])
@token_required
def delete_fixed_bill(bill_id):
    """Remove uma conta fixa (soft delete - muda status para CANCELLED)"""
    try:
        logged_user = g.logged_user
        user_id = logged_user.get("id")

        # Verifica se a conta existe
        bill = profile_config_service.get_fixed_bill_by_id(bill_id)
        if not bill:
            return jsonify({"error": "Bill not found"}), 404

        # Soft delete - muda o status para CANCELLED
        from datetime import datetime
        from zoneinfo import ZoneInfo

        result = profile_config_service.collection.update_one(
            {"userId": user_id, "fixedBills.billId": bill_id},
            {
                "$set": {
                    "fixedBills.$.status": "CANCELLED",
                    "fixedBills.$.updatedAt": datetime.now(
                        ZoneInfo("America/Sao_Paulo")
                    ),
                }
            },
        )

        if result.modified_count == 0:
            return jsonify({"error": "Failed to delete bill"}), 500

        return (
            jsonify(
                {
                    "message": f"Fixed bill '{bill['name']}' cancelled successfully",
                    "note": "The bill was not permanently deleted and can be reactivated if needed",
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
