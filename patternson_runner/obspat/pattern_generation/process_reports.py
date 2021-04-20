import logging
from pathlib import Path
from typing import List, Dict

import stix2
from multiprocessing import Pool
from .domain_type import process_domain_type
from .file_type import process_file_type
from .process_type import process_process_type

log = logging.getLogger(__name__)


def pattern_generation(
    objects_per_type: Dict[str, List],
    objects_per_run: Dict[int, Dict[str, List]],
    output_directory: Path,
):
    patterns = get_patterns(objects_per_type, objects_per_run)
    stix_pkg = create_stix_package(output_directory, patterns)
    if stix_pkg:
        with open(output_directory, "w") as f:
            f.write(stix_pkg)


def get_patterns(
    objects_per_type: Dict[str, List], objects_per_run: Dict[int, Dict[str, List]]
) -> Dict[str, List]:
    patterns = {"file_patterns": [], "process_patterns": [], "domain_patterns": []}
    if "file" in objects_per_type:
        log.info("Startet generating patterns for files")
        patterns["file_patterns"] = process_file_type(objects_per_type["file"], objects_per_run)
    if "process" in objects_per_type:
        log.info("Startet generating patterns for processes")
        patterns["process_patterns"] = process_process_type(
            objects_per_type["process"], objects_per_run
        )
    if "domain-name" in objects_per_type:
        log.info("Startet generating patterns for domains")
        patterns["domain_patterns"] = process_domain_type(objects_per_type["domain-name"])
    return patterns


def create_stix_package(output_directory, patterns: Dict[str, List]) -> str:
    sample_name = output_directory.stem

    indicators = []

    for type in patterns.keys():
        for element in patterns[type]:
            indicators.append(
                stix2.Indicator(
                    labels=[sample_name],
                    pattern=element.replace("\\", "\\\\"),
                    pattern_type="stix",
                )
            )

    if not indicators:
        log.info(f"No indicators could be inferred for {output_directory}")
        return f"No indicators could be inferred for {output_directory}"

    return stix2.Bundle(objects=indicators).serialize(sort_keys=False, indent=4)
