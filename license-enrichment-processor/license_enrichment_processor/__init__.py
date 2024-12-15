from flask import Flask
from flask_cors import CORS
from .controller import create_blueprint

API_PREFIX = "/api"
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


controller = create_blueprint()
app.register_blueprint(controller)
