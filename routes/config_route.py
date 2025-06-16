# routes/config.py
import datetime
from flask import Blueprint, request, jsonify
from bson import ObjectId
from db.mongo import config_collection, user_collection

from dto.config_dto import config_to_dto
from services.token_service import TokenService
from utils.auth_decorator import token_required

config_bp = Blueprint("config", __name__)

@config_bp.route("/config", methods=["GET"])
@token_required
def get_config(user_id):
    cfg = config_collection.find_one({"userId": user_id})
    if not cfg:
        return jsonify({"error": "Config not found"}), 404
    return jsonify(config_to_dto(cfg)), 200

@config_bp.route("/config", methods=["POST"])
@token_required
def create_config(user_id):
    if config_collection.find_one({"userId": user_id}):
        return jsonify({"error": "Config already exists"}), 400

    data = request.get_json()
    data.update({
        "userId": user_id,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    })
    result = config_collection.insert_one(data)
    cfg = config_collection.find_one({"_id": result.inserted_id})
    return jsonify(config_to_dto(cfg)), 201

@config_bp.route("/config", methods=["PUT"])
@token_required
def update_config(user_id):
    data = request.get_json()
    data["updatedAt"] = datetime.utcnow()

    result = config_collection.update_one(
        {"userId": user_id},
        {"$set": data},
        upsert=False
    )
    if not result.matched_count:
        return jsonify({"error": "Config not found"}), 404

    cfg = config_collection.find_one({"userId": user_id})
    return jsonify(config_to_dto(cfg)), 200