import itertools
import logging
import re
from typing import Dict, List

from .gen_regex import regex_from_tree
from .helper_functions import nested_set_for_processes, ProcessData

log = logging.getLogger(__name__)


def process_process_type(
    processes: List[ProcessData], objects_per_run: Dict[int, Dict[str, List]]
) -> List[str]:
    same_across_reports = get_same_processes_across_reports(objects_per_run)
    same_cmd_lines = filter_too_rare_objects(same_across_reports, len(objects_per_run.keys()))
    regex_cmd_lines = get_cmd_line_regexes(processes, same_cmd_lines)
    return [f"[process:command_line MATCHES '{regex}']" for regex in regex_cmd_lines]


def get_same_processes_across_reports(
    objects_per_run: Dict[int, Dict[str, List]]
) -> Dict[str, List[int]]:
    same_across_reports = {}
    for id_1, id_2 in itertools.combinations(objects_per_run.keys(), 2):
        if id_1 != id_2:
            for p1, p2 in itertools.product(
                objects_per_run[id_1]["process"], objects_per_run[id_2]["process"]
            ):
                if p1.cmd == p2.cmd:
                    same_across_reports[p1.cmd] = add_report_ids_where_process_occured(
                        same_across_reports.get(p1.cmd, []), id_1, id_2
                    )
    return same_across_reports


def add_report_ids_where_process_occured(ocurred_reports: List, id_1: int, id_2: int) -> List[int]:
    if id_1 not in ocurred_reports:
        ocurred_reports.append(id_1)
    if id_2 not in ocurred_reports:
        ocurred_reports.append(id_2)
    return ocurred_reports


def filter_too_rare_objects(
    same_across_reports: Dict[str, List[int]], number_of_reports: int
) -> List[str]:
    same_cmd_lines = []
    for obj in same_across_reports.keys():
        if len(same_across_reports[obj]) < (number_of_reports / 3):
            del same_across_reports[obj]
        else:
            same_cmd_lines.append(obj)
    return same_cmd_lines


def get_cmd_line_regexes(processes: List[ProcessData], same_cmd_lines: List[str]) -> List[str]:
    cmd_lines = [process.cmd for process in processes if process.cmd not in same_cmd_lines]
    tree = {}
    for cmd_line in cmd_lines:
        nested_set_for_processes(tree, cmd_line.split("/"), {})

    regex_cmd_lines = []
    regex_from_tree(tree, regex_cmd_lines)
    for cmd in same_cmd_lines:
        regex_cmd_lines.append(re.escape(cmd))
    return regex_cmd_lines
