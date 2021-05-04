import logging
import os
import time
from typing import List

import requests
from requests_toolbelt import MultipartEncoder

from app import app
from models.project import Project

headers = {'Authorization': f'Bearer {app.config["CUCKOO_API_TOKEN"]}'}
base_url = app.config["CUCKOO_API_URL"]
whitelist_custom_path = app.config["CUSTOM_WHITELIST"]


def start_run_for_zip_and_get_task_ids(zip_path: str, project: Project) -> List[int]:
    task_ids = []
    for i in range(project.cuckoo_analysis_per_run):
        task_id = create_task(zip_path)
        task_ids.append(task_id)
    return task_ids


def load_whitelist():
    if not os.path.exists(whitelist_custom_path):
        return ""
    file = open(whitelist_custom_path)
    content = file.read()
    file.close()
    return content


def create_task(zip_path):
    url = base_url + "/tasks/create/file"
    custom_whitelist = load_whitelist()
    m = MultipartEncoder(
        fields={
            'file': ('custom_file_name.zip', open(zip_path, 'rb')),
            'package': 'buildwatch',
            'custom': custom_whitelist,
            "options": "analpath=tmpCuckoo"
        }
    )
    my_headers = headers
    my_headers["Content-Type"] = m.content_type
    result = requests.post(url, data=m, headers=my_headers)
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


def is_task_finished(task_id: int):
    url = f"{base_url}/tasks/view/{task_id}"
    response = requests.get(url, headers=headers)
    task = response.json()["task"]
    if task["errors"]:
        raise Exception(f"Cuckoo task with id {task_id} failed because of errors {task['errors']}")
    logging.info(f"Task with id {task_id} has status {task['status']}")
    return task['status'] == "reported"


def check_tasks_states_and_fetch_data_if_finished(pending_task_ids: List[int], output_folder: str):
    for task_id in pending_task_ids:
        if is_task_finished(task_id):
            pending_task_ids.remove(task_id)
            save_artifacts(task_id, output_folder)


def save_artifacts(task_id: int, output_folder: str):
    url = f"{base_url}/tasks/report/{task_id}/artifacts"
    response = requests.get(url, headers=headers)
    if response.status_code == 404:
        raise Exception(f"No artifacts extracted for task{task_id} even after status was reported")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    with open(os.path.join(output_folder, f"artifacts_{task_id}.json"), "wb") as outfile:
        outfile.write(response.content)

    url = f"{base_url}/tasks/report/{task_id}/programlog"
    response = requests.get(url, headers=headers)
    if response.status_code == 404:
        logging.info(f"No program log found for task with id {task_id}")
        return
    with open(os.path.join(output_folder, f"program_log_{task_id}.log"), "wb") as outfile:
        outfile.write(response.content)
