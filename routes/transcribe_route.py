import os
import re
import tempfile
import json as pyjson

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from services.transcribe import transcribe
from db.mongo import spending_collection
from utils.date_utils import get_date_range

transcribe_bp = Blueprint("transcribe", __name__)

@transcribe_bp.route("/transcribe", methods=["POST"])
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
        json_str = transcribe(temp_filepath)
        cleaned_str = re.sub(r"^```json\s*|```$", "", json_str.strip(), flags=re.MULTILINE)
        json_data = pyjson.loads(cleaned_str)

        results = None
        if json_data.get("consult") is True:
            filters = {k: json_data[k] for k in ["type", "category"] if json_data.get(k)}

            if json_data.get("date"):
                try:
                    filters["date"] = get_date_range(json_data["date"])
                except Exception as e:
                    return jsonify({"error": f"Erro ao processar data: {str(e)}"}), 400

            operation = json_data.get("operation")
            if operation == "MAX":
                results = list(spending_collection.find(filters).sort("value", -1).limit(1))
            elif operation == "MIN":
                results = list(spending_collection.find(filters).sort("value", 1).limit(1))
            else:
                results = list(spending_collection.find(filters))

            for r in results:
                r["_id"] = str(r["_id"])
        else:
            required_fields = ["description", "value", "type", "category", "date"]
            missing = [field for field in required_fields if not json_data.get(field)]

            if not missing:
                spending_doc = {field: json_data[field] for field in required_fields}
                spending_collection.insert_one(spending_doc)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)

    return jsonify({
        "transcription": {
            "gpt_answer": json_data.get("gpt_answer"),
            "description": json_data.get("description"),
            "consult_results": results
        }
    })