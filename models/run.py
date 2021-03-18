from db import db


class Run(db.Model):
    __table_args__ = (
        db.UniqueConstraint('project_id', 'user_set_identifier'),
    )
    # External:
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    previous_run_id = db.Column(db.Integer, db.ForeignKey('run.id'), nullable=True)
    children = db.relationship("Run",
                               backref=db.backref('previous_run', remote_side=[id])
                               )
    user_set_identifier = db.Column(db.String(120), unique=False, nullable=False)
    # error: An error occurred for this run
    # created: Successfully created this run
    # cuckoo_running: Cuckoo is analyzing
    # diff_tool_running: Old observables get subtracted from current report
    # first_finished_unprepared: If no previous runs are available,
    # diff tool sets this status, patternson-runner waits for it
    # first_finished_prepared: If no previous runs are available,
    # patterson sets this once the pattern generation is complete
    # finished_unprepared: diff tool sets this status, patternson-runner waits for it
    # finished_prepared: patterson sets this once the pattern generation is complete

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
