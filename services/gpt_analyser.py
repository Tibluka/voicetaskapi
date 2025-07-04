from openai import OpenAI
from decouple import config
from utils.load_file import load_prompt
from typing import List, Dict, Any, Optional
import json
from utils.convert_utils import convert_object_ids

API_KEY = config("API_KEY_OPENAI")


def analyse_result(results: Dict[str, Any], prompt: str):
    client = OpenAI(api_key=API_KEY)
    agent_analyser = load_prompt("prompts/agent_analyser.txt")

    # Limpeza de ObjectIds
    results_clean = {}
    for key, value in results.items():
        results_clean[key] = convert_object_ids(value)

    messages = [
        {"role": "system", "content": agent_analyser},
        {"role": "assistant", "content": f"A solicitação do usuário é: {prompt}"},
    ]

    for key, value in results_clean.items():
        messages.append(
            {"role": "assistant", "content": f"Dados da coleção '{key}': {value}"}
        )

    response = client.chat.completions.create(model="o4-mini", messages=messages)

    print(response.choices[0].message.content)
    return response.choices[0].message.content
