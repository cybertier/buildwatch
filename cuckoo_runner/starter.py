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
    from cuckoo_runner.runner import run
    import logging
    from app import app
    target_dir = os.path.join(app.config['PROJECT_STORAGE_DIRECTORY'], 'run',
                              str(run_id))
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    logging.info('Cuckoo runner running in fork for id %s', run_id)
    run(run_id, git_lock)
    logging.info('Cuckoo runner finished and is now terminating')
    sys.exit(0)
