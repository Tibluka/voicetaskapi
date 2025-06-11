import sys
from flask_cors import CORS  # <-- import CORS
from flask import Flask
from routes.transcribe_route import transcribe_bp
from routes.auth_routes import auth_bp
from routes.spendings_route import spending_bp
from db.mongo import client

app = Flask(__name__)
CORS(app)  

try:
    client.admin.command('ping')
    print("✅ Conexão com o MongoDB estabelecida com sucesso.")
except Exception as e:
    print("❌ Erro ao conectar ao MongoDB:", e)
    sys.exit(1)

app.register_blueprint(transcribe_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(spending_bp)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=6002)