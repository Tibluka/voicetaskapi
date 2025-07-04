from openai import OpenAI
from decouple import config
from services.profile_config_service import ProfileConfigService
from utils.load_file import load_prompt
from typing import List, Dict, Any
import json
from utils.convert_utils import convert_object_ids
from db.mongo import profile_config_collection

API_KEY = config("API_KEY_OPENAI")

profile_config_service = ProfileConfigService(profile_config_collection)


def analyse_profile_result(config: Dict[str, Any], prompt: str):
    client = OpenAI(api_key=API_KEY)

    agent_profile_analyser = load_prompt("prompts/agent_profile-analyser.txt")

    config_clean = convert_object_ids(config)

    if config_clean == None:
        config_clean = profile_config_service.create_default_profile_config(5000, 3000)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=512,  # Limitar tokens para acelerar resposta
        temperature=0.2,  # Menor variação, respostas mais diretas
        top_p=0.8,
        messages=[
            {"role": "system", "content": f"{agent_profile_analyser}"},
            {"role": "assistant", "content": f"A solicitação do usuário é: {prompt}"},
            {
                "role": "user",
                "content": f"As configurações do perfil do usuário são: {str(config_clean)}",
            },
        ],
    )

    print(response.choices[0].message.content)
    return response.choices[0].message.content
