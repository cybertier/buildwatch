from db import db


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # External:
    name = db.Column(db.String(120), unique=True, nullable=False)
    git_url = db.Column(db.String(300), unique=False, nullable=True)
    git_managed = db.Column(db.Boolean(), unique=False, nullable=False)
    cuckoo_analysis_per_run = db.Column(db.Integer(), unique=False, nullable=False)
    # Internal:
    git_checkout_path = db.Column(db.String(500), unique=False, nullable=True)
    storage_path = db.Column(db.String(500), unique=False, nullable=True)
    runs = db.relationship('Run', backref='project', lazy=True)

    def json(self):
        return {
            "id": self.id,
            "name": self.name,
            "git_url": self.git_url,
            "git_managed": self.git_managed,
            "cuckoo_analysis_per_run": self.cuckoo_analysis_per_run,
        }
