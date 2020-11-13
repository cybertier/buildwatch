from db import db


class Run(db.Model):
    id = db.Column(db.Integer, primary_key=True)
