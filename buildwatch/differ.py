import glob
import json
import logging
import os
import re
import time
from pathlib import Path

from app import app
from db import db
from models.run import Run


def init():
    db.init_app(app)
    app.app_context().push()


def merge_reports(output_folder: str, merge_clean=False):
    if merge_clean:
        all_json_files = glob.glob(f'{output_folder}/*_cleaned.json')
    else:
        all_json_files = glob.glob(f'{output_folder}/*.json')
    merged_artifacts = {}

    for key in json.load(open(all_json_files[0], 'r')).keys():
        for artifact_file in all_json_files:
            merged_artifacts[key] = merged_artifacts.get(key, []) + json.load(
                open(artifact_file, 'r'))[key]
        merged_artifacts[key] = list(set(merged_artifacts[key]))

    return merged_artifacts


def cross_known(output_folder: str):
    merged_artifacts = {}
    all_json_files = glob.glob(f'{output_folder}/*.json')

    for key in json.load(open(all_json_files[0], 'r')).keys():
        tmp = []
        for index, artifact_file in enumerate(all_json_files):
            tmp.append(set(json.load(open(artifact_file, 'r'))[key]))

        merged_artifacts[key] = list(set.intersection(*tmp))

    return merged_artifacts


def set_run_status(run, status):
    run.status = status
    db.session.commit()


def assure_correct_status_of_previous_run(previous_run: Run):
    start_time = time.time()
    timeout: int = app.config['TIME_OUT_WAITING_FOR_PREVIOUS_COMMIT']
    while time.time() - start_time < timeout:
        db.session.refresh(previous_run)
        if (previous_run.status == 'finished_prepared'
                or previous_run.status == 'first_finished_prepared'):
            return
        if previous_run.status == 'error' or previous_run.error:
            raise Exception(
                f"Previous run has an error '{previous_run.error}', therefore we can not built a report. Resolve the error in run {previous_run.id}"
            )
        time.sleep(app.config['DELAY_CHECKING_PREVIOUS_TASK_STATUS'])
        logging.info('Previous run has not yet finished, status: %s',
                     previous_run.status)
    logging.warning(
        'Timeout exceeded for waiting for previous run to get prepared status, status: %s',
        previous_run.status)


def write_result(result, run):
    output_path = os.path.join(app.config['PROJECT_STORAGE_DIRECTORY'], 'run',
                               str(run.id))
    file_path = os.path.join(output_path, 'final_report.json')
    with Path(file_path).open('w') as outfile:
        json.dump(result, outfile, indent=2)
    run.diff_tool_output_path = output_path
    db.session.commit()


def calculate_diff(run: Run):
    set_run_status(run, 'diff_tool_running')
    previous_run = run.previous_run
    new_reports = glob.glob(f'{run.cuckoo_output_path}/*.json')

    if previous_run:
        assure_correct_status_of_previous_run(previous_run)

        # load everything
        known_artifacts = merge_reports(run.previous_run.cuckoo_output_path)
        with open(f'{run.previous_run.patterson_output_path}/patterns.json',
                  'r') as patternfile:
            known_patterns = json.load(patternfile)

        # compile patterns
        for key in known_patterns:
            known_patterns[key] = [
                re.compile(pattern) for pattern in known_patterns[key]
            ]
    else:
        # we know nothing
        known_artifacts = {}
        known_patterns = {}

    cross_known_artifacts = cross_known(run.cuckoo_output_path)
    # this will hold the cleaned report
    clean = {}
    cross_checked = {}

    # for each report remove exact and pattern matches
    keys = json.load(open(new_reports[0], 'r')).keys()
    for new_report in new_reports:
        for key in keys:
            clean[key] = []
            cross_checked[key] = []
            current_report = json.load(open(new_report, 'r'))
            for artifact in current_report[key]:
                if not artifact in known_artifacts.get(key, []) and not any([
                        re.match(pattern, artifact)
                        for pattern in known_patterns.get(key, [])
                ]):
                    clean[key].append(artifact)
                    if not artifact in cross_known_artifacts.get(key, []):
                        cross_checked[key].append(artifact)

        with open(f'{new_report.split(".json")[0]}_cleaned.json',
                  'w') as outfile:
            json.dump(clean, outfile, indent=2)

        with open(f'{new_report.split(".json")[0]}_cross_cleaned.json',
                  'w') as outfile:
            json.dump(cross_checked, outfile, indent=2)

    write_result(merge_reports(run.cuckoo_output_path, merge_clean=True), run)
    set_run_status(run, 'finished_unprepared')
    logging.info('diff tool done')


def run(run_id: int):
    init()
    run = Run.query.get(run_id)
    try:
        calculate_diff(run)
    except Exception as e:
        run.status = 'error'
        run.error = str(e)
        db.session.commit()
        logging.error('Something went wrong in the diff tool: %s', e)
        raise Exception('cuckoo diff tool terminated') from e
