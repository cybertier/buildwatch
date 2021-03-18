import logging
import os
import time
from pathlib import Path

from app import app
from db import db
from models.run import Run
from patternson_runner.obspat.patternson import start_patternson


def run(run_id: int):
    init()
    run = Run.query.get(run_id)
    if run.project.patternson_off:
        logging.info("patternson turned off for this project")
        set_status_for_run_and_wait(run)
        db.session.commit()
    else:
        try:
            actual_procedure(run)
        except Exception as e:
            run.status = "error"
            run.error = str(e)
            db.session.commit()
            logging.error(f"Something went wrong in the patternson runner tool: {e}")
            raise Exception("patternson terminated") from e


def init():
    db.init_app(app)
    app.app_context().push()


def actual_procedure(run: Run):
    path_of_current_reports: Path = Path(run.cuckoo_output_path)
    create_patternson_path(run)
    start_patternson(path_of_current_reports, path_of_current_reports.with_name("patternson-output"), run.id)
    set_status_for_run_and_wait(run)


def create_patternson_path(run: Run):
    output_dir = os.path.join(app.config['PROJECT_STORAGE_DIRECTORY'], 'run', str(run.id), 'patternson-output')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    run.patterson_output_path = output_dir
    db.session.commit()


def set_status_for_run_and_wait(run):
    start_time = time.time()

    patterns_file = Path(run.cuckoo_output_path).with_name("patternson-output") / "patterns.json"
    while time.time() - start_time < app.config['TIME_OUT_WAITING_FOR_CUCKOO']:
        run = Run.query.get(run.id)
        time.sleep(app.config['DELAY_CHECKING_CUCKOO_TASK_STATUS'])
        db.session.refresh(run)
        if patterns_file.exists() or run.project.patternson_off:
            if run.status == "finished_unprepared":
                set_run_status(run, "finished_prepared")
                break
            elif run.status == "first_finished_unprepared":
                set_run_status(run, "first_finished_prepared")
                break


def set_run_status(run, status):
    run.status = status
    db.session.commit()
