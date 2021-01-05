import re
import shlex
import logging
import itertools
from .gen_regex import regex_from_tree
from .helper_functions import nested_set, match_patterns_on_reports

log = logging.getLogger(__name__)


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

    def match_ratio(self, accumulated_reports=None):
        if accumulated_reports:
            self.update_matched_reports(accumulated_reports)
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
            if re.match(self.regex, observable["0"].command_line):
                groups = re.match(self.regex, observable["0"].command_line).groupdict()
                for re_id in groups.keys():
                    entry_group_id = regex_groups.get(re_id, {})
                    entry_observable_id = entry_group_id.get(report_id, [])
                    entry_observable_id.append(groups[re_id])
                    entry_observable_id = list(set(entry_observable_id))
                    entry_group_id[report_id] = entry_observable_id
                    regex_groups[re_id] = entry_group_id
        if hasattr(observable["0"], "name") and self.name:
            if re.match(self.name, observable["0"].name):
                groups = re.match(self.name, observable["0"].name).groupdict()
                for re_id in groups.keys():
                    entry_group_id = regex_groups.get(re_id, {})
                    entry_observable_id = entry_group_id.get(report_id, [])
                    entry_observable_id.append(groups[re_id])
                    entry_observable_id = list(set(entry_observable_id))
                    entry_group_id[report_id] = entry_observable_id
                    regex_groups[re_id] = entry_group_id

    def update_matched_reports(self, accumulated_reports):
        match_patterns_on_reports(accumulated_reports, [self])


def process_process_type(accumulated_objects, accumulated_reports):
    process_patterns = []
    names = []
    names_only = []
    cmd_lines = []

    same_cmd_lines = []
    same_names = []
    same_across_reports = get_same_processes_across_reports(accumulated_objects)
    for obj in list(same_across_reports["cmds"].keys()):
        if len(same_across_reports["cmds"][obj]) < (len(accumulated_reports) * 1 / 3):
            del same_across_reports["cmds"][obj]
        else:
            same_cmd_lines.append(obj)
    for obj in list(same_across_reports["names"].keys()):
        if len(same_across_reports["names"][obj]) < (len(accumulated_reports) * 1 / 3):
            del same_across_reports["names"][obj]
        else:
            same_names.append(obj)

    for process in accumulated_objects["process"]:
        if "command_line" in process["0"] and process["0"].command_line not in same_cmd_lines:
            cmd_lines.append(process["0"].command_line)
        if "name" in process["0"] and process["0"].name not in same_names:
            names.append(process["0"].name)
        if "command_line" not in process["0"] and "name" in process["0"]:
            names_only.append(process["0"].name)

    tree = {}
    regex_cmd_lines = []
    for cmd_line in cmd_lines:
        nested_set(tree, cmd_line.split("/"), {})
    regex_from_tree(tree, regex_cmd_lines)
    for cmd in same_cmd_lines:
        regex_cmd_lines.append(re.escape(cmd))

    tree = {}
    regex_names = []
    for name in names:
        nested_set(tree, name.split("\\"), {})
    regex_from_tree(tree, regex_names)
    for name in same_names:
        regex_names.append(re.escape(name))

    # handle cmd_line
    for regex in regex_cmd_lines:
        obj = ProcessPattern(len(accumulated_reports))
        obj.regex = regex

        exe_names = []
        for cmd_line in cmd_lines + same_cmd_lines:
            if re.fullmatch(regex, cmd_line):
                try:
                    exe_name = cmd_line.split("/")[-1]
                except ValueError:  # noqa
                    exe_name = None
                if exe_name and exe_name not in exe_names:
                    exe_names.append(exe_name)

        if len(exe_names) == 1 and exe_names[0] in same_names:
            obj.name = re.escape(exe_names[0])
            process_patterns.append(obj)
            break

        tree = {}
        re_exe_names = []
        for name in exe_names:
            nested_set(tree, [name], {})
        regex_from_tree(tree, re_exe_names)
        if len(re_exe_names) == 1:
            obj.name = re_exe_names[0]

        process_patterns.append(obj)

    for regex in regex_names:
        matched = False
        for name in names_only:
            if re.fullmatch(regex, name):
                matched = True
        if matched:
            obj = ProcessPattern(len(accumulated_reports))
            obj.name = regex
            process_patterns.append(obj)
            continue

    # match resulting patterns against input data from reports; also fill in
    # which of these reports are matched
    match_patterns_on_reports(accumulated_reports, process_patterns)
    return process_patterns


def get_same_processes_across_reports(accumulated_objects):
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
                cmd_1 = p1["0"].command_line
            if hasattr(p1["0"], "name"):
                name_1 = p1["0"].name
            for p2 in processes_2:
                cmd_2 = None
                name_2 = None
                if hasattr(p2["0"], "command_line"):
                    cmd_2 = p2["0"].command_line
                if hasattr(p2["0"], "name"):
                    name_2 = p2["0"].name
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
    return same_across_reports
