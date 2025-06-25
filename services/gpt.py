from openai import OpenAI
from decouple import config
from datetime import datetime
from utils.load_file import load_prompt
from zoneinfo import ZoneInfo

API_KEY = config("API_KEY_OPENAI")

def ask_gpt(prompt: str, context: str):
    client = OpenAI(api_key=API_KEY)
        
    agent_consulting = load_prompt('prompts/agent_consulting.txt')
    
    today = datetime.now(ZoneInfo("America/Sao_Paulo"))
    print(today)
    
    response = client.chat.completions.create(
    model="gpt-4o-mini",
    max_tokens=512,  # Limitar tokens para acelerar resposta
    temperature=0.2, # Menor variação, respostas mais diretas
    top_p=0.8, 
    messages=[
            {"role": "system", "content": f"{agent_consulting}"},
            {"role": "system", "content": f"Hoje é {today.date()}. Se o usuário disser 'ontem', use a data de hoje menos um dia."},
            {"role": "assistant", "content": f"Mensagens anteriores de contexto: {context}"},
            {"role": "user", "content": prompt}
    ])
    print(response.choices[0].message.content)
    return response.choices[0].message.content