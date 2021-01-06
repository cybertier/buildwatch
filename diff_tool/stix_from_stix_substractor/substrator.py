import json
from pathlib import Path
from typing import List

import stix2

to_identifiers = {
    "process": lambda process: [process["command_line"]],
    "file": lambda file: [file["parent_directory_str"] + "/" + file["name"]],

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
    string = base.serialize(pretty=False, indent=4)
    path = Path(out_put_file_path)
    with path.open("w", encoding="utf-8") as out_put_file:
        out_put_file.write(string)


def delete_not_found_in_index(base, index):
    all_objects = base["objects"]
    for element in all_objects:
        if not element["type"] == "grouping":
            continue
        delete_not_found_in_index_of_group(element, index, all_objects)


def delete_not_found_in_index_of_group(group, index, all_objects):
    group_index = index[group.name]
    for element in all_objects:
        if not element["id"] in group["object_refs"]:
            continue
        if not element["type"] in to_identifiers:
            continue
        get_identifier_function = to_identifiers[element["type"]]
        identifiers = get_identifier_function(element)
        for identifier in identifiers:
            if identifier in group_index:
                remove_element(element, group, all_objects)


def remove_element(element, group, all_objects):
    group["object_refs"].remove(element.id)
    all_objects.remove(element)
