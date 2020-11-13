from db import db


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
