import os
import re
import tempfile
import json as pyjson
from flask import Blueprint, request, jsonify, g
from werkzeug.utils import secure_filename
from services.gpt_profile_analyser import analyse_profile_result
from services.spending_service import SpendingService
from services.gpt_analyser import analyse_result
from services.transcribe import transcribe
from services.gpt_chart import analyse_chart_intent
from db.mongo import spending_collection, profile_config_collection
from utils.auth_decorator import token_required
from utils.convert_utils import convert_object_ids
from services.profile_config_service import ProfileConfigService
from services.query_orchestrator import QueryOrchestrator

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
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
        file.save(tmp.name)
        temp_filepath = tmp.name

    try:
        transcribed_json = transcribe(temp_filepath)
        cleaned_str = re.sub(r'^```(json)?\s*|\s*```$', '', transcribed_json["gpt"].strip(), flags=re.MULTILINE)
        json_data = pyjson.loads(cleaned_str)
        
        if json_data.get("answer_blocked") is True:
            return jsonify({"transcription": {
                "gpt_answer": json_data.get("gpt_answer"),
                "description": None,
                "consult_results": None,
                "chart_data": None,
                "results": None
            }}), 200

        results = {}

        if json_data.get("consult") is True:
            try:
                orchestrator = QueryOrchestrator(spending_collection, profile_config_collection, g.logged_user.get("id"))
                query_result = orchestrator.execute_queries(json_data)

                analyser_result = analyse_result(query_result, transcribed_json["prompt"])
                cleaned_str = re.sub(r"^```json\\s*|```$", "", analyser_result.strip(), flags=re.MULTILINE)
                json_data.update(pyjson.loads(cleaned_str))

                if json_data.get("chart_data") is True:
                    chart_response = analyse_chart_intent(query_result.get("spendings", []), transcribed_json["prompt"])
                    cleaned_chart_str = re.sub(r"^```json\\s*|```$", "", chart_response.strip(), flags=re.MULTILINE)
                    json_data["chart_data"] = pyjson.loads(cleaned_chart_str)

                if json_data.get("config_field") != "monthly_limit":
                    json_data["consult_results"] = query_result.get("spendings", [])

            except Exception as e:
                return jsonify({"error": str(e)}), 400

        else:
            try:
                spending_service.insert_spending(json_data)
            except ValueError as ve:
                return jsonify({"transcription": {
                    "gpt_answer": json_data.get("gpt_answer"),
                    "description": None,
                    "consult_results": None,
                    "chart_data": None
                }}), 200

    except Exception as e:
        print(str(e))
        return jsonify({"transcription": {
            "gpt_answer": "Ocorreu um erro desconhecido",
            "description": None,
            "consult_results": None,
            "chart_data": None
        }}), 400
    finally:
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)

    return jsonify({
        "transcription": {
            "gpt_answer": json_data.get("gpt_answer"),
            "description": json_data.get("description"),
            "consult_results": convert_object_ids(json_data.get("consult_results")),
            "chart_data": json_data.get("chart_data", False)
        }
    })