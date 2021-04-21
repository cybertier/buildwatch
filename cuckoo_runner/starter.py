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
    p = Process(target=child, args=(run_id, lock), )
    p.daemon = False
    p.start()


def child(run_id, git_lock):
    from cuckoo_runner.runner import run
    import logging
    from app import app
    target_dir = os.path.join(app.config['PROJECT_STORAGE_DIRECTORY'], 'run', str(run_id))
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    logging.basicConfig(filename=os.path.join(target_dir, "cuckoo_runner.log"), level=logging.DEBUG)
    formatter = logging.Formatter(f'%(asctime)s-CR({run_id})-%(levelname)s-%(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logging.getLogger().addHandler(ch)
    logging.info(f"Cuckoo runner running in fork for id {run_id}")
    run(run_id, git_lock)
    logging.info(f"Cuckoo runner finished and is now terminating")
    exit(0)
