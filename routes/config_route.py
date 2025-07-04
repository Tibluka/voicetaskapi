# routes/config.py
import datetime
from flask import Blueprint, request, jsonify
from dto.config_dto import config_to_dto
from utils.auth_decorator import token_required
from db.mongo import profile_config_collection
from services.profile_config_service import ProfileConfigService

config_bp = Blueprint("config", __name__)
profile_config_service = ProfileConfigService(profile_config_collection)


@config_bp.route("/config/<user_id>", methods=["GET"])
@token_required
def get_config(user_id):
    try:
        cfg = profile_config_service.collection.find_one({"userId": user_id})

        if not cfg:
            cfg = profile_config_service.create_default_profile_config(5000, 3000)

        return jsonify(config_to_dto(cfg)), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500


@config_bp.route("/config/<user_id>", methods=["POST"])
@token_required
def create_config(user_id):
    try:
        if profile_config_service.collection.find_one({"userId": user_id}):
            return jsonify({"error": "Config already exists"}), 400

        data = request.get_json()
        data.update(
            {
                "userId": user_id,
                "createdAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow(),
            }
        )
        result = profile_config_service.collection.insert_one(data)
        cfg = profile_config_service.collection.find_one({"_id": result.inserted_id})
        return jsonify(config_to_dto(cfg)), 201
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500


@config_bp.route("/config", methods=["PUT"])
@token_required
def update_config(user_id):
    try:
        data = request.get_json()
        data["updatedAt"] = datetime.utcnow()

        result = profile_config_service.collection.update_one(
            {"userId": user_id}, {"$set": data}, upsert=False
        )
        if not result.matched_count:
            return jsonify({"error": "Config not found"}), 404

        cfg = profile_config_service.collection.find_one({"userId": user_id})
        return jsonify(config_to_dto(cfg)), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500
