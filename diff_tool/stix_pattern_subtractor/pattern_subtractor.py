#!/usr/bin/env python3
import itertools
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
    p = Path("/home/ruben/Desktop/result.json")
    p.write_text(bundle.serialize(indent=4))
    print_results(bundle)


def subtract_pattern_after_loading_files(stix_report_path, patterns_path):
    stix_report, patterns = load_stix_report_and_patterns(stix_report_path, patterns_path)
    if hasattr(stix_report, "objects"):
        objects_by_type = parse_stix_objects(stix_report.objects)
        objects_to_delete = find_objects_matching_patterns(objects_by_type, patterns)
        remaining_objects = delete_objects(objects_to_delete, stix_report)
        groupings, analysis = get_groupings_and_analysis_object(remaining_objects)
        objects_by_grouping_name = place_objects_in_respective_groupings(
            remaining_objects, groupings
        )
        all_stix_objects = replace_old_references(objects_by_grouping_name, groupings, analysis)
        return stix2.Bundle(
            type="bundle",
            id="bundle--" + str(uuid1()),
            objects=all_stix_objects,
            allow_custom=True,
        )
    else:
        return stix2.Bundle(
            type="bundle",
            id="bundle--" + str(uuid1()),
            objects=[],
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


def parse_stix_objects(stix_objects: List) -> Dict[str, Dict[str, Any]]:
    objects_by_type = {"domain-name": {}, "file": {}, "process": {}, "ip-addr": {}}
    for stix_object in stix_objects:
        if stix_object.type == "domain-name":
            observation_expression = (
                f"domain-name:value = '{stix_object.value}' "
                f"OR domain-name:resolves_to_str = '{stix_object.resolves_to_str}'"
            )
            objects_by_type = add_object_by_type(
                objects_by_type, "domain-name", observation_expression, stix_object
            )
        if stix_object.type == "ipv4-addr" or stix_object.type == "ipv6-addr":
            observation_expression = stix_object.value
            objects_by_type = add_object_by_type(
                objects_by_type, "ip-addr", observation_expression, stix_object
            )
        if stix_object.type == "file":
            observation_expression = (
                f"file:parent_directory_str MATCHES '{stix_object.parent_directory_str}' "
                f"AND file:name MATCHES '{stix_object.name}'"
            )
            objects_by_type = add_object_by_type(
                objects_by_type, "file", observation_expression, stix_object
            )
        if stix_object.type == "process":
            observation_expression = f"process:command_line MATCHES '{stix_object.command_line}'"
            objects_by_type = add_object_by_type(
                objects_by_type, "process", observation_expression, stix_object
            )
    return objects_by_type


def add_object_by_type(
    objects_by_type: Dict[str, Dict[str, List]], key: str, observation_expression: str, stix_object
) -> Dict[str, Dict[str, List]]:
    if observation_expression in objects_by_type[key].keys():
        objects_by_type[key][observation_expression].append(stix_object)
    else:
        objects_by_type[key].update({observation_expression: [stix_object]})
    return objects_by_type


def find_objects_matching_patterns(
    objects_by_type: Dict[str, Dict[str, Any]], patterns: stix2.Bundle
) -> List:
    objects_to_delete = []
    indicators: List[stix2.Indicator] = patterns.objects
    for indicator in indicators:
        pattern = indicator.pattern[1:-1]
        matched_objects = find_stix_objects(objects_by_type, pattern)
        objects_to_delete.extend(matched_objects)
    return objects_to_delete


def find_stix_objects(objects_by_type: Dict[str, Dict[str, Any]], pattern: str) -> List:
    objects_to_delete = []
    if "domain-name" in pattern:
        for obj in objects_by_type.get("domain-name", []):
            if domain_name_object_matches(pattern, obj):
                objects_to_delete.extend(objects_by_type["domain-name"][obj])
                ip_string = objects_by_type["domain-name"][obj][0].resolves_to_str
                if ip_string in objects_by_type["ip-addr"]:
                    objects_to_delete.extend(objects_by_type["ip-addr"][ip_string])
    if "file" in pattern:
        return find_stix_object_by_type(objects_by_type, "file", pattern)
    if "process" in pattern:
        return find_stix_object_by_type(objects_by_type, "process", pattern)
    return objects_to_delete


def domain_name_object_matches(pattern, obj) -> bool:
    return Any(
        [re.search(expression.replace("\\\\", "\\"), obj) for expression in pattern.split(" OR ")]
    )


def find_stix_object_by_type(
    objects_by_type: Dict[str, Dict[str, Any]], type: str, pattern
) -> List:
    objects_to_delete = []
    for obj in objects_by_type.get(type, []):
        pattern = pattern.replace("\\\\", "\\").replace("\\\\]", "]")
        if re.fullmatch(pattern, obj):
            objects_to_delete.extend(objects_by_type[type][obj])
    return objects_to_delete


def delete_objects(objects_to_delete: List, stix_report: stix2.Bundle) -> List:
    remaining_objects = stix_report.objects.copy()
    for obj, old_obj in itertools.product(objects_to_delete, stix_report.objects):
        if obj.id == old_obj.id:
            try:
                remaining_objects.remove(old_obj)
            except ValueError:
                logging.debug(f"Object apparently was already removed:\n{old_obj}")
            if old_obj.type == "file":
                if has_no_siblings(remaining_objects, old_obj):
                    # all files who were inside the parent directory got deleted -> delete dir object
                    remaining_objects = delete_parent_dir_object(remaining_objects, old_obj)
    return remaining_objects


# File objects that share the same parent_dir_str are siblings
def has_no_siblings(remaining_objects: List, old_obj: stix2.File) -> bool:
    for new_object in remaining_objects:
        if new_object.type == "file":
            if new_object.parent_directory_str == old_obj.parent_directory_str:
                if not new_object.name == old_obj.name:
                    return False
    return True


def delete_parent_dir_object(remaining_objects: List, old_obj: stix2.File) -> List:
    parent = delete_parent_and_clones(remaining_objects, old_obj)
    if parent and has_no_siblings(remaining_objects, parent):
        remaining_objects = delete_parent_dir_object(remaining_objects, parent)
    return remaining_objects


def delete_parent_and_clones(remaining_objects: List, old_obj: stix2.File):
    expected_dir = "/".join(old_obj.parent_directory_str.split("/")[:-1])
    expected_name = old_obj.parent_directory_str.split("/")[-1]

    if expected_dir == "":
        expected_dir = "/"
    clone = None
    for new_object in remaining_objects.copy():
        if new_object.type == "file":
            if (
                new_object.parent_directory_str == expected_dir
                and new_object.name == expected_name
            ):
                remaining_objects.remove(new_object)
                clone = new_object
    return clone


def get_groupings_and_analysis_object(
    remaining_objects: List,
) -> Tuple[List[stix2.Grouping], stix2.MalwareAnalysis]:
    groupings = []
    analysis = None
    for obj in remaining_objects.copy():
        if obj.type == "grouping":
            groupings.append(obj)
            remaining_objects.remove(obj)
        elif obj.type == "malware-analysis":
            analysis = obj
            remaining_objects.remove(obj)
    return groupings, analysis


def place_objects_in_respective_groupings(
    remaining_objects: List, groupings: List[stix2.Grouping]
) -> Dict[str, List]:
    objects_by_grouping_name = {}
    for grouping in groupings:
        objects_by_grouping_name.update({grouping.name: []})
    for _del, grouping in itertools.product(remaining_objects, groupings):
        if _del.id in grouping.object_refs:
            objects_by_grouping_name[grouping.name].append(_del)
    return objects_by_grouping_name


def replace_old_references(
    objects_by_grouping_name: Dict[str, List],
    groupings: List[stix2.Grouping],
    analysis: stix2.MalwareAnalysis,
) -> List:
    all_stix_objects = []
    remaining_groupings = []
    for grouping in groupings:
        if objects_by_grouping_name[grouping.name]:
            remaining_groupings.append(
                grouping.new_version(object_refs=objects_by_grouping_name[grouping.name])
            )
            all_stix_objects.extend(objects_by_grouping_name[grouping.name])

    if all_stix_objects:
        new_analysis = analysis.new_version(analysis_sco_refs=all_stix_objects)
        all_stix_objects.append(new_analysis)

    for grouping in remaining_groupings:
        if objects_by_grouping_name[grouping.name]:
            all_stix_objects.append(grouping)
    return all_stix_objects


def print_results(bundle: stix2.Bundle):
    print("Remaining Stix Objects:")
    if hasattr(bundle, "objects"):
        for obj in bundle.objects:
            if obj.type == "file":
                print(f"File: {obj.name}")
            if obj.type == "process":
                print(f"Process: {obj.command_line}")
            if obj.type == "domain-name":
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
