import logging
import json
from pathlib import Path
from typing import List, Dict
from .domain_type import process_domain_type
from .file_type import process_file_type
from .process_type import process_process_type

log = logging.getLogger(__name__)


def pattern_generation(
    objects_per_type: Dict[str, List],
    objects_per_run: Dict[int, Dict[str, List]],
    output_file: Path,
    old_patterns_file: Path
):
    patterns = get_patterns(objects_per_type, objects_per_run)
    # import yaml

    # print(yaml.dump(patterns))

    if old_patterns_file:
        log.info('Merging old patterns from %s', old_patterns_file)
        with open(old_patterns_file, "r") as f:
            old_patterns = json.load(f)
            for key in patterns:
                patterns[key] += old_patterns[key]


    with open(output_file, "w") as f:
        f.write(json.dumps(patterns, indent=2))


def get_patterns(
    objects_per_type: Dict[str, List], objects_per_run: Dict[int, Dict[str, List]]
) -> Dict[str, List]:
    patterns = {
        "files_written": [],
        "files_read": [],
        "files_removed": [],
        "processes_created": [],
        "hosts_connected": [],
    }
    if objects_per_type["files_written"]:
        log.info("Startet generating patterns for files_written")
        patterns["files_written"] = process_file_type(
            objects_per_type["files_written"], objects_per_run, "files_written"
        )
    if objects_per_type["files_read"]:
        log.info("Startet generating patterns for files_read")
        patterns["files_read"] = process_file_type(
            objects_per_type["files_read"], objects_per_run, "files_read"
        )
    if objects_per_type["files_removed"]:
        log.info("Startet generating patterns for files_removed")
        patterns["files_removed"] = process_file_type(
            objects_per_type["files_removed"], objects_per_run, "files_removed"
        )
    if objects_per_type["processes_created"]:
        log.info("Startet generating patterns for processes")
        patterns["processes_created"] = process_process_type(
            objects_per_type["processes_created"], objects_per_run
        )
    if objects_per_type["domains_connected"]:
        log.info("Startet generating patterns for domains")
        patterns["hosts_connected"] = process_domain_type(
            objects_per_type["domains_connected"], objects_per_run
        )
    return patterns
