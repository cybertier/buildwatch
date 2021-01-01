#!/usr/bin/env python3
import json
import logging
import re
from pathlib import Path
from argparse import ArgumentParser
import stix2
from typing import List, Tuple, Dict, Any


def main():
    stix_report_path, patterns_path = parse_args()
    results = subtract_pattern_after_loading_files(stix_report_path, patterns_path)
    print_results(results)


def subtract_pattern_after_loading_files(stix_report_path, patterns_path):
    stix_report, patterns = load_stix_report_and_patterns(stix_report_path, patterns_path)
    return mach_pattern_against_stix_report(patterns, stix_report)


def mach_pattern_against_stix_report(patterns, stix_report):
    objects_by_type = parse_stix_objects(stix_report.objects)
    for indicator in patterns.objects:
        objects_by_type = match_pattern(objects_by_type, indicator)
    return objects_by_type


def load_stix_report_and_patterns(stix_report_file, patterns_file) -> Tuple[stix2.Bundle, stix2.Bundle]:
    patterns = stix2.parse(json.load(patterns_file.open()), allow_custom=True)
    stix_report = stix2.parse(json.load(stix_report_file.open()), allow_custom=True)
    return stix_report, patterns


def parse_args() -> Tuple[Path, Path]:
    parser = ArgumentParser()
    parser.add_argument(
        "report", help="A JSON file containing a STIX2 Bundle containing STIX2 Objects"
    )
    parser.add_argument(
        "patterns",
        help="A JSON file containing a STIX2 Bundle containing Indicator Objects",
    )
    args = parser.parse_args()
    return Path(args.report), Path(args.patterns)


def parse_stix_objects(stix_objects) -> Dict[str, Dict[str, Any]]:
    objects_by_type = {"domain-name": {}, "file": {}, "process": {}}
    for stix_object in stix_objects:
        if stix_object.type == "domain-name":
            object_str = (
                f"domain-name:value = '{stix_object.value}' "
                f"OR domain-name:resolves_to_str = '{stix_object.resolves_to_str}'"
            )
            objects_by_type["domain-name"].update({object_str: stix_object})
        if stix_object.type == "file":
            object_str = (
                f"file:parent_directory_str MATCHES '{stix_object.parent_directory_str}' "
                f"AND file:name MATCHES '{stix_object.name}'"
            )
            objects_by_type["file"].update({object_str: stix_object})
        if stix_object.type == "process":
            object_str = f"process:command_line MATCHES {stix_object.command_line}"
            objects_by_type["process"].update({object_str: stix_object})
    return objects_by_type


def match_pattern(
    objects_by_type: Dict[str, Dict[str, Any]], indicator: stix2.Indicator
) -> Dict[str, Dict[str, Any]]:
    if pattern_is_one_expression(indicator.pattern):
        objects_by_type = delete_objects_matching_pattern(objects_by_type, indicator)
    else:
        objects_by_type = delete_objects_matching_patterns(objects_by_type, indicator)
    return objects_by_type


def pattern_is_one_expression(pattern: str) -> bool:
    if len(pattern.split("] AND [")) > 1:
        return False
    return True


def delete_objects_matching_pattern(
    objects_by_type: Dict[str, Dict[str, Any]], indicator: stix2.Indicator
):
    pattern = indicator.pattern.replace("[", "").replace("]", "")
    objects_to_delete = find_stix_objects(objects_by_type, pattern)
    return remove_matching_objects(objects_by_type, objects_to_delete)


def delete_objects_matching_patterns(
    objects_by_type: Dict[str, Dict[str, Any]], indicator: stix2.Indicator
):
    patterns = split_pattern(indicator.pattern)
    try:
        objects_to_delete = find_all_objects_to_delete(objects_by_type, patterns)
        return remove_matching_objects(objects_by_type, objects_to_delete)
    except ValueError as e:
        logging.debug(f"Failed to match pattern {indicator.pattern}\n{e}")


def split_pattern(pattern: str) -> List[str]:
    multiple_objects = pattern.split("] AND [")
    patterns = []
    for pattern in multiple_objects:
        pattern = pattern.replace("[", "").replace("]", "")
        patterns.append(pattern)
    return patterns


def find_all_objects_to_delete(
    objects_by_type: Dict[str, Dict[str, Any]], patterns
) -> List[str]:
    all_objects_to_delete = []
    for pattern in patterns:
        objects_to_delete = find_stix_objects(objects_by_type, pattern)
        if objects_to_delete:
            all_objects_to_delete.extend(objects_to_delete)
        else:
            logging.debug(
                f"Pattern could not be matched on any STIX object: {pattern}"
            )
    return all_objects_to_delete


def find_stix_objects(objects_by_type: Dict[str, Dict[str, Any]], pattern) -> List[str]:
    objects_to_delete = []
    if "domain-name" in pattern:
        expressions = pattern.split(" OR ")
        for obj in objects_by_type["domain-name"]:
            for pattern in expressions:
                regex = re.compile(pattern)
                if re.search(regex, obj):
                    objects_to_delete.append(obj)
    if "file" in pattern:
        return find_stix_object_by_type(objects_by_type, "file", pattern)
    if "process" in pattern:
        return find_stix_object_by_type(objects_by_type, "process", pattern)
    return objects_to_delete


def find_stix_object_by_type(
    objects_by_type: Dict[str, Dict[str, Any]], type: str, pattern
) -> List[str]:
    objects_to_delete = []
    for obj in objects_by_type[type]:
        regex = re.compile(pattern)
        if re.search(regex, obj):
            objects_to_delete.append(obj)
    return objects_to_delete


def remove_matching_objects(
    objects_by_type: Dict[str, Dict[str, Any]], objects_to_delete: List[str]
) -> Dict[str, Dict[str, Any]]:
    temp = objects_by_type.copy()
    for type, objects in temp.items():
        tmp = objects.copy()
        for object_str in tmp:
            if object_str in objects_to_delete:
                del temp[type][object_str]
    return temp


def print_results(objects_by_type: Dict[str, Dict[str, Any]]):
    print("Remaining Stix Objects by type:")
    for type, objects in objects_by_type.items():
        if objects:
            print(f"\nType: {type}")
            for object in objects.values():
                print(object)


if __name__ == "__main__":
    main()
