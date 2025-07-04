import os
import tempfile
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from services.spending_service import SpendingService
from services.transcribe import transcribe
from db.mongo import spending_collection, profile_config_collection
from utils.auth_decorator import token_required
from services.profile_config_service import ProfileConfigService

transcribe_bp = Blueprint("transcribe", __name__)

spending_service = SpendingService(spending_collection)
profile_config_service = ProfileConfigService(profile_config_collection)


@transcribe_bp.route("/transcribe", methods=["POST"])
@token_required
def transcribe_audio():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    filename = secure_filename(file.filename)
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=os.path.splitext(filename)[1]
    ) as tmp:
        file.save(tmp.name)
        temp_filepath = tmp.name

    try:
        transcribed_text = transcribe(temp_filepath)

        if transcribed_text == None:
            return jsonify({"erro": "Erro ao transcrever o áudio"}), 400

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400

    finally:
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)

    return jsonify({"transcribed_text": transcribed_text}), 200
