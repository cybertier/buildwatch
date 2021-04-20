import json
import logging
import os
from pathlib import Path
from typing import Tuple, Dict, List, Set

import stix2
from jinja2 import Environment, select_autoescape, FileSystemLoader

from app import app
from db import db
from diff_tool.stix_from_stix_substractor.substractor import to_identifiers
from models.run import Run


def process_identifiers(identifiers) -> str:
    if len(identifiers) == 1:
        return identifiers[0]
    else:
        return f"{identifiers[0]} | {identifiers[1]}"


def fill_render_object_for_group(render_object: Dict[str, List[any]], group, all_objects):
    group_name = group.name.replace("_", " ")
    render_object[group_name] = [list(), 0]
    identifiers_already_used = list()
    for element in all_objects:
        if not element["id"] in group["object_refs"]:
            continue
        if not element["type"] in to_identifiers:
            continue
        add_to_render_objects(element, group_name, identifiers_already_used, render_object)


def get_or_create_directory(directory, last_traveled_directory, group):
    if last_traveled_directory is None:
        already_existing_directory = [x for x in group if x[0] == directory and type(x[1]) == list]
        if already_existing_directory:
            return already_existing_directory[0]
        else:
            newly_created_directory = [directory, list(), 0]
            group.append(newly_created_directory)
            return newly_created_directory
    list_of_items_of_last_traveled_directory = last_traveled_directory[1]
    already_existing_directory_in_list_of_items_of_last_traveled_directory = [x for x in
                                                                              list_of_items_of_last_traveled_directory
                                                                              if x[0] == directory and type(x[1]) == list]
    if already_existing_directory_in_list_of_items_of_last_traveled_directory:
        return already_existing_directory_in_list_of_items_of_last_traveled_directory[0]
    else:
        newly_created_directory = [directory, list(), 0]
        list_of_items_of_last_traveled_directory.append(newly_created_directory)
        return newly_created_directory


def get_and_Increment_directory(directory, last_traveled_directory, group_item_list):
    if last_traveled_directory is None:
        already_existing_directory = [x for x in group_item_list if x[0] == directory and type(x[1]) == list]
        if already_existing_directory:
            already_existing_directory[0][2] += 1
            return already_existing_directory[0]

    list_of_items_of_last_traveled_directory = last_traveled_directory[1]
    already_existing_directory_in_list_of_items_of_last_traveled_directory = [x for x in
                                                                              list_of_items_of_last_traveled_directory
                                                                              if x[0] == directory and type(x[1]) == list]
    if already_existing_directory_in_list_of_items_of_last_traveled_directory:
        already_existing_directory_in_list_of_items_of_last_traveled_directory[0][2] += 1
        return already_existing_directory_in_list_of_items_of_last_traveled_directory[0]


def increment_directories(element, group_item_list, group):
    parent_directory = element["parent_directory_str"]
    parent_directory_split = parent_directory.split("/")
    last_traveled_directory = None
    for directory in parent_directory_split:
        if not directory:
            group[1] += 1
            continue
        last_traveled_directory = get_and_Increment_directory(directory, last_traveled_directory, group_item_list)


def add_item_to_directory(element, last_traveled_directory, group_item_list, group):
    items = last_traveled_directory[1]
    file_name = element["name"]
    old_list = [x for x in items if x[0] == file_name]
    if old_list:
        old_list = old_list[0]
        if type(old_list[1]) == list:
            return
        items.append([file_name,
                      element.serialize(pretty=False, indent=4) + "\n" + old_list[1]
                         , old_list[2] + 1])
        items.remove(old_list)
    else:
        items.append([file_name,
                      element.serialize(pretty=False, indent=4)
                         , 1])
        increment_directories(element, group_item_list, group)


def add_to_render_objects(element, group_name, identifiers_already_used, render_object):
    get_identifier_function = to_identifiers[element["type"]]
    identifiers = get_identifier_function(element)
    identifier = process_identifiers(identifiers)

    group = render_object[group_name]
    group_item_list = group[0]
    if element["type"] == "file":
        parent_directory = element["parent_directory_str"]
        parent_directory_split = parent_directory.split("/")
        last_traveled_directory = None
        for directory in parent_directory_split:
            if not directory:
                continue
            last_traveled_directory = get_or_create_directory(directory, last_traveled_directory, group_item_list)
        if last_traveled_directory is None:
            add_item_root_level(element, group_item_list, group_name, identifier, identifiers_already_used,
                                render_object)
            return

        add_item_to_directory(element, last_traveled_directory, group_item_list, group)
        return

    add_item_root_level(element, group_item_list, group_name, identifier, identifiers_already_used, render_object)


def add_item_root_level(element, group_item_list, group_name, identifier, identifiers_already_used, render_object):
    if identifier in identifiers_already_used:
        old_list = [x for x in group_item_list if x[0] == identifier][0]
        already_existing_stix_object = old_list[1]
        group_item_list.remove(old_list)
        group_item_list.append([identifier,
                                element.serialize(pretty=False, indent=4) + "\n" + already_existing_stix_object
                                   , old_list[2] + 1])
    else:
        group_item_list.append([identifier,
                                element.serialize(pretty=False, indent=4), 1])
        identifiers_already_used.append(identifier)
        render_object[group_name][1] = render_object[group_name][1] + 1


def reformat_result(report_object):
    render_object: Dict[str, Set[Tuple[str, str]]] = {}
    if "objects" not in report_object:
        return render_object
    all_objects = report_object["objects"]
    for element in all_objects:
        if not element["type"] == "grouping":
            continue
        fill_render_object_for_group(render_object, element, all_objects)
    return render_object


def build_html_report(report_object, run):
    output_path = os.path.join(app.config['PROJECT_STORAGE_DIRECTORY'],
                               'run', str(run.id), 'diff_tool_out_put', 'report.html')
    build_html_report_to_path(output_path, report_object, run)


def build_html_report_to_path(output_path, report_object, run):
    render_object = reformat_result(report_object)
    env = Environment(
        loader=FileSystemLoader('templates'),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template('report.html')
    result = template.render(run=run, objects=render_object)
    logging.info(f"Writing the html report to {output_path}")
    with Path(output_path).open("w") as file:
        file.write(result)


if __name__ == '__main__':
    stix_report = stix2.parse(json.load(Path("diff_tool/html_report/sample.json").open()), allow_custom=True)
    db.init_app(app)
    app.app_context().push()
    run = Run.query.get(1)
    build_html_report_to_path("report.html", stix_report, run)
