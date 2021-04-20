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

    cmd_lines = []
    for process in processes:
        if process.cmd not in same_cmd_lines:
            cmd_lines.append(process.cmd)

    regex_cmd_lines = get_cmd_line_regexes(cmd_lines, same_cmd_lines)
    return return_observation_expressions(regex_cmd_lines)


def get_same_processes_across_reports(
    objects_per_run: Dict[int, Dict[str, List]]
) -> Dict[str, Dict[str, List[int]]]:
    same_across_reports = {"cmds": {}}
    for id_1, id_2 in itertools.combinations(objects_per_run.keys(), 2):
        if id_1 != id_2:
            processes_1 = objects_per_run[id_1]["process"]
            processes_2 = objects_per_run[id_2]["process"]
            for p1 in processes_1:
                for p2 in processes_2:
                    if p1.cmd == p2.cmd:
                        cmds = same_across_reports["cmds"]
                        ocurred_reports = cmds.get(p1.cmd, [])
                        if id_1 not in ocurred_reports:
                            ocurred_reports.append(id_1)
                        if id_2 not in ocurred_reports:
                            ocurred_reports.append(id_2)
                        cmds[p1.cmd] = ocurred_reports
                        same_across_reports["cmds"] = cmds
    return same_across_reports


def filter_too_rare_objects(
    same_across_reports: Dict[str, Dict[str, List[int]]], number_of_reports: int
) -> List[str]:
    same_cmd_lines = []
    for obj in list(same_across_reports["cmds"].keys()):
        if len(same_across_reports["cmds"][obj]) < (number_of_reports * 1 / 3):
            del same_across_reports["cmds"][obj]
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


def return_observation_expressions(
    regex_cmd_lines: List[str],
) -> List[str]:
    observation_expressions = []
    for regex in regex_cmd_lines:
        observation_expressions.append(f"[process:command_line MATCHES '{regex}']")
    return observation_expressions
