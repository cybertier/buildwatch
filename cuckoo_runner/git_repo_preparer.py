import logging
from git import Repo

import git
import typing
import os
import zipfile

from db import db
from app import app
from models.project import Project
from models.run import Run

git_lock = None


def checkout_correct_commit(repo: Repo, run: Run):
    repo.git.fetch()
    repo.git.checkout(run.user_set_identifier)
    logging.info(f"Checked out commit {repo.head.commit}")


def zip_repo(repo: Repo, run: Run) -> str:

    target_zip = os.path.join(app.config['PROJECT_STORAGE_DIRECTORY'], 'run', str(run.id), "input.zip")
    if not os.path.exists(os.path.dirname(target_zip)):
        os.makedirs(os.path.dirname(target_zip))
    zip_file = zipfile.ZipFile(target_zip, 'w', zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk(repo.working_dir):
        zip_file.write(root, os.path.relpath(root, repo.working_dir))
        for file in files:
            zip_file.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), repo.working_dir))
    return target_zip


def package_zip_for_upload(project: Project, run: Run, lock) -> str:
    global git_lock
    git_lock = lock
    repo: Repo = initialize_git_if_needed(project)
    git_lock.acquire()
    try:
        checkout_correct_commit(repo, run)
        determine_previous_commit_for_git_run(run, repo)
        return zip_repo(repo, run)
    finally:
        git_lock.release()


def initialize_git_if_needed(project: Project) -> Repo:
    base_dir = os.path.join(app.config['PROJECT_STORAGE_DIRECTORY'], 'project', str(project.id))
    repo_dir = os.path.join(os.path.join(base_dir, "git_repo"))
    if os.path.exists(repo_dir):
        return Repo(repo_dir)
    return clone_repo(project, repo_dir)


def clone_repo(project: Project, repo_dir: str) -> Repo:
    logging.info(f"Repo for project {project.name} did not yet exist, creating it.")
    os.makedirs(repo_dir)
    project.git_checkout_path = repo_dir
    git.Git(project.git_checkout_path).clone(project.git_url, ".")
    db.session.commit()
    return Repo(repo_dir)


def determine_previous_commit_for_git_run(run: Run, repo: Repo):
    commit_to_id_dictionary = get_id_and_commit_hash_for_runs_in_project(run.project)
    for item in repo.iter_commits(rev='HEAD'):
        if str(item) in commit_to_id_dictionary:
            previous_run_id = commit_to_id_dictionary[str(item)]
            logging.info(f"Identified previous commit as {previous_run_id}")
            run.previous_run_id = previous_run_id
            db.session.commit()
            return
    logging.info("No previous commit found that was a run")


def get_id_and_commit_hash_for_runs_in_project(project: Project) -> typing.Dict[str, int]:
    commit_to_id: typing.Dict[str, int] = {}
    all_runs = Run.query.all()
    for run in all_runs:
        commit_to_id[run.user_set_identifier] = run.id
    return commit_to_id
