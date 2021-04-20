import itertools
import logging
import re
from typing import Dict, List

from .gen_regex import regex_from_tree
from .helper_functions import nested_set_for_processes, ProcessData

log = logging.getLogger(__name__)


<<<<<<< HEAD
class ProcessPattern:
    def __hash__(self):
        return hash(repr(self))

    def __init__(self, amount_of_reports):
        self.name = None
        self.regex = None
        self.matched_reports = []
        self.amount_of_reports = amount_of_reports

    def __eq__(self, other):
        if not isinstance(other, ProcessPattern):
            return False

        same = [
            self.name == other.name,
            self.regex == other.regex,
        ]
        return False not in same

    def match_ratio(self):
        return len(self.matched_reports) / self.amount_of_reports

    def observation_expression(self):
        properties = []
        if self.regex:
            properties.append(f"process:command_line MATCHES '{self.regex}'")
        # if self.name: TODO: Add name field to process object
        #    properties.append(f"process:name MATCHES '{self.name}'")
        obs_expr = "[" + " AND ".join(properties) + "]"
        return obs_expr

    def get_re_groups(self, observable, regex_groups, report_id):
        if hasattr(observable["0"], "command_line") and self.regex:
            if re.match(self.regex, observable["0"]['command_line']):
                groups = re.match(self.regex, observable["0"]['command_line']).groupdict()
                for re_id in groups.keys():
                    entry_group_id = regex_groups.get(re_id, {})
                    entry_observable_id = entry_group_id.get(report_id, [])
                    entry_observable_id.append(groups[re_id])
                    entry_observable_id = list(set(entry_observable_id))
                    entry_group_id[report_id] = entry_observable_id
                    regex_groups[re_id] = entry_group_id
        if hasattr(observable["0"], "name") and self.name:
            if re.match(self.name, observable["0"]['name']):
                groups = re.match(self.name, observable["0"]['name']).groupdict()
                for re_id in groups.keys():
                    entry_group_id = regex_groups.get(re_id, {})
                    entry_observable_id = entry_group_id.get(report_id, [])
                    entry_observable_id.append(groups[re_id])
                    entry_observable_id = list(set(entry_observable_id))
                    entry_group_id[report_id] = entry_observable_id
                    regex_groups[re_id] = entry_group_id


=======
>>>>>>> main
def process_process_type(
    processes: List[ProcessData], objects_per_run: Dict[int, Dict[str, List]]
) -> List[str]:
    same_across_reports = get_same_processes_across_reports(objects_per_run)
    same_cmd_lines = filter_too_rare_objects(same_across_reports, len(objects_per_run.keys()))

<<<<<<< HEAD
    same_across_reports = get_same_processes_across_reports(accumulated_objects)
    same_cmd_lines, same_names = split_objects_by_name_or_cmd_line(
        same_across_reports, number_of_reports
    )

    for process in accumulated_objects["process"]:
        if (
            "command_line" in process["0"]
            and process["0"]['command_line'] not in same_cmd_lines
        ):
            cmd_lines.append(process["0"]['command_line'])
        if "name" in process["0"] and process["0"]['name'] not in same_names:
            names.append(process["0"]['name'])
        if "command_line" not in process["0"] and "name" in process["0"]:
            names_only.append(process["0"]['name'])
=======
    cmd_lines = []
    for process in processes:
        if process.cmd not in same_cmd_lines:
            cmd_lines.append(process.cmd)
>>>>>>> main

    regex_cmd_lines = get_cmd_line_regexes(cmd_lines, same_cmd_lines)
    return return_observation_expressions(regex_cmd_lines)


def get_same_processes_across_reports(
<<<<<<< HEAD
    accumulated_objects: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Dict[str, List]]:
    same_across_reports = {"cmds": {}, "names": {}}
    for id_1, id_2 in itertools.combinations(accumulated_objects.keys(), 2):
        if (
            id_1 == id_2
            or not isinstance(id_1, int)
            or not isinstance(id_2, int)
            or "process" not in accumulated_objects[id_1]
            or "process" not in accumulated_objects[id_2]
        ):
            continue
        processes_1 = accumulated_objects[id_1]["process"]
        processes_2 = accumulated_objects[id_2]["process"]
        for p1 in processes_1:
            cmd_1 = None
            name_1 = None
            if hasattr(p1["0"], "command_line"):
                cmd_1 = p1["0"]['command_line']
            if hasattr(p1["0"], "name"):
                name_1 = p1["0"]['name']
            for p2 in processes_2:
                cmd_2 = None
                name_2 = None
                if hasattr(p2["0"], "command_line"):
                    cmd_2 = p2["0"]['command_line']
                if hasattr(p2["0"], "name"):
                    name_2 = p2["0"]['name']
                if cmd_1 and cmd_1 == cmd_2:
                    cmds = same_across_reports["cmds"]
                    ocurred_reports = cmds.get(cmd_1, [])
                    if id_1 not in ocurred_reports:
                        ocurred_reports.append(id_1)
                    if id_2 not in ocurred_reports:
                        ocurred_reports.append(id_2)
                    cmds[cmd_1] = ocurred_reports
                    same_across_reports["cmds"] = cmds
                if name_1 and name_1 == name_2:
                    names = same_across_reports["names"]
                    ocurred_reports = names.get(name_1, [])
                    if id_1 not in ocurred_reports:
                        ocurred_reports.append(id_1)
                    if id_2 not in ocurred_reports:
                        ocurred_reports.append(id_2)
                    names[name_1] = ocurred_reports
                    same_across_reports["names"] = names
=======
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
>>>>>>> main
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
