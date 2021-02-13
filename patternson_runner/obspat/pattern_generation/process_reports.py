import logging
from pathlib import Path
from typing import List, Dict, Any

import stix2
import yaml
from stix2patterns.validator import run_validator

from .domain_type import process_domain_type, DomainPattern
from .file_type import process_file_type, FilePattern
from .process_type import process_process_type, ProcessPattern

log = logging.getLogger(__name__)


def pattern_generation(
    accumulated_objects: Dict[str, List[Dict[str, Any]]],
    accumulated_reports: List[List[stix2.ObservedData]],
    output_directory: Path,
):
    patterns = get_patterns(accumulated_objects, len(accumulated_reports))
    stix_pkg = create_stix_package(output_directory, patterns)
    if stix_pkg:
        with open(output_directory, "w") as f:
            f.write(stix_pkg)


def get_patterns(
    accumulated_objects: Dict[str, List[Dict[str, Any]]], number_of_reports: int
) -> Dict[str, List]:
    patterns = {"file_patterns": [], "process_patterns": [], "domain_patterns": []}
    if "file" in accumulated_objects:
        patterns["file_patterns"] = generate_patterns_for_files(
            accumulated_objects, number_of_reports
        )
    if "process" in accumulated_objects:
        patterns["process_patterns"] = generate_patterns_for_processes(
            accumulated_objects, number_of_reports
        )
    if "domain-name" in accumulated_objects:
        patterns["domain_patterns"] = generate_patterns_for_domainnames(
            accumulated_objects, number_of_reports
        )
    return patterns


def generate_patterns_for_files(
    accumulated_objects: Dict[str, List[Dict[str, Any]]], number_of_reports: int
) -> List[FilePattern]:
    log.debug("Started processing files")
    try:
        file_patterns = process_file_type(accumulated_objects, number_of_reports)
        log.debug("File-Patterns:\n" + yaml.dump(file_patterns))
        return file_patterns
    except Exception as error:
        log.exception(f"Exception during pattern generation of type 'file'. {error}")
        return []


def generate_patterns_for_processes(
    accumulated_objects: Dict[str, List[Dict[str, Any]]], number_of_reports: int
) -> List[ProcessPattern]:
    log.debug("Started processing processes")
    try:
        process_patterns = process_process_type(accumulated_objects, number_of_reports)
        log.debug("Process-Patterns:\n" + yaml.dump(process_patterns))
        return process_patterns
    except Exception as error:
        log.exception(f"Exception during pattern generation of type 'process'. {error}")
        return []


def generate_patterns_for_domainnames(
    accumulated_objects: Dict[str, List[Dict[str, Any]]], number_of_reports: int
) -> List[DomainPattern]:
    log.debug("Started processing domains")
    try:
        domain_patterns = process_domain_type(
            accumulated_objects["domain-name"], number_of_reports
        )
        log.debug("Domain-Patterns:\n" + yaml.dump(domain_patterns))
        return domain_patterns
    except Exception as error:
        log.exception(f"Exception during pattern generation of type 'domain-name'. {error}")
        return []


def create_stix_package(output_directory, patterns):
    sample_name = output_directory.stem

    indicators = []

    for type in patterns.keys():
        for element in patterns[type]:
            pattern = element.observation_expression().replace("\\", "\\\\")
            indicator = get_stix2_indicator_from_pattern(
                pattern, sample_name, element.match_ratio()
            )
            if indicator:
                indicators.append(indicator)

    if not indicators:
        log.info(f"No indicators could be inferred for {output_directory}")
        return None

    return stix2.Bundle(objects=indicators).serialize(sort_keys=False, indent=4)


def get_stix2_indicator_from_pattern(pattern, sample_name, match_ratio):
    if pattern:
        errors = run_validator(pattern)
        if not errors:
            indicator = stix2.Indicator(
                labels=[sample_name, f"match-ratio: {match_ratio}"],
                pattern=pattern,
                pattern_type="stix",
            )
            return indicator
        else:
            log.error(f"Invalid pattern generated. Pattern: {pattern}\n" f"Errors: {errors}")
