import multiprocessing
import os
import sys
from multiprocessing import Process

lock = None


def start(run_id: int):
    global lock
    if lock is None:
        lock = multiprocessing.Manager().Lock()
    multiprocessing.set_start_method('spawn', force=True)
    p = Process(
        target=child,
        args=(run_id, lock),
    )
    p.daemon = False
    p.start()


def child(run_id, git_lock):
    from buildwatch.runner import run
    import logging
    from app import app
    target_dir = os.path.join(app.config['PROJECT_STORAGE_DIRECTORY'], 'run',
                              str(run_id))
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    logging.info('buildwatch running in fork for id %s', run_id)
    run(run_id, git_lock)
    logging.info('buildwatch finished and is now terminating')
    sys.exit(0)
