from flask import Blueprint, jsonify, g, request
from services.gpt import ask_gpt
from services.spending_service import SpendingService
from services.gpt_analyser import analyse_result
from services.gpt_chart import analyse_chart_intent
from db.mongo import spending_collection, profile_config_collection
from services.profile_config_service import ProfileConfigService
from services.query_orchestrator import QueryOrchestrator
import re
import os
import json as pyjson
from typing import List, Dict, Any

from utils.auth_decorator import token_required
from utils.convert_utils import convert_object_ids

execute_bp = Blueprint("execute-query", __name__)

spending_service = SpendingService(spending_collection)
profile_config_service = ProfileConfigService(profile_config_collection)


@execute_bp.route("/execute-query", methods=["POST"])
@token_required
def execute():
    data = request.get_json()
    transcribed_text = data.get("transcribedText")
    context: List[Dict[str, Any]] = data.get("context", [])
    if not transcribed_text:
        return (
            jsonify(
                {
                    "transcription": {
                        "gpt_answer": "Texto não identificado no áudio",
                        "description": None,
                        "consult_results": None,
                        "chart_data": None,
                        "results": None,
                    }
                }
            ),
            400,
        )

    # Converter context para string
    context_str = pyjson.dumps(context) if context else ""

    gpt_response = ask_gpt(transcribed_text, context_str)
    if not gpt_response:
        return (
            jsonify(
                {
                    "transcription": {
                        "gpt_answer": "Erro ao processar a solicitação",
                        "description": None,
                        "consult_results": None,
                        "chart_data": None,
                        "results": None,
                    }
                }
            ),
            400,
        )

    json_data = pyjson.loads(gpt_response)

    try:
        if json_data.get("answer_blocked") is True:
            return (
                jsonify(
                    {
                        "transcription": {
                            "gpt_answer": json_data.get("gpt_answer"),
                            "description": None,
                            "consult_results": None,
                            "chart_data": None,
                            "results": None,
                        }
                    }
                ),
                200,
            )

        if json_data.get("greeting") is True:
            return (
                jsonify(
                    {
                        "transcription": {
                            "gpt_answer": json_data.get("gpt_answer"),
                            "description": json_data.get("prompt"),
                            "consult_results": None,
                            "chart_data": None,
                            "results": None,
                        }
                    }
                ),
                200,
            )

        if json_data.get("consult") is True:
            try:
                orchestrator = QueryOrchestrator(
                    spending_collection,
                    profile_config_collection,
                    g.logged_user.get("id"),
                )
                query_result = orchestrator.execute_queries(json_data)

                analyser_result = analyse_result(query_result, transcribed_text)
                cleaned_str = re.sub(
                    r"^```json\\s*|```$",
                    "",
                    analyser_result.strip(),
                    flags=re.MULTILINE,
                )
                json_data.update(pyjson.loads(cleaned_str))
                json_data["consult_results"] = []

                if json_data.get("chart_data") is True:
                    chart_response = analyse_chart_intent(
                        query_result.get("spendings", []), transcribed_text
                    )
                    cleaned_chart_str = re.sub(
                        r"^```json\\s*|```$",
                        "",
                        chart_response.strip(),
                        flags=re.MULTILINE,
                    )
                    json_data["chart_data"] = pyjson.loads(cleaned_chart_str)

                if json_data.get("config_field") != "monthly_limit":
                    json_data["consult_results"] = query_result.get("spendings", [])

            except Exception as e:
                return jsonify({"error": str(e)}), 400

        else:
            try:
                spending_service.insert_spending(json_data)
            except ValueError as ve:
                return (
                    jsonify(
                        {
                            "transcription": {
                                "gpt_answer": json_data.get("gpt_answer"),
                                "description": json_data.get("prompt"),
                                "consult_results": None,
                                "chart_data": None,
                            }
                        }
                    ),
                    200,
                )

    except Exception as e:
        print(str(e))
        return (
            jsonify(
                {
                    "transcription": {
                        "gpt_answer": "Ocorreu um erro desconhecido",
                        "description": json_data.get("prompt"),
                        "consult_results": None,
                        "chart_data": None,
                    }
                }
            ),
            400,
        )

    return (
        jsonify(
            {
                "transcription": {
                    "gpt_answer": json_data.get("gpt_answer"),
                    "description": json_data.get("prompt"),
                    "consult_results": convert_object_ids(
                        json_data.get("consult_results")
                    ),
                    "chart_data": convert_object_ids(
                        json_data.get("chart_data", False)
                    ),
                }
            }
        ),
        200,
    )
