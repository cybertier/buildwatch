import itertools
import logging
from pathlib import Path
from typing import List, Dict, Set

import stix2
import yaml
from stix2patterns.validator import run_validator

from .domain_type import process_domain_type
from .file_type import process_file_type
from .helper_functions import conf
from .process_type import process_process_type

log = logging.getLogger(__name__)


def pattern_generation(
    accumulated_objects,
    accumulated_reports: List[List[stix2.ObservedData]],
    output_directory: Path,
):
    patterns = get_patterns(accumulated_objects, accumulated_reports)
    #matched_all_reports, remaining_patterns = build_pattern_compositions(
    #    patterns, accumulated_reports
    #)
    stix_pkg = create_stix_package(output_directory, patterns)
    if stix_pkg:
        with open(output_directory, "w") as f:
            f.write(stix_pkg)


def get_patterns(accumulated_objects, accumulated_reports):
    patterns = {"file_patterns": [], "process_patterns": [], "domain_patterns": []}
    if "file" in accumulated_objects:
        patterns["file_patterns"] = generate_patterns_for_files(
            accumulated_objects, accumulated_reports
        )
    if "process" in accumulated_objects:
        patterns["process_patterns"] = generate_patterns_for_processes(
            accumulated_objects, accumulated_reports
        )
    if "domain-name" in accumulated_objects:
        patterns["domain_patterns"] = generate_patterns_for_domainnames(
            accumulated_objects, accumulated_reports
        )
    return patterns


def generate_patterns_for_files(accumulated_objects, accumulated_reports):
    log.debug("Started processing files")
    try:
        file_patterns = process_file_type(accumulated_objects, accumulated_reports)
        log.debug("File-Patterns:\n" + yaml.dump(file_patterns))
        return file_patterns
    except Exception as error:
        log.exception(f"Exception during pattern generation of type 'file'. {error}")
        return []


def generate_patterns_for_processes(accumulated_objects, accumulated_reports):
    log.debug("Started processing processes")
    try:
        process_patterns = process_process_type(accumulated_objects, accumulated_reports)
        log.debug("Process-Patterns:\n" + yaml.dump(process_patterns))
        return process_patterns
    except Exception as error:
        log.exception(f"Exception during pattern generation of type 'process'. {error}")
        return []


def generate_patterns_for_domainnames(accumulated_objects, accumulated_reports):
    log.debug("Started processing domains")
    try:
        domain_patterns = process_domain_type(
            accumulated_objects["domain-name"], accumulated_reports
        )
        log.debug("Domain-Patterns:\n" + yaml.dump(domain_patterns))
        return domain_patterns
    except Exception as error:
        log.exception(f"Exception during pattern generation of type 'domain-name'. {error}")
        return []


def build_pattern_compositions(patterns, accumulated_reports):
    occur_together = find_patterns_that_occur_together(patterns)
    if not occur_together:
        log.debug("No patterns occured together during multiple runs.")
    remove_patterns_if_occured_together(patterns, occur_together)
    matched_all_reports, remaining_patterns = find_patterns_that_match_all_reports(
        accumulated_reports, patterns, occur_together
    )
    return matched_all_reports, remaining_patterns


def find_patterns_that_occur_together(patterns: Dict[str, List]) -> List[Set]:
    combined_patterns = (
        patterns.get("file_patterns", [])
        + patterns.get("process_patterns", [])
        + patterns.get("domain_patterns", [])
    )
    occur_together = []

    for pat1, pat2 in itertools.combinations(combined_patterns, 2):
        if set(pat1.matched_reports) == set(pat2.matched_reports):
            if {pat1, pat2} not in occur_together and {
                pat2,
                pat1,
            } not in occur_together:
                occur_together.append({pat1, pat2})
    return merge_pattern_pairs(occur_together)


def merge_pattern_pairs(pattern_pairs: List[Set]) -> List[Set]:
    # merge pairs together, e.g. if A and B always occur together,
    # and B and C occur always together, then A and C always occur together.
    # A AND B, B AND C --> A AND B AND C     [remove A,B and B,C -- insert A,B,C]  # noqa
    occur_together = pattern_pairs
    changed = True
    while changed:
        changed = False
        for set1, set2 in itertools.combinations(occur_together, 2):
            items_from_set1_in_set2 = [item for item in set1 if item in set2]
            if items_from_set1_in_set2:
                occur_together.remove(set1)
                occur_together.remove(set2)
                new_set = set()
                for obj in set1.union(set2):
                    new_set.add(obj)
                occur_together.append(new_set)
                changed = True
                break
    return occur_together


def remove_patterns_if_occured_together(patterns_dict, occur_together):
    for pattern_type, patterns in patterns_dict.items():
        for pattern_pair in occur_together:
            for p in patterns:
                if p in pattern_pair:
                    patterns_dict[pattern_type].remove(p)


def find_patterns_that_match_all_reports(accumulated_reports, patterns, occur_together):
    combined_patterns = (
        patterns.get("file_patterns", [])
        + patterns.get("process_patterns", [])
        + patterns.get("domain_patterns", [])
    )
    matched_all_reports = []
    remaining_patterns = []

    for pat in combined_patterns:
        match_ratio = pat.match_ratio(accumulated_reports)
        if match_ratio == 1.0:
            matched_all_reports.append(pat)
        elif pat.match_ratio(accumulated_reports) > conf.match_ratio_threshold:
            remaining_patterns.append(pat)

    for gathered_patterns in occur_together:
        and_comp = []
        for pat in gathered_patterns:
            if pat.match_ratio(accumulated_reports) == 1.0:
                matched_all_reports.append(pat)
            elif pat.match_ratio(accumulated_reports) > conf.match_ratio_threshold:
                and_comp.append(pat)
        if and_comp:
            remaining_patterns.append(and_comp)
    return matched_all_reports, remaining_patterns


def create_stix_package(output_directory, patterns):
    #pattern = join_patterns_that_occur_in_all_reports(matched_all_reports)
    sample_name = output_directory.stem
    #stix_indicator = get_stix2_indicator_from_pattern(pattern, sample_name, "1.0")

    indicators = []
    #if stix_indicator:
    #    patterns.append(stix_indicator)

    for type in patterns.keys():
        for element in patterns[type]:
        #if isinstance(element, list):
        #    indicator = get_indicators_from_list_of_patterns(sample_name, element)
        #    if indicator:
        #        indicators.append(indicator)
        #else:
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


def join_patterns_that_occur_in_all_reports(matched_all_reports):
    and_comp = []
    for pattern in matched_all_reports:
        and_comp.append(pattern.observation_expression())
    return " AND ".join(and_comp).replace("\\", "\\\\")


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


def get_indicators_from_list_of_patterns(sample_name, element):
    and_comp = []
    for pattern in element:
        and_comp.append(pattern.observation_expression())
    pattern = " AND ".join(and_comp).replace("\\", "\\\\")
    indicator = get_stix2_indicator_from_pattern(pattern, sample_name, element[0].match_ratio())
    return indicator
