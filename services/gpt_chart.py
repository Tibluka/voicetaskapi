from openai import OpenAI
from decouple import config
from utils.convert_utils import convert_object_ids
from utils.load_file import load_prompt
from typing import List, Dict, Any
import json

API_KEY = config("API_KEY_OPENAI")

def analyse_chart_intent(results: List[Dict[str, Any]], prompt: str):
    client = OpenAI(api_key=API_KEY)

    chart_prompt = load_prompt('prompts/agent_chart-analyser.txt')

    results_clean = convert_object_ids(results)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=512,  # Limitar tokens para acelerar resposta
        temperature=0.2, # Menor variação, respostas mais diretas
        top_p=0.8,
        messages=[
            {"role": "system", "content": chart_prompt},
            {"role": "system", "content": f"A solicitação do usuário é: {prompt}"},
            {"role": "user", "content": json.dumps(results_clean, indent=2)}
        ]
    )
    print(response.choices[0].message.content)
    return response.choices[0].message.content