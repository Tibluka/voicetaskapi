from openai import OpenAI
from decouple import config
from utils.load_file import load_prompt
from typing import List, Dict, Any
import json

API_KEY = config("API_KEY_OPENAI")

def analyse_result(results: List[Dict[str, Any]], prompt: str):
    client = OpenAI(api_key=API_KEY)
        
    agent_analyser = load_prompt('prompts/agent_analyser.txt')
    
    response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
            {"role": "system", "content": f"{agent_analyser}"},
            {"role": "system", "content": f"A solicitação do usuário é: {prompt}"},
            {"role": "user", "content": json.dumps(results, indent=2)}
    ])
    print(response.choices[0].message.content)
    return response.choices[0].message.content