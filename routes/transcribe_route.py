import os
import re
import tempfile
import json as pyjson

from flask import Blueprint, request, jsonify, g
from werkzeug.utils import secure_filename

from services.spending_service import SpendingService
from services.gpt_analyser import analyse_result
from services.transcribe import transcribe
from services.gpt_chart import analyse_chart_intent

from db.mongo import spending_collection

from utils.auth_decorator import token_required

transcribe_bp = Blueprint("transcribe", __name__)

spending_service = SpendingService(spending_collection)

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
        cleaned_str = re.sub(r"^```json\s*|```$", "", transcribed_json["gpt"].strip(), flags=re.MULTILINE)
        json_data = pyjson.loads(cleaned_str)
        
        results = None
        if json_data.get("consult") is True:
            try:
                results = spending_service.consult_spending(json_data)
                analyser = analyse_result(results, json_data.get("description"))
                cleaned_str = re.sub(r"^```json\s*|```$", "", analyser.strip(), flags=re.MULTILINE)

                # Se o agente inicial sinalizou que é para gerar gráfico
                if json_data.get("chart_data") is True:
                    chart_response = analyse_chart_intent(results, transcribed_json["prompt"])
                    cleaned_chart_str = re.sub(r"^```json\s*|```$", "", chart_response.strip(), flags=re.MULTILINE)
                    chart_data = pyjson.loads(cleaned_chart_str)
                    json_data["chart_data"] = chart_data  # substitui bool pelo conteúdo
                    json_data["gpt_answer"] = pyjson.loads(cleaned_str)["gpt_answer"]
                else:
                    json_data = pyjson.loads(cleaned_str)
                
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
            "consult_results": results,
            "chart_data": json_data.get("chart_data", False)
        }
    })