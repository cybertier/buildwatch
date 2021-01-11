import logging
import os
from multiprocessing import Lock

from app import app
from cuckoo_runner import cuckoo_communicator
from cuckoo_runner.git_repo_preparer import package_zip_for_upload
from db import db
from diff_tool.starter import start as start_diff_tool
from models.project import Project
from models.run import Run
from patternson_runner.starter import start as run_patternson


def run(run_id: int, lock: Lock):
    init()
    run = Run.query.get(run_id)
    try:
        actual_procedure(lock, run)
    except Exception as e:
        run.status = "error"
        run.error = str(e)
        db.session.commit()
        logging.error(f"Something went wrong in the cuckoo runner: {e}")
        raise Exception("cuckoo runner terminated") from e


def actual_procedure(lock, run):
    project = run.project
    path_to_zip = get_zip_for_upload(project, run, lock)
    task_ids = cuckoo_communicator.start_run_for_zip_and_get_task_ids(path_to_zip, project)
    set_run_status_to_cuckoo_running(run)
    output_cuckoo_path = set_output_cuckoo_path(run)
    cuckoo_communicator.busy_waiting_for_task_completion_and_fetch_results(task_ids, output_cuckoo_path)
    start_diff_tool(run.id)
    run_patternson(run.id)


def init():
    db.init_app(app)
    app.app_context().push()


def get_zip_for_upload(project: Project, run: Run, lock) -> str:
    if project.git_managed:
        return package_zip_for_upload(project, run, lock)
    else:
        return run.user_submitted_artifact_path


def set_run_status_to_cuckoo_running(run):
    run.status = "cuckoo_running"
    db.session.commit()


def set_output_cuckoo_path(run: Run) -> str:
    output_dir = os.path.join(app.config['PROJECT_STORAGE_DIRECTORY'], 'run', str(run.id), 'cuckoo')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    run.cuckoo_output_path = output_dir
    db.session.commit()
    return output_dir
