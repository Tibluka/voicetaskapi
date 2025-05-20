from flask import Flask
from routes.transcribe_route import transcribe_bp

app = Flask(__name__)
app.register_blueprint(transcribe_bp)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5004)