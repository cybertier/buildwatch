import multiprocessing
import os
import sys
from multiprocessing import Process


def start(run_id: int):
    multiprocessing.set_start_method('spawn', force=True)
    p = Process(target=child, args=(run_id,))
    p.daemon = False
    p.start()


def child(run_id):
    from patternson_runner.runner import run
    import logging
    from app import app
    target_dir = os.path.join(app.config['PROJECT_STORAGE_DIRECTORY'], 'run', str(run_id))
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    logging.basicConfig(filename=os.path.join(target_dir, "patternson.log"), level=logging.DEBUG)
    formatter = logging.Formatter(f'PR({run_id})-%(levelname)s-%(message)s')
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logging.getLogger().addHandler(ch)
    logging.info(f"Patternson running in fork for id {run_id}")
    run(run_id)
    logging.info(f"Patternson finished and is now terminating")
    exit(0)
