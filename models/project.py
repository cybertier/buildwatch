from db import db


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)

    def json(self):
        return {
            "id": self.id,
            "name": self.name
        }
