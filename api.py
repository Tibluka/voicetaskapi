from flask import Flask
from routes.transcribe_route import transcribe_bp
from routes.auth_routes import auth_bp

app = Flask(__name__)
app.register_blueprint(transcribe_bp)
app.register_blueprint(auth_bp)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=6002)