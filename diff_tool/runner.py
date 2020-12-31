import glob
import logging
import ntpath
import os
import shutil
import time
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
    assure_correct_status_of_previous_run(previous_run)
    path_of_current_report: str = get_path_current_report(run)
    path_of_reports: List[str] = get_list_of_reports_from_previous_run(previous_run)
    pattern_path: str = get_pattern_of_previous_run(previous_run)
    subtract_observables_from_old_run(path_of_current_report, path_of_reports)
    subtract_pattern_from_old_run(path_of_current_report, pattern_path)
    set_run_status(run, "finished_unprepared")


def set_run_status(run, status):
    run.status = status
    db.session.commit()


def assure_correct_status_of_previous_run(previous_run: Run):
    if previous_run.status == "error" or previous_run.error:
        raise Exception(
            f"Previous run has an error '{previous_run.error}', therefore we can not built a report. Resolve the error in run {previous_run.id}")
    start_time = time.time()
    timeout: int = app.config['TIME_OUT_WAITING_FOR_PREVIOUS_COMMIT']
    while time.time() - start_time < timeout:
        if previous_run.status == "finished_prepared":
            return
        time.sleep(app.config['DELAY_CHECKING_PREVIOUS_TASK_STATUS'])
        logging.info(f"Previous run has not yet finished, status:{previous_run.status}")


def get_pattern_of_previous_run(run: Run):
    path_pattern_dir = run.patterson_output_path
    all_json_files = glob.glob(f"{path_pattern_dir}/*.json")
    if len(all_json_files) != 1:
        raise Exception(
            f"Expected 1 json pattern file in {path_pattern_dir} but found the following files: {all_json_files}")
    return all_json_files[0]


def get_list_of_reports_from_previous_run(run: Run):
    cuckoo_output_path: str = run.cuckoo_output_path
    all_json_files = glob.glob(f"{cuckoo_output_path}/*.json")
    if len(all_json_files) < 3:
        raise Exception(f"Found less than 3 json files in the cuckoo_output_path({cuckoo_output_path})."
                        f"Something is wrong with previous run of id {run.id}."
                        f"Only found {all_json_files}")
    return all_json_files


def subtract_observables_from_old_run(path_of_current_reports, path_of_reports):
    # TODO: implement
    pass


def get_path_current_report(run: Run):
    cuckoo_output_path = run.cuckoo_output_path
    all_json_files = glob.glob(f"{cuckoo_output_path}/*.json")
    if len(all_json_files) < 3:
        raise Exception(f"Found less than 3 json files in the cuckoo_output_path({cuckoo_output_path})."
                        f"Something is wrong with current run of id {run.id}."
                        f"Only found {all_json_files}")
    input_report = cuckoo_output_path[0]
    return create_copy_in_diff_tool_out_put_path_and_return_path(input_report, run)


def create_copy_in_diff_tool_out_put_path_and_return_path(input_report, run: Run):
    diff_tool_output_dir = os.path.join(app.config['PROJECT_STORAGE_DIRECTORY'],
                                        'run', str(run.id), 'diff_tool_out_put')
    if not os.path.exists(diff_tool_output_dir):
        os.makedirs(diff_tool_output_dir)
    copied_to = os.path.join(diff_tool_output_dir, ntpath.basename(input_report))
    shutil.copy2(input_report, copied_to)
    return copied_to


def subtract_pattern_from_old_run(current_report_path, pattern_path):
    result = subtract_pattern_after_loading_files(current_report_path, pattern_path)

    # TODO: serialize result somehow
