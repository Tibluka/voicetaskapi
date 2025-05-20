# Flask Transcription API

Este projeto é uma API Flask que permite transcrição de arquivos de áudio e integração com um banco de dados MongoDB.

## 📦 Requisitos

- Python 3.8+
- `pip`
- MongoDB Atlas (ou MongoDB local)
- Um serviço de transcrição (ex: OpenAI Whisper, etc.)

## 📁 Estrutura do Projeto

```
project/
├── api.py
├── config.py
├── services/
│   └── transcribe.py
│   └── gpt.py
├── db/
│   └── mongo.py
├── routes/
│   └── transcribe_route.py
├── utils/
│   └── date_utils.py
├── .env
├── requirements.txt
└── README.md
```

## ⚙️ Configuração do Ambiente

1. **Clone o repositório:**

```bash
git clone https://github.com/seu-usuario/seu-projeto.git
cd seu-projeto
```

2. **Crie um ambiente virtual (opcional, mas recomendado):**

```bash
python -m venv venv
source venv/bin/activate  # no Windows use: venv\Scripts\activate
```

3. **Instale as dependências:**

```bash
pip install -r requirements.txt
```

4. **Configure as variáveis de ambiente:**

Este projeto utiliza um arquivo `.env` para manter as chaves sensíveis seguras.

- Faça uma cópia do arquivo de exemplo:

```bash
cp .env.example .env
```

- Edite o arquivo `.env` com suas chaves reais:

```env
MONGO=mongodb+srv://usuario:senha@cluster.mongodb.net/agacode?retryWrites=true&w=majority
# outras variáveis aqui, se necessário
```

⚠️ **Nunca envie seu `.env` para o GitHub!**  
O `.env` está listado no `.gitignore` por segurança.

## 🚀 Rodando o Projeto

Execute o projeto com o seguinte comando:

```bash
python app.py
```

A aplicação estará disponível em `http://localhost:5004`.

## 📤 Endpoint

**POST** `/transcribe`

- Envie um arquivo de áudio no corpo da requisição com o campo `file`.

Exemplo com `curl`:

```bash
curl -X POST -F "file=@audio.mp3" http://localhost:5004/transcribe
```

## 🧪 Testando

Você pode usar ferramentas como Postman, Thunder Client (VSCode), ou curl para testar o endpoint.

## 📄 Licença

Este projeto está licenciado sob a MIT License.
