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
from routes.fixed_bills_route import fixed_bills_bp  # Nova importação
from routes.summary_route import summary_bp  # Nova importação 
from db.mongo import client 

app = Flask(__name__) 
CORS(app) 
 
try:
    client.admin.command("ping") 
    print("✅ Conexão com o MongoDB estabelecida com sucesso.") 
except Exception as e: 
    print("❌ Erro ao conectar ao MongoDB:", e) 
    sys.exit(1) 
 
app.register_blueprint(execute_bp) 
app.register_blueprint(transcribe_bp) 
app.register_blueprint(auth_bp) 
app.register_blueprint(spending_bp) 
app.register_blueprint(config_bp) 
app.register_blueprint(projects_bp) 
app.register_blueprint(fixed_bills_bp)  # Nova rota 
app.register_blueprint(summary_bp)  # Nova rota 

if __name__ == "__main__": 
    app.run(debug=True, host="0.0.0.0", port=6002) 
