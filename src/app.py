from flask import Flask
from flask_cors import CORS
from routes import setup_routes
from db import userDb, reset
import os

FLAS_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "1234")

app = Flask(__name__)
app.secret_key = FLAS_SECRET_KEY
userDb()
reset()
CORS(app, supports_credentials=True, origins=["ihre url"])

setup_routes(app)

if __name__ == "__main__":
    app.run(debug=True)
