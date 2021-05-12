import logging
import json
from pathlib import Path
from typing import List, Dict
import time
from pprint import pprint
import concurrent.futures
from .domain_type import process_domain_type
from .file_type import process_file_type
from .process_type import process_process_type

log = logging.getLogger(__name__)


def pattern_generation(objects_per_type: Dict[str, List],
                       objects_per_run: Dict[int, Dict[str, List]],
                       output_file: Path, old_patterns_file: Path):

    tasks = []
    patterns = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        for object in objects_per_type:
            tasks.append(executor.submit(get_patterns, object, objects_per_type, objects_per_run))

    for task in concurrent.futures.as_completed(tasks):
        patterns.update(task.result())

    if old_patterns_file:
        log.info('Merging old patterns from %s', old_patterns_file)
        with open(old_patterns_file, 'r') as f:
            old_patterns = json.load(f)
            for key in patterns:
                patterns[key] += old_patterns[key]

    with open(output_file, 'w') as f:
        json.dump(patterns, f, indent=2)


def get_patterns(
        object: str,
        objects_per_type: Dict[str, List],
        objects_per_run: Dict[int, Dict[str, List]]) -> Dict[str, List]:

    patterns = []
    log.info('Startet generating patterns for %s', object)
    if objects_per_type[object]:
        if object in ['files_written', 'files_read', 'files_removed']:
            patterns = process_file_type(objects_per_type[object], objects_per_run, object)
        elif object == 'processes_created':
            patterns = process_process_type(objects_per_type[object], objects_per_run)
        elif object == 'domains_connected':
            patterns = process_domain_type(objects_per_type[object], objects_per_run)

    log.info('Done with %s', object)
    return {object: patterns}
