from flask import Flask
import os

app = Flask(__name__)

if os.environ.get('BUILDWATCH_SETTINGS_FILE'):
    app.config.from_envvar('BUILDWATCH_SETTINGS_FILE')
else:
    app.config.from_object('config.default_config')