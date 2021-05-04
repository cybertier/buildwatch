import glob
import json
import logging
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import List, Optional

from app import app
from db import db
from models.project import Project
from models.run import Run

def merge_reports(output_folder:str, merge_clean=False):
    if merge_clean:
        all_json_files = glob.glob(f"{output_folder}/*_cleaned.json")
    else:
        all_json_files = glob.glob(f"{output_folder}/*.json")
    merged_artifacts = {}

    for key in json.load(open(all_json_files[0], 'r')).keys():
        for artifact_file in all_json_files:
            merged_artifacts[key] = merged_artifacts.get(key, []) + json.load(open(artifact_file, 'r'))[key]
        merged_artifacts[key] = list(set(merged_artifacts[key]))

    return merged_artifacts


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
    new_reports = glob.glob(f"{run.cuckoo_output_path}/*.json")

    if previous_run:
        assure_correct_status_of_previous_run(previous_run)

        # load everything
        known_artifacts = merge_reports(run.previous_run.cuckoo_output_path)
        with open(f'{run.previous_run.patterson_output_path}/patterns.json', 'r') as patternfile:
            known_patterns = json.load(patternfile)

        # compile patterns
        for key in known_patterns:
            known_patterns[key] = [re.compile(pattern) for pattern in known_patterns[key]]
    else:
        # we know nothing
        known_artifacts = {}
        known_patterns = {}

    # this will hold the cleaned report
    clean = {}

    # for each report remove exact and pattern matches
    keys = json.load(open(new_reports[0], 'r')).keys()
    for new_report in new_reports:
        for key in keys:
            clean[key] = []
            current_report = json.load(open(new_report, 'r'))
            for artifact in current_report[key]:
                if artifact in known_artifacts.get(key, []) or any([re.search(pattern, artifact) for pattern in known_patterns.get(key, [])]):
                    continue
                clean[key].append(artifact)

        with open(f'{new_report.split(".json")[0]}_cleaned.json', 'w') as outfile:
            json.dump(clean, outfile, indent=2)

    write_result(merge_reports(run.cuckoo_output_path, merge_clean=True), run)
    set_run_status(run, "finished_unprepared")
    logging.info('diff tool done')

def set_run_status(run, status):
    run.status = status
    db.session.commit()


def assure_correct_status_of_previous_run(previous_run: Run):
    start_time = time.time()
    timeout: int = app.config["TIME_OUT_WAITING_FOR_PREVIOUS_COMMIT"]
    while time.time() - start_time < timeout:
        db.session.refresh(previous_run)
        if (
            previous_run.status == "finished_prepared"
            or previous_run.status == "first_finished_prepared"
        ):
            return
        if previous_run.status == "error" or previous_run.error:
            raise Exception(
                f"Previous run has an error '{previous_run.error}', therefore we can not built a report. Resolve the error in run {previous_run.id}"
            )
        time.sleep(app.config["DELAY_CHECKING_PREVIOUS_TASK_STATUS"])
        logging.info(f"Previous run has not yet finished, status:{previous_run.status}")
    else:
        logging.warning(
            f"Timeout exceeded for waiting for previous run to get prepared status, status:{previous_run.status}"
        )

def write_result(result, run):
    output_path = os.path.join(app.config["PROJECT_STORAGE_DIRECTORY"], "run", str(run.id))
    file_path = os.path.join(output_path, "final_report.json")
    with Path(file_path).open("w") as outfile:
        json.dump(result, outfile, indent=2)
    run.diff_tool_output_path = output_path
    db.session.commit()


if __name__ == "__main__":
    run(int(sys.argv[1]))
