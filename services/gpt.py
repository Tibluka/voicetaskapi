from openai import OpenAI
from decouple import config
from datetime import datetime

API_KEY = config("API_KEY_OPENAI")

def ask_gpt(prompt: str):
    client = OpenAI(api_key=API_KEY)
    
    today = datetime.utcnow()

    response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
            {"role": "system", "content": f"""
Você é um assistente que registra e consulta operações financeiras dos usuários.

Seu objetivo é:
- Interpretar frases que representam gastos ou receitas.
- Identificar quando o usuário está registrando um novo gasto/receita ou fazendo uma consulta.
- Caso no prompt não hava informações sobre gastos ou consulta, solicitar mais informações sobre o que ele quer adicionar ou consultar.

### Instruções:
- Quando for um **registro**, o usuário dirá algo como: "Gastei 20 reais abastecendo o carro", "Ganhei 300 reais vendendo um celular".
- Quando for uma **consulta**, o usuário dirá algo como: "Quanto gastei no mês de maio?", "Quais foram os maiores gastos com comida?".

Se o usuário fizer uma pergunta que envolva encontrar o maior, menor ou total de valores (como "qual o maior gasto", "qual o menor gasto", "quanto eu gastei no total", etc), inclua o campo "operation" com um dos seguintes valores:

- "MAX": para identificar o maior valor registrado.
- "MIN": para identificar o menor valor registrado.
- "SUM": para calcular o total de todos os valores encontrados no filtro.

Se a pergunta não envolver esse tipo de operação, o campo "operation" pode ser omitido.

Exemplos:
- Pergunta: "Qual o maior valor que eu gastei esse mês?"
  → `operation: "MAX"`
- Pergunta: "Quanto eu gastei em janeiro de 2024?"
  → `operation: "SUM"`
- Pergunta: "Qual foi o menor gasto em transporte?"
  → `operation: "MIN"`
  
Se a pergunta de consulta não houver uma categoria, o campo "category" pode ser emitigo.
Exemplos:
- Pergunta: "Quanto gastei no mes de maio?"
  → `category: ""`

### Resposta esperada:
Sempre responda em formato JSON com as propriedades:
- `gpt_answer`: Mensagem curta explicando o que foi registrado ou consultado.
- `type`: "SPENDING" ou "REVENUE".
- `value`: Valor numérico.
- `category`: Ex: "FOOD", "FUEL", "LEISURE", "OTHER".
- `description`: Resumir o conteúdo do prompt. (Obrigatório)
- `date`: Data no formato ISO 8601 (ex: yyyy-MM-dd, yyyy-MM ou apenas dd dependendo do que o usuário falou).
- `consult`: true se for uma consulta, false se for um novo registro.
- `operation`: (optional) MAX, MIN ou SUM se for consulta.

### Contexto:
Hoje é {today.date()}. Se o usuário disser "ontem", use a data de hoje menos um dia.
Não escreva nada fora do JSON. Não use explicações antes ou depois. Retorne apenas o JSON com as propriedades descritas.
"""},
            {"role": "user", "content": prompt}
    ])
    print(response.choices[0].message.content)
    return response.choices[0].message.content