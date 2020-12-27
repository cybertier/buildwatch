from db import db
from app import app

def run(project_id: int):
    db.init_app(app)
