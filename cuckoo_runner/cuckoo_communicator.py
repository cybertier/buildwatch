import logging
import os
import time
from typing import List
from app import app
from models.project import Project
import requests

headers = {'Authorization': f'Bearer {app.config["CUCKOO_API_TOKEN"]}'}
base_url = app.config["CUCKOO_API_URL"]


def start_run_for_zip_and_get_task_ids(zip_path: str, project: Project) -> List[int]:
    task_ids = []
    for i in range(project.cuckoo_analysis_per_run):
        task_id = create_task(zip_path)
        task_ids.append(task_id)
    return task_ids


def create_task(zip_path):
    url = base_url + "/tasks/create/file"
    multipart_form_data = {
        'file': ('custom_file_name.zip', zip_path),
        'package': 'buildwatch'
    }
    result = requests.post(url, files=multipart_form_data, headers=headers)
    task_id: int = result.json()["task_id"]
    return task_id


def busy_waiting_for_task_completion_and_fetch_results(task_ids: List[int], output_folder: str):
    pending_task_ids = task_ids.copy()
    start_time = time.time()
    while time.time() - start_time < app.config['TIME_OUT_WAITING_FOR_CUCKOO']:
        time.sleep(app.config['DELAY_CHECKING_CUCKOO_TASK_STATUS'])
        check_tasks_states_and_fetch_data_if_finished(pending_task_ids, output_folder)
        if not pending_task_ids:
            return
    raise Exception("cuckoo run timed out as it was not finished after 3 hours")


def is_task_finished(id: int):
    url = f"{base_url}/tasks/view/{id}"
    response = requests.get(url, headers=headers)
    task = response.json()["task"]
    errors = task["errors"]
    if errors:
        raise Exception(f"Cuckoo task with id {id} failed because of errors {errors}")
    status = task["status"]
    logging.info(f"Task with id {id} has status {status}")
    return status == "reported"


def check_tasks_states_and_fetch_data_if_finished(pending_task_ids: List[int], output_folder: str):
    for task_id in pending_task_ids:
        finished = is_task_finished(task_id)
        if finished:
            pending_task_ids.remove(task_id)
            save_artifacts(task_id, output_folder)


def save_artifacts(task_id: int, output_folder: str):
    url = f"{base_url}/tasks/report/{task_id}/stix"
    response = requests.get(url, headers=headers)
    if response.status_code == 404:
        raise Exception(f"No stix report for task{task_id} even after status was reported")
    file = open(os.path.join(output_folder, f"stix_{task_id}.json", "wb"))
    file.write(response.content)

    url = f"{base_url}/tasks/report/{task_id}/programlog"
    response = requests.get(url, headers=headers)
    if response.status_code == 404:
        logging.info(f"No program log found for task with id {task_id}")
        return
    file = open(os.path.join(output_folder, f"program_log_{task_id}.log", "wb"))
    file.write(response.content)
