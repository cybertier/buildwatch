import glob
import logging
import os
import shutil
import sys
import time
from pathlib import Path
from typing import List, Optional

from app import app
from db import db
from diff_tool.html_report.html_report_builder import build_html_report
from diff_tool.stix_from_stix_substractor.substractor import subtract as stix_from_stix_subtract
from diff_tool.stix_pattern_subtractor.pattern_subtractor import subtract_pattern_after_loading_files
from models.project import Project
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
        set_run_status(run, "first_finished_unprepared")
        return
    assure_correct_status_of_previous_run(previous_run)
    path_of_current_report: str = get_path_current_report(run)
    path_of_reports: List[str] = get_list_of_reports_from_previous_run(run)
    output_path = subtract_observables_from_old_run(path_of_current_report, path_of_reports, run)
    if not run.project.patternson_off:
        pattern_paths: List[str] = get_pattern_of_previous_run(run)
        subtract_pattern_from_old_runs(output_path, pattern_paths, run)
    set_run_status(run, "finished_unprepared")


def set_run_status(run, status):
    run.status = status
    db.session.commit()


def assure_correct_status_of_previous_run(previous_run: Run):
    start_time = time.time()
    timeout: int = app.config['TIME_OUT_WAITING_FOR_PREVIOUS_COMMIT']
    while time.time() - start_time < timeout:
        db.session.refresh(previous_run)
        if previous_run.status == "finished_prepared" or previous_run.status == "first_finished_prepared":
            return
        if previous_run.status == "error" or previous_run.error:
            raise Exception(
                f"Previous run has an error '{previous_run.error}', therefore we can not built a report. Resolve the error in run {previous_run.id}")
        time.sleep(app.config['DELAY_CHECKING_PREVIOUS_TASK_STATUS'])
        logging.info(f"Previous run has not yet finished, status:{previous_run.status}")
    else:
        logging.warning(
            f"Timeout exceeded for waiting for previous run to get prepared status, status:{previous_run.status}")


def get_pattern_of_previous_run(run: Run):
    all_json_files = []
    project: Project = run.project
    for i in range(project.old_runs_considered):
        run = run.previous_run
        if not run:
            break
        add_pattern_files_for_run(all_json_files, run)
    return all_json_files


def add_pattern_files_for_run(all_json_files, previous_run):
    path_pattern_dir = previous_run.patterson_output_path
    pattern_files = glob.glob(f"{path_pattern_dir}/*.json")
    if len(pattern_files) != 1:
        raise Exception(
            f"Expected 1 json pattern file in {path_pattern_dir} but found the following files: {all_json_files}")
    all_json_files.append(pattern_files[0])


def get_list_of_reports_from_previous_run(run: Run):
    all_json_files = []
    project: Project = run.project
    for i in range(project.old_runs_considered):
        run = run.previous_run
        if not run:
            break
        add_cuckoo_report_files_for_run(all_json_files, run)
    if len(all_json_files) < 3:
        raise Exception(f"Found less than 3 json files."
                        f"Only found {all_json_files}")
    return all_json_files


def add_cuckoo_report_files_for_run(all_json_files, run):
    cuckoo_output_path: str = run.cuckoo_output_path
    all_json_files.extend(glob.glob(f"{cuckoo_output_path}/*.json"))


def subtract_observables_from_old_run(path_of_current_report, path_of_reports, run):
    output_path = os.path.join(app.config['PROJECT_STORAGE_DIRECTORY'],
                               'run', str(run.id), 'diff_tool_out_put', 'simple_subtraction.json')
    logging.info(f"Subtracting {path_of_reports} from {path_of_current_report}")
    stix_from_stix_subtract(path_of_current_report, path_of_reports, output_path)
    return output_path


def get_path_current_report(run: Run):
    cuckoo_output_path = run.cuckoo_output_path
    all_json_files = glob.glob(f"{cuckoo_output_path}/*.json")
    if len(all_json_files) < 3:
        raise Exception(f"Found less than 3 json files in the cuckoo_output_path({cuckoo_output_path})."
                        f"Something is wrong with current run of id {run.id}."
                        f"Only found {all_json_files}")
    input_report = all_json_files[0]
    return create_copy_in_diff_tool_out_put_path_and_return_path(input_report, run)


def create_copy_in_diff_tool_out_put_path_and_return_path(input_report, run: Run):
    diff_tool_output_dir = os.path.join(app.config['PROJECT_STORAGE_DIRECTORY'],
                                        'run', str(run.id), 'diff_tool_out_put')
    if not os.path.exists(diff_tool_output_dir):
        os.makedirs(diff_tool_output_dir)
    copied_to = os.path.join(diff_tool_output_dir, "original_stix.json")
    shutil.copy2(input_report, copied_to)
    return copied_to


def subtract_pattern_from_old_runs(current_report_path, pattern_paths, run):
    result = subtract_pattern_after_loading_files(Path(current_report_path), Path(pattern_paths[0]))
    for i in range(len(pattern_paths) - 1):
        if "objects" not in result:
            break
        result = subtract_pattern_after_loading_files(result, Path(pattern_paths[i + 1]))
    write_result(result, run)


def write_result(result, run):
    output_path = os.path.join(app.config['PROJECT_STORAGE_DIRECTORY'],
                               'run', str(run.id), 'diff_tool_out_put')
    file_path = os.path.join(output_path, 'stix_report_final.json')
    with Path(file_path).open("w") as file:
        file.write(result.serialize(pretty=False, indent=4))
    build_html_report(result, run)
    run.diff_tool_output_path = output_path
    db.session.commit()


if __name__ == "__main__":
    run(int(sys.argv[1]))
