import os
from multiprocessing import Lock, synchronize

import git

from db import db
from app import app
from models.project import Project
from models.run import Run
import logging
from git import Repo

git_lock: synchronize.Lock


def run(run_id: int, lock: Lock):
    init(lock)
    run = Run.query.get(run_id)
    project = run.project
    path_to_zip = get_zip_for_upload(project, run)


def init(lock):
    global git_lock
    git_lock = lock
    db.init_app(app)
    app.app_context().push()


def get_zip_for_upload(project: Project, run: Run) -> str:
    if not project.git_managed:
        return package_zip_for_upload(project)
    else:
        return run.user_submitted_artifact_path


def checkout_correct_commit(repo: Repo, run: Run):
    pass


def zip_repo(repo: Repo) -> str:
    pass


def package_zip_for_upload(project: Project) -> str:
    repo: Repo = initialize_git_if_needed(project)
    checkout_correct_commit(repo)
    return zip_repo(repo)


def initialize_git_if_needed(project: Project) -> Repo:
    base_dir = os.path.join(app.config['PROJECT_STORAGE_DIRECTORY'], 'project', str(project.id))
    repo_dir = os.path.join(os.path.join(base_dir, "git_repo"))
    if os.path.exists(repo_dir):
        return Repo(repo_dir)
    return clone_repo(project, repo_dir)


def clone_repo(project: Project, repo_dir: str) -> Repo:
    git_lock.acquire()
    try:
        logging.info(f"Repo for project {project.name} did not yet exist, creating it.")
        os.makedirs(repo_dir)
        project.git_checkout_path = repo_dir
        git.Git(project.git_checkout_path).clone(project.git_url, ".")
        db.session.commit()
        return Repo(repo_dir)
    finally:
        git_lock.release()