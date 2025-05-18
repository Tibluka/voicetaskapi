from openai import OpenAI
from decouple import config

API_KEY = config("API_KEY_OPENAI")

def ask_gpt(prompt: str):
    client = OpenAI(api_key=API_KEY)

    response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
            {"role": "system", "content": "Você é um assistente que registra operações financeiras de usuários."},
            {"role": "system", "content": "Deve identificar no prompt informações que o usuário te passar que dizem respeito a gastos financeiros."},
            {"role": "system", "content": "O usuário pode fazer consultas ou registrar novos gastos/receitas."},
            {"role": "system", "content": "Quando for um novo registro, usuário deve te passar informações do tipo: Gastei 20 reais abastecendo o carro; Fui ao mercado e comprei pão por 5 reais; etc... Quando for uma consulta, o usuário deve informar ou a data ou a categoria ou valores. Ex: Qual o maior valor que gastei no mês de maio?; Quanto gastei no mês de Junho?; etc..."},
            {"role": "system", "content": "O formato da sua resposta deve ser um JSON que tenha as propriedades: gpt_answer, type (SPENDING OU REVENUE), category (Categoria do gasto/receita) e date (yyyy-MM-dd ou yyyy-MM ou somente dd, dependendo do período que o usuário falar). Quando for uma consulta, adicione a propriedade consult (true ou false) no json de retorno e no gpt_answer vc responde: Seguem informações."},
            {"role": "user", "content": prompt}
    ])

    print(response.choices[0].message.content)
    return response.choices[0].message.content