import logging
import os
from builtins import ValueError
from typing import List, Optional
from pathlib import Path
from db import db
from app import app
from models.run import Run
from patternson_runner.obspat.patternson import start_patternson
import time


def run(run_id: int):
    init()
    run = Run.query.get(run_id)
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
    start_patternson(path_of_current_reports, path_of_current_reports.with_name("patternson-output"))
    set_status_for_run_and_wait(run)


def set_status_for_run_and_wait(run):
    start_time = time.time()

    patterns_file = Path(run.cuckoo_output_path).with_name("patternson-output") / "patterns.json"
    while time.time() - start_time < app.config['TIME_OUT_WAITING_FOR_CUCKOO']:
        run = Run.query.get(run.id)
        time.sleep(app.config['DELAY_CHECKING_CUCKOO_TASK_STATUS'])
        db.session.refresh(run)
        if patterns_file.exists() and run.status == "finished_unprepared":
            set_run_status(run, "finished_prepared")
            break


def set_run_status(run, status):
    run.status = status
    db.session.commit()
