#!/usr/bin/env python3
import json
import logging
import re
from argparse import ArgumentParser
from pathlib import Path
from typing import List, Tuple, Dict, Any
from uuid import uuid1

import stix2


def main():
    stix_report_path, patterns_path = parse_args()
    bundle = subtract_pattern_after_loading_files(stix_report_path, patterns_path)
    print_results(bundle)


def subtract_pattern_after_loading_files(stix_report_path, patterns_path):
    stix_report, patterns = load_stix_report_and_patterns(
        stix_report_path, patterns_path
    )
    objects_by_type = parse_stix_objects(stix_report.objects)
    objects_to_delete = []
    for indicator in patterns.objects:
        objects_to_delete.extend(
            match_pattern_and_return_objects_to_delete(objects_by_type, indicator)
        )

    # remove objtects_o-eletze from stix report
    remaining_objects = stix_report.objects.copy()
    for obj in objects_to_delete:
        for old_obj in stix_report.objects:
            if obj.id == old_obj.id:
                remaining_objects.remove(old_obj)
    for obj in remaining_objects.copy():
        if obj.type == "grouping" or obj.type == "malware-analysis":
            remaining_objects.remove(obj)

    # load groupings and malware analysis object
    groupings, analysis = get_groupings_and_analysis(stix_report)

    # check which object should be in which grouping
    group_names = {}
    for grouping in groupings:
        group_names.update({grouping.name: []})
    for _del in remaining_objects:
        for grouping in groupings:
            if _del.id in grouping.object_refs:
                group_names[grouping.name].append(_del)

    # replace old references
    all_stix_objects = []
    remaining_groupings = []
    for grouping in groupings:
        if group_names[grouping.name]:
            remaining_groupings.append(grouping.new_version(object_refs=group_names[grouping.name]))
            all_stix_objects.extend(group_names[grouping.name])

    if all_stix_objects:
        new_analysis = analysis.new_version(analysis_sco_refs=all_stix_objects)
        all_stix_objects.append(new_analysis)

    for grouping in remaining_groupings:
        if group_names[grouping.name]:
            all_stix_objects.append(grouping)

    return stix2.Bundle(
        type="bundle",
        id="bundle--" + str(uuid1()),
        objects=all_stix_objects,
        allow_custom=True,
    )


def load_stix_report_and_patterns(
    stix_report_file, patterns_file
) -> Tuple[stix2.Bundle, stix2.Bundle]:
    patterns = stix2.parse(json.load(patterns_file.open()), allow_custom=True)
    if type(stix_report_file) == stix2.Bundle:
        return stix_report_file, patterns
    stix_report = stix2.parse(json.load(stix_report_file.open()), allow_custom=True)
    return stix_report, patterns


def parse_stix_objects(stix_objects) -> Dict[str, Dict[str, Any]]:
    objects_by_type = {"domain-name": {}, "file": {}, "process": {}}
    for stix_object in stix_objects:
        if stix_object.type == "domain-name":
            object_str = (
                f"domain-name:value = '{re.escape(stix_object.value)}' "
                f"OR domain-name:resolves_to_str = '{re.escape(stix_object.resolves_to_str)}'"
            )
            if object_str in objects_by_type["domain-name"].keys():
                objects_by_type["domain-name"][object_str].append(stix_object)
            else:
                objects_by_type["domain-name"].update({object_str: [stix_object]})
        if stix_object.type == "file":
            object_str = (
                f"file:parent_directory_str MATCHES '{stix_object.parent_directory_str}' "
                f"AND file:name MATCHES '{re.escape(stix_object.name)}'"
            )
            if object_str in objects_by_type["file"].keys():
                objects_by_type["file"][object_str].append(stix_object)
            else:
                objects_by_type["file"].update({object_str: [stix_object]})
        if stix_object.type == "process":
            object_str = f"process:command_line MATCHES '{re.escape(stix_object.command_line)}'"
            if object_str in objects_by_type["process"].keys():
                objects_by_type["process"][object_str].append(stix_object)
            else:
                objects_by_type["process"].update({object_str: [stix_object]})
    return objects_by_type


def match_pattern_and_return_objects_to_delete(
    objects_by_type: Dict[str, Dict[str, Any]], indicator: stix2.Indicator
) -> List[Any]:
    if pattern_is_one_expression(indicator.pattern):
        pattern = indicator.pattern[1:-1]
        objects_to_delete = find_stix_objects(objects_by_type, pattern)
    else:
        patterns = split_pattern(indicator.pattern)
        objects_to_delete = find_all_objects_to_delete(objects_by_type, patterns)
    return objects_to_delete


def split_pattern(pattern: str) -> List[str]:
    multiple_objects = pattern.split("] AND [")
    patterns = []
    for pattern in multiple_objects:
        pattern = pattern.replace("[", "").replace("]", "")
        patterns.append(pattern)
    return patterns


def pattern_is_one_expression(pattern: str) -> bool:
    if len(pattern.split("] AND [")) > 1:
        return False
    return True


def find_stix_objects(objects_by_type: Dict[str, Dict[str, Any]], pattern) -> List[Any]:
    objects_to_delete = []
    if "domain-name" in pattern:
        expressions = pattern.split(" OR ")
        for obj in objects_by_type["domain-name"]:
            for pattern in expressions:
                regex = re.compile(pattern)
                if re.search(regex, obj):
                    objects_to_delete.extend(objects_by_type["domain-name"][obj])
    if "file" in pattern:
        return find_stix_object_by_type(objects_by_type, "file", pattern)
    if "process" in pattern:
        return find_stix_object_by_type(objects_by_type, "process", pattern)
    return objects_to_delete


def find_stix_object_by_type(
    objects_by_type: Dict[str, Dict[str, Any]], type: str, pattern
) -> List[Any]:
    objects_to_delete = []
    for obj in objects_by_type[type]:
        regex = re.compile(pattern)
        if re.search(regex, obj):
            objects_to_delete.extend(objects_by_type[type][obj])
    return objects_to_delete


def find_all_objects_to_delete(
    objects_by_type: Dict[str, Dict[str, Any]], patterns
) -> List[str]:
    all_objects_to_delete = []
    for pattern in patterns:
        objects_to_delete = find_stix_objects(objects_by_type, pattern)
        if objects_to_delete:
            all_objects_to_delete.extend(objects_to_delete)
        else:
            logging.debug(f"Pattern could not be matched on any STIX object: {pattern}")
    return all_objects_to_delete


def get_groupings_and_analysis(stix_report):
    groupings = []
    analysis = None

    for object in stix_report.objects:
        if object.type == "grouping":
            groupings.append(object)
        if object.type == "malware-analysis":
            analysis = object
    return groupings, analysis


def print_results(bundle: stix2.Bundle):
    print("Remaining Stix Objects:")
    for obj in bundle.objects:
        if obj.type == "file":
            print(f"File: {obj.name}")
        if obj.type == "process":
            print(f"Process: {obj.command_line}")
        if obj.type == "domain":
            print(f"Domain: {obj.value}")


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


if __name__ == "__main__":
    main()
