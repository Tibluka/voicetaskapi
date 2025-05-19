import os

import pymongo
from services.transcribe import transcribe
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import tempfile
import pymongo
import json as pyjson
import re
from datetime import datetime, timedelta
import calendar
from decouple import config

app = Flask(__name__)

MONGO = config("MONGO")

try:
    client = pymongo.MongoClient(MONGO)
    db = client['agacode']
    spending_collection = db['spending']
except Exception as e:
    print(str(e))

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
        
        results = None
        
        if json_data.get("consult") == True:
            filters = {}

            # Adiciona type e category se existirem
            for key in ["type", "category"]:
                value = json_data.get(key)
                if value:
                    filters[key] = value

            # Trata o campo de data
            date_str = json_data.get("date")
            if date_str:
                try:
                    parts = date_str.split("-")
                    if len(parts) == 1:
                        # Apenas ano
                        year = int(parts[0])
                        start = datetime(year, 1, 1)
                        end = datetime(year + 1, 1, 1)
                    elif len(parts) == 2:
                        # Ano e mês
                        year, month = int(parts[0]), int(parts[1])
                        start = datetime(year, month, 1)
                        _, last_day = calendar.monthrange(year, month)
                        end = datetime(year, month, last_day) + timedelta(days=1)
                    elif len(parts) == 3:
                        # Ano, mês e dia
                        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                        start = datetime(year, month, day)
                        end = start + timedelta(days=1)
                    else:
                        raise ValueError("Formato de data inválido")

                    # Aplica o filtro de intervalo
                    filters["date"] = {"$gte": start.strftime("%Y-%m-%d"), "$lt": end.strftime("%Y-%m-%d")}

                except Exception as e:
                    return jsonify({"error": f"Erro ao processar data: {str(e)}"}), 400

            # Consulta no MongoDB
            results = list(spending_collection.find(filters))

            for r in results:
                r["_id"] = str(r["_id"])  # converte ObjectId para string

        else:
            # Prepara o documento para inserção
            spending_doc = {
                "description": json_data.get("description"),
                "value": json_data.get("value"),
                "type": json_data.get("type"),
                "category": json_data.get("category"),
                "date":  json_data.get("date"),
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