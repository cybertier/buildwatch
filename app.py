import os

from flask import Flask

app = Flask(__name__)

app.config.from_object("config.default_config")
if os.environ.get("BUILDWATCH_SETTINGS_FILE"):
    app.config.from_envvar("BUILDWATCH_SETTINGS_FILE")
