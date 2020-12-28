from typing import List
from app import app
from models.project import Project
import requests

headers = {'Authorization': f'Bearer {app.config["CUCKOO_API_TOKEN"]}'}


def start_run_for_zip_and_get_task_ids(zip_path: str, project: Project) -> List[int]:
    url = app.config["CUCKOO_API_URL"] + "/tasks/create/file"
    multipart_form_data = {
        'file': ('custom_file_name.zip', open(zip_path, 'rb')),
        'package': 'buildwatch'
    }
    result = requests.post(url, files=multipart_form_data)
    return []


def busy_waiting_for_task_completion_and_fetch_results(task_ids: List[int], out_put_folder: str):
    pass