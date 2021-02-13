import json
import logging
from pathlib import Path
from typing import List

import stix2

to_identifiers = {
    "process": lambda process: [process["command_line"]],
    "file": lambda file: [file["parent_directory_str"] + "/" + file["name"]],
    "domain-name": lambda domain: [domain["value"], domain["resolves_to_str"]],
    "ipv6-addr": lambda ip: [ip["value"]],
    "ipv4-addr": lambda ip: [ip["value"]]
}


def subtract(base_stix_file_path: str, subtract_file_path: List[str], out_put_file_path: str):
    base, list_of_old_runs = load_files(base_stix_file_path, subtract_file_path)
    index = {}
    for run in list_of_old_runs:
        build_index(run, index)
    delete_not_found_in_index(base, index)
    write_result(base, out_put_file_path)


def load_files(base_stix_file_path: str, subtract_file_paths: List[str]):
    subtract = []
    for path in subtract_file_paths:
        subtract.append(stix2.parse(json.load(Path(path).open()), allow_custom=True))
    base = stix2.parse(json.load(Path(base_stix_file_path).open()), allow_custom=True)
    return base, subtract


def build_index(subtract: stix2.Bundle, index):
    all_objects = subtract["objects"]
    for element in all_objects:
        if not element["type"] == "grouping":
            continue
        index[element["name"]] = index_elements_of_group(element, all_objects)


def index_elements_of_group(group, all_objects):
    index = set()
    for element in all_objects:
        if not element["id"] in group["object_refs"]:
            continue
        if not element["type"] in to_identifiers:
            continue
        get_identifier_function = to_identifiers[element["type"]]
        index.update(get_identifier_function(element))
    return index


def write_result(base: stix2.Bundle, out_put_file_path):
    for obj in base.objects.copy():
        if obj.type == "grouping":
            if not obj.object_refs:
                base.objects.remove(obj)
    for obj in base.objects.copy():
        if obj.type == "malware-analysis":
            if not obj.analysis_sco_refs:
                base.objects.remove(obj)
    string = base.serialize(pretty=False, indent=4)
    path = Path(out_put_file_path)
    with path.open("w", encoding="utf-8") as out_put_file:
        out_put_file.write(string)


def delete_not_found_in_index(base, index):
    all_objects = base["objects"]
    malware_object = None
    for element in all_objects.copy():
        if not element["type"] == "malware-analysis":
            continue
        malware_object = element
        break
    if not malware_object:
        raise Exception("There was no malware analysis object on the report")
    for element in all_objects.copy():
        if not element["type"] == "grouping":
            continue
        logging.debug(f"Looking at group {element.name}")
        delete_not_found_in_index_of_group(element, index, all_objects, malware_object)


def delete_not_found_in_index_of_group(group, index, all_objects, malware_object):
    if not (group.name in index):
        return
    group_index = index[group.name]
    for element in all_objects.copy():
        if not element["id"] in group["object_refs"]:
            continue
        if not element["type"] in to_identifiers:
            continue
        get_identifier_function = to_identifiers[element["type"]]
        identifiers = get_identifier_function(element)
        for identifier in identifiers:
            if identifier.startswith("//"):
                identifier = identifier[1:]
            if identifier in group_index:
                if element.id not in group["object_refs"]:
                    logging.debug(f"Object is already removed: UUID = {element.id}")
                    continue
                logging.debug(f"Found object with identifier {identifier} and id {element.id} that can be filtered out")
                remove_element(element, group, all_objects, malware_object)


def remove_element(element, group, all_objects, malware_object):
    group["object_refs"].remove(element.id)
    all_objects.remove(element)
    malware_object["analysis_sco_refs"].remove(element.id)
