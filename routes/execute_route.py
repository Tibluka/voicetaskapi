from flask import Blueprint, jsonify, g, request
from services.gpt import ask_gpt
from services.spending_service import SpendingService
from services.gpt_analyser import analyse_result
from services.gpt_chart import analyse_chart_intent
from db.mongo import spending_collection, profile_config_collection
from services.profile_config_service import ProfileConfigService
from services.query_orchestrator import QueryOrchestrator
import re
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
                # Verifica se é criação de projeto
                if json_data.get("type") == "PROJECT_CREATION":
                    # Validações
                    required_fields = ["projectName", "targetValue"]
                    field_names_pt = {
                        "projectName": "nome do projeto",
                        "targetValue": "valor alvo",
                    }
                    missing = [
                        field for field in required_fields if not json_data.get(field)
                    ]
                    if missing:
                        missing_pt = [
                            field_names_pt.get(field, field) for field in missing
                        ]
                        return (
                            jsonify(
                                {
                                    "transcription": {
                                        "gpt_answer": f"🏗️ **Para criar seu projeto, preciso de mais informações:**\n\n❓ **Faltam:** {', '.join(missing_pt)}\n\nExemplo: *\"Criar projeto reforma da casa com meta de 50 mil reais\"*",
                                        "description": json_data.get("prompt"),
                                        "consult_results": None,
                                        "chart_data": None,
                                    }
                                }
                            ),
                            400,
                        )

                    # Verifica se já existe um projeto com esse nome
                    existing_project = profile_config_service.get_project_by_name(
                        json_data["projectName"]
                    )
                    if existing_project:
                        return (
                            jsonify(
                                {
                                    "transcription": {
                                        "gpt_answer": f"❌ **Projeto já existe!**\n\nJá existe um projeto chamado \"{json_data['projectName']}\". Escolha outro nome ou use o projeto existente.",
                                        "description": json_data.get("prompt"),
                                        "consult_results": None,
                                        "chart_data": None,
                                    }
                                }
                            ),
                            400,
                        )

                    # Cria o projeto
                    project = profile_config_service.create_project(
                        name=json_data["projectName"],
                        description="",
                        target_value=float(json_data["targetValue"]),
                    )

                    # Atualiza a resposta para confirmar a criação
                    description_text = (
                        f"📝 **Descrição:** {project['description']}\n"
                        if project.get("description")
                        else ""
                    )
                    json_data["gpt_answer"] = (
                        f"🏗️ **Projeto criado com sucesso!**\n\n"
                        f"✅ **Nome:** {project['projectName']}\n"
                        f"🎯 **Meta:** R$ {project['targetValue']:.2f}\n"
                        f"{description_text}"
                        f"Agora você pode vincular gastos a este projeto! 📊"
                    )

                    # Para projetos, adapta para o formato ConsultResult
                    project_result = {
                        "_id": project["projectId"],
                        "category": project["projectName"],
                        "description": "Novo projeto criado",
                        "date": json_data.get("date", ""),
                        "value": float(project["targetValue"]),
                        "type": "PROJECT_CREATION",
                    }
                    json_data["consult_results"] = [project_result]

                # Verifica se é criação de conta fixa
                elif json_data.get("type") == "FIXED_BILL":
                    # Validações
                    required_fields = ["name", "amount", "dueDay"]
                    # Mapeamento dos campos para nomes em português
                    field_names_pt = {
                        "name": "nome",
                        "amount": "valor",
                        "dueDay": "dia de vencimento",
                    }
                    missing = [
                        field for field in required_fields if not json_data.get(field)
                    ]
                    if missing:
                        missing_pt = [
                            field_names_pt.get(field, field) for field in missing
                        ]
                        return (
                            jsonify(
                                {
                                    "transcription": {
                                        "gpt_answer": f"Faltam informações para criar a conta fixa: {', '.join(missing_pt)}",
                                        "description": json_data.get("prompt"),
                                        "consult_results": None,
                                        "chart_data": None,
                                    }
                                }
                            ),
                            200,
                        )

                    # Cria a conta fixa
                    bill = profile_config_service.create_fixed_bill(
                        name=json_data["name"],
                        amount=float(json_data["amount"]),
                        due_day=int(json_data["dueDay"]),
                        description=json_data.get("description", ""),
                        category=json_data.get("category", "OTHER"),
                        autopay=json_data.get("autopay", False),
                        reminder=json_data.get("reminder", True),
                    )

                    # Atualiza a resposta para confirmar a criação
                    json_data["gpt_answer"] = (
                        f"✅ **Conta fixa criada com sucesso!**\n\n📝 {bill['name']}\n💰 Valor: R$ {bill['amount']:.2f}\n📅 Vencimento: Todo dia {bill['dueDay']}\n\nA conta será lembrada todos os meses!"
                    )

                # Se não for projeto nem conta fixa, é um gasto normal
                else:
                    # Verifica se há menção a projeto
                    if json_data.get("projectName"):
                        project_name = json_data["projectName"]

                        # Busca o projeto pelo nome
                        project = profile_config_service.get_project_by_name(
                            project_name
                        )

                        if project:
                            # Adiciona o projectId ao json_data
                            json_data["projectId"] = project["projectId"]
                            profile_config_service.update_project_spending(
                                project["projectId"], json_data.get("value", 0)
                            )

                            # Atualiza a mensagem de resposta com o nome do projeto
                            json_data["gpt_answer"] = (
                                f"✅ **Gasto registrado no projeto '{project['projectName']}'!**\n\n💰 Valor: R$ {json_data.get('value', 0):.2f}\n📝 {json_data.get('description', '')}"
                            )
                        else:
                            # Se o projeto não existir, retorna erro
                            return (
                                jsonify(
                                    {
                                        "transcription": {
                                            "gpt_answer": f"❌ Projeto '{project_name}' não encontrado. Por favor, crie o projeto primeiro ou verifique o nome.",
                                            "description": json_data.get("prompt"),
                                            "consult_results": None,
                                            "chart_data": None,
                                        }
                                    }
                                ),
                                400,
                            )

                    # Só insere gasto se não for criação de projeto
                    if json_data.get("type") != "PROJECT_CREATION":
                        added_document = spending_service.insert_spending(json_data)
                        json_data["consult_results"] = [added_document]

            except ValueError as ve:
                return (
                    jsonify(
                        {
                            "transcription": {
                                "gpt_answer": str(ve),
                                "description": json_data.get("prompt"),
                                "consult_results": None,
                                "chart_data": None,
                            }
                        }
                    ),
                    400,
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
