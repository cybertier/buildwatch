import os
from multiprocessing import Process
import multiprocessing


def start(run_id: int):
    multiprocessing.set_start_method('spawn')
    p = Process(target=child, args=(run_id,), )
    p.daemon = False
    p.start()


def child(run_id):
    from cuckoo_runner.runner import run
    import logging
    from app import app
    target_dir = os.path.join(app.config['PROJECT_STORAGE_DIRECTORY'], 'cuckoo_runner_logs', str(run_id))
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    logging.basicConfig(filename=os.path.join(target_dir, "runner.log"), level=logging.DEBUG)
    logging.info(f"Cuckoo runner running in fork for id {run_id}")
    run(run_id)
    logging.info(f"Cuckoo runner finished and is now terminating")
    exit(0)
