import logging
import os
from typing import List, Optional

from db import db
from app import app
from diff_tool.stix_pattern_subtractor.pattern_subtractor import subtract_pattern_after_loading_files
from models.run import Run


def run(run_id: int):
    init()
    run = Run.query.get(run_id)
    try:
        actual_procedure(run)
    except Exception as e:
        run.status = "error"
        run.error = str(e)
        db.session.commit()
        logging.error(f"Something went wrong in the diff tool: {e}")
        raise Exception("cuckoo diff tool terminated") from e


def init():
    db.init_app(app)
    app.app_context().push()


def actual_procedure(run: Run):
    set_run_status(run, "diff_tool_running")
    previous_run: Optional[Run] = run.previous_run
    if not previous_run:
        logging.info(f"There is no previous run, so no need for the diff tool to run")
        set_run_status(run, "finished_unprepared")
        return
    path_of_current_reports: str = get_path_current_report(run)
    path_of_reports: List[str] = get_list_of_reports_from_previous_run(previous_run)
    pattern_path: str = get_pattern_of_previous_run(previous_run)
    subtract_observables_from_old_run(path_of_current_reports, path_of_reports)
    subtract_pattern_from_old_run(pattern_path, path_of_reports)
    update_run(run, path_of_current_reports)


def set_run_status(run, status):
    run.status = status
    db.session.commit()


def get_pattern_of_previous_run(run: Run):
    pass


def get_list_of_reports_from_previous_run(run: Run):
    # cuckoo_output_path: str = previous_run.cuckoo_output_path
    # for root, dirs, files in os.walk(cuckoo_output_path):
    pass


def subtract_observables_from_old_run(path_of_current_reports, path_of_reports):
    pass


def get_path_current_report(run: Run):
    pass


def subtract_pattern_from_old_run(pattern_path, path_of_reports):
    # subtract_pattern_after_loading_files()
    pass


def update_run(run: Run, path_of_current_reports):
    # TODO : rest
    set_run_status(run, "finished_unprepared")

