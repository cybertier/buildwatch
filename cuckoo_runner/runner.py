
from multiprocessing import Lock, synchronize

from cuckoo_runner.git_repo_preparer import package_zip_for_upload
from db import db
from app import app
from models.project import Project
from models.run import Run
import cuckoo_communicator


def run(run_id: int, lock: Lock):
    init(lock)
    run = Run.query.get(run_id)
    project = run.project
    path_to_zip = get_zip_for_upload(project, run, lock)
    task_ids = cuckoo_communicator.start_run_for_zip_and_get_task_id(path_to_zip)
    output_cuckoo_path = set_output_cuckoo_path(run)
    cuckoo_communicator.busy_waiting_for_task_completion_and_fetch_results(task_ids, output_cuckoo_path)


def init(lock):
    global git_lock
    git_lock = lock
    db.init_app(app)
    app.app_context().push()


def get_zip_for_upload(project: Project, run: Run, lock) -> str:
    if project.git_managed:
        return package_zip_for_upload(project, run, lock)
    else:
        return run.user_submitted_artifact_path


def set_output_cuckoo_path(run: Run) -> str:
    pass
