from db import db


class Run(db.Model):
    # External:
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    previous_run_id = db.Column(db.Integer, db.ForeignKey('run.id'), nullable=True)
    children = db.relationship("Run",
                backref=db.backref('previous_run', remote_side=[id])
            )
    user_set_identifier = db.Column(db.String(120), unique=True, nullable=False)
    # error, created, cuckoo_running, diff_tool_running, finished_unprepared, finished_prepared
    status = db.Column(db.String, unique=False, nullable=False, default="created")
    error = db.Column(db.String, unique=False, nullable=True)

    # Internal:
    cuckoo_output_path = db.Column(db.String(300), unique=True, nullable=True)
    user_submitted_artifact_path = db.Column(db.String(300), unique=True, nullable=True)
    diff_tool_output_path = db.Column(db.String(300), unique=True, nullable=True)
    patterson_output_path = db.Column(db.String(300), unique=True, nullable=True)

    def json(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "previous_run_id": self.previous_run_id,
            "user_set_identifier": self.user_set_identifier,
            "status": self.status,
            "error": self.error
        }
