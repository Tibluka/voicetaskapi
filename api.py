# api.py
import sys
from flask_cors import CORS
from flask import Flask
from routes.transcribe_route import transcribe_bp
from routes.auth_routes import auth_bp
from routes.spendings_route import spending_bp
from routes.config_route import config_bp
from routes.execute_route import execute_bp
from routes.projects_route import projects_bp
from routes.fixed_bills_route import fixed_bills_bp
from routes.summary_route import summary_bp
from db.mongo import client
from websocket_server import init_socketio

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Verificar conexão com MongoDB
try:
    client.admin.command("ping")
    print("✅ Conexão com o MongoDB estabelecida com sucesso.")
except Exception as e:
    print("❌ Erro ao conectar ao MongoDB:", e)
    sys.exit(1)

# Registrar blueprints
app.register_blueprint(execute_bp)
app.register_blueprint(transcribe_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(spending_bp)
app.register_blueprint(config_bp)
app.register_blueprint(projects_bp)
app.register_blueprint(fixed_bills_bp)
app.register_blueprint(summary_bp)

# Inicializar WebSocket
socketio = init_socketio(app)

if __name__ == "__main__":
    # Usar socketio.run ao invés de app.run para suportar WebSocket
    socketio.run(app, debug=True, host="0.0.0.0", port=6002)
