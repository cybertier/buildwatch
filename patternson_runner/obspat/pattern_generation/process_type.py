import itertools
import logging
import re
from typing import Dict, List

from .gen_regex import regex_from_tree, resolve_quantifier
from .helper_functions import nested_set_for_processes

log = logging.getLogger(__name__)


def process_process_type(
    processes: List[str], objects_per_run: Dict[int, Dict[str, List]]
) -> List[str]:
    same_across_reports = get_same_processes_across_reports(objects_per_run)
    same_cmd_lines = filter_too_rare_objects(same_across_reports, len(objects_per_run.keys()))

    cmd_lines = []
    for process in processes:
        if process not in same_cmd_lines:
            cmd_lines.append(process)

    regex_cmd_lines = get_cmd_line_regexes(cmd_lines, same_cmd_lines)
    finished_regexes = sanitize_regexes(regex_cmd_lines, processes)
    return finished_regexes


def get_same_processes_across_reports(
    objects_per_run: Dict[int, Dict[str, List]]
) -> Dict[str, Dict[str, List[int]]]:
    same_across_reports = {}
    for id_1, id_2 in itertools.combinations(objects_per_run.keys(), 2):
        if id_1 != id_2:
            processes_1 = objects_per_run[id_1]["processes_created"]
            processes_2 = objects_per_run[id_2]["processes_created"]
            for p1 in processes_1:
                for p2 in processes_2:
                    if p1 == p2:
                        ocurred_reports = same_across_reports.get(p1, [])
                        if id_1 not in ocurred_reports:
                            ocurred_reports.append(id_1)
                        if id_2 not in ocurred_reports:
                            ocurred_reports.append(id_2)
                        same_across_reports[p1] = ocurred_reports
    return same_across_reports


def filter_too_rare_objects(
    same_across_reports: Dict[str, Dict[str, List[int]]], number_of_reports: int
) -> List[str]:
    same_cmd_lines = []
    for obj in list(same_across_reports.keys()):
        if len(same_across_reports[obj]) < (number_of_reports * 1 / 3):
            del same_across_reports[obj]
        else:
            same_cmd_lines.append(obj)
    return same_cmd_lines


def get_cmd_line_regexes(cmd_lines: List[str], same_cmd_lines: List[str]) -> List[str]:
    tree = {}
    regex_cmd_lines = []
    for cmd_line in cmd_lines:
        nested_set_for_processes(tree, cmd_line.split("/"), {})
    regex_from_tree(tree, regex_cmd_lines)
    for cmd in same_cmd_lines:
        regex_cmd_lines.append(re.escape(cmd))
    return regex_cmd_lines


# resolve quantifier and remove named capture groups
def sanitize_regexes(finished_regexes: List[str], files: List[str]):
    str_lengths = {}
    for regex in finished_regexes:
        for file in files:
            match = re.match(regex, file)
            if match:
                for group_id, string in match.groupdict().items():
                    lengths = str_lengths.get(group_id, [])
                    if len(string) not in lengths:
                        lengths.append(len(string))
                    str_lengths[group_id] = lengths
    cleaned_regexes = []
    for regex in finished_regexes:
        cleaned_regexes.append(resolve_quantifier(regex, str_lengths))
    return cleaned_regexes
