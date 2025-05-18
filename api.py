import os

import pymongo
from services.transcribe import transcribe
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import tempfile
import pymongo
import json as pyjson  # para evitar conflito com sua variável
import re

app = Flask(__name__)

try:
    client = pymongo.MongoClient(
        "mongodb+srv://tibluka:Lukkao1234@cluster0.4mljuv7.mongodb.net/?retryWrites=true&w=majority")
    db = client['agacode']
except Exception as e:
    print(str(e))
spending_collection = db['spending']

@app.route("/transcribe", methods=["POST"])
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
        
        if json_data.get("consult") == True:
            filters = {}
            for key in ["type", "category", "date"]:
                value = json_data.get(key)
                if value:
                    filters[key] = value
            
            results = list(spending_collection.find(filters))
            
            for r in results:
                r["_id"] = str(r["_id"])

        else:
            # Prepara o documento para inserção
            spending_doc = {
                "description": json_data.get("description"),
                "value": json_data.get("value"),
                "type": json_data.get("type"),
                "category": json_data.get("category"),
                "date": json_data.get("date")
            }
            
            inserted_id = spending_collection.insert_one(spending_doc).inserted_id
        # Insere no MongoDB
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)

    return jsonify({"transcription": {
        "gpt_answer": json_data.get("gpt_answer"),
        "description": json_data.get("description"),
        "consult_results": results
    }})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5004)