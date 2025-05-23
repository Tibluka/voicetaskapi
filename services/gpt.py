from openai import OpenAI
from decouple import config
from datetime import datetime
from utils.load_file import load_prompt

API_KEY = config("API_KEY_OPENAI")

def ask_gpt(prompt: str):
    client = OpenAI(api_key=API_KEY)
        
    agent_consulting = load_prompt('prompts/agent_consulting.txt')
    
    today = datetime.now()
    
    response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
            {"role": "system", "content": f"{agent_consulting}"},
            {"role": "system", "content": f"Hoje é {today.date()}. Se o usuário disser 'ontem', use a data de hoje menos um dia."},
            {"role": "user", "content": prompt}
    ])
    print(response.choices[0].message.content)
    return response.choices[0].message.content