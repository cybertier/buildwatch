import json
import logging
import os
from pathlib import Path
from typing import Tuple, Dict, List

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


def fill_render_object_for_group(render_object: Dict[str, List[Tuple[str, str]]], group, all_objects):
    group_name = group.name.replace("_", " ")
    render_object[group_name] = []
    for element in all_objects:
        if not element["id"] in group["object_refs"]:
            continue
        if not element["type"] in to_identifiers:
            continue
        get_identifier_function = to_identifiers[element["type"]]
        identifiers = get_identifier_function(element)
        render_object[group_name].append((process_identifiers(identifiers),
                                          element.serialize(pretty=False, indent=4)))


def reformat_result(report_object):
    render_object: Dict[str, List[Tuple[str, str]]] = {}
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
