import itertools
import json
import logging
import re
from typing import List, Dict, Any

from .gen_regex import regex_from_tree, resolve_quantifier
from .helper_functions import (
    nested_set_for_files,
    conf,
)
from stix2 import File

log = logging.getLogger(__name__)

class FilePattern:
    def __hash__(self):
        return hash(repr(self))

    def __init__(self, amount_of_reports):
        self.regex = None
        self.size = None
        self.hashes = {}
        self.matched_reports = []
        self.amount_of_reports = amount_of_reports

    def __eq__(self, other):
        if not isinstance(other, FilePattern):
            return False

        same = [
            self.regex == other.regex,
            self.size == other.size,
            self.hashes == other.hashes,
        ]
        return False not in same

    def match_ratio(self):
        return len(self.matched_reports) / self.amount_of_reports

    def observation_expression(self):
        obs_expr = "["

        if self.hashes:
            if self.regex:
                obs_expr += "(("
            hashes = []
            for hash_type, value in self.hashes.items():
                if len(value) == 1:
                    hashes.append(f"file:hashes.'{hash_type}' = '{value[0]}'")
            obs_expr += " AND ".join(hashes)
            if self.regex:
                obs_expr += ") OR ("

        if self.regex:
            path = r"/".join(self.regex.split(r"/")[0:-1])
            file_name = self.regex.split(r"/")[-1]
            obs_expr += f"file:parent_directory_str MATCHES '{path}'"
            obs_expr += f" AND file:name MATCHES '{file_name}'"
            if self.hashes:
                obs_expr += "))"

        if self.size:
            if len(self.size) == 1:
                obs_expr += f" AND file:size = {str(self.size[0])}"
            else:
                log.warning(
                    "TODO [this can not occur atm]: got multiple file "
                    f"sizes for pattern {self.regex}"
                )

        return obs_expr + "]"

    def get_re_groups(self, observable, regex_groups, report_id):
        try:
            full_path = f"{observable['0']['parent_directory_str']}/{observable['0']['name']}"
            if re.match(self.regex, full_path):
                groups = re.match(self.regex, full_path).groupdict()
                for re_id in groups.keys():
                    entry_group_id = regex_groups.get(re_id, {})
                    entry_observable_id = entry_group_id.get(report_id, [])
                    entry_observable_id.append(groups[re_id])
                    entry_observable_id = list(set(entry_observable_id))
                    entry_group_id[report_id] = entry_observable_id
                    regex_groups[re_id] = entry_group_id
        except Exception:
            pass


# builds tree-like structure for observed files over all reports
def build_tree(files: List[Dict[str, File]], same_across_reports) -> Dict[str, Dict]:
    tree = {}
    for file in files:
        path = file["0"]['parent_directory_str']
        name = file["0"]['name']

        if path and name:
            if path == "/":
                path = ""
            if f"{path}/{name}" in same_across_reports:
                continue
            nested_set_for_files(tree, f"{path}/{name}".split("/"))
        else:
            log.warning(
                "[FILE] Unsupported - path or name not provided." f" Object: {file}"
            )
    return tree


# in case a file pattern can not be pinned down to one specific hash sum,
# remove them all [do not bloat pattern with a multitude of hashes!]
def clean_hashes(file_patterns):
    hashes = {}
    for pattern in file_patterns:
        if pattern.hashes:
            hsums = hashes.get(json.dumps(pattern.hashes), [])
            hsums.append(pattern)
            hashes[json.dumps(pattern.hashes)] = hsums
    same_hashes = [p for h, p in hashes.items() if len(p) > 1]

    for patterns in same_hashes:
        new_pattern = patterns[0]
        for pattern in patterns:
            file_patterns.remove(pattern)
            if (
                new_pattern.regex
                and pattern.regex
                and new_pattern.regex != pattern.regex
            ):
                new_pattern.regex = None
            if new_pattern.size and pattern.size and new_pattern.size != pattern.size:
                new_pattern.size = None
        file_patterns.append(new_pattern)
    return file_patterns


def process_file_type(
    accumulated_objects: Dict[str, List[Dict[str, Any]]], number_of_reports: int
):
    files = accumulated_objects["file"]
    finished_regexes = []

    # directly use file paths, if they are the same across multiple reports
    same_across_reports = get_same_files_across_reports(accumulated_objects)
    for obj in list(same_across_reports.keys()):
        if len(same_across_reports[obj]) < number_of_reports * conf.fix_value_threshold:
            del same_across_reports[obj]
        else:
            finished_regexes.append("/".join([re.escape(x) for x in obj.split("/")]))

    # build regexes on file paths
    tree = build_tree(files, same_across_reports)
    regex_from_tree(tree, finished_regexes)
    finished_regexes = list(set(finished_regexes))

    # get secondary features
    file_sizes, file_hashes, str_lengths = get_file_features(finished_regexes, files)
    for i, regex in enumerate(finished_regexes):
        finished_regexes[i] = resolve_quantifier(regex, str_lengths)

    file_patterns = []
    for regex in finished_regexes:
        obj = FilePattern(number_of_reports)
        obj.regex = regex
        if regex in file_sizes:
            obj.size = file_sizes[regex]
        if regex in file_hashes:
            obj.hashes = file_hashes[regex]
        file_patterns.append(obj)

    file_patterns = clean_hashes(file_patterns)

    return file_patterns


def get_same_files_across_reports(accumulated_objects: Dict[str, List[Dict[str, Any]]]):
    same_across_reports = {}
    for id_1, id_2 in itertools.combinations(accumulated_objects.keys(), 2):
        try:
            files_1 = accumulated_objects[id_1]["file"]
            files_2 = accumulated_objects[id_2]["file"]

            for f1 in files_1:
                path_1 = f1["0"]['parent_directory_str']
                name_1 = f1["0"]['name']
                for f2 in files_2:
                    path_2 = f2["0"]['parent_directory_str']
                    name_2 = f2["0"]['name']

                    if path_1 == path_2 and name_1 == name_2:
                        ocurred_reports = same_across_reports.get(f"{path_1}/{name_1}", [])
                        if id_1 not in ocurred_reports:
                            ocurred_reports.append(id_1)
                        if id_2 not in ocurred_reports:
                            ocurred_reports.append(id_2)
                        same_across_reports[f"{path_1}/{name_1}"] = ocurred_reports
        except Exception as exc:
            continue
    return same_across_reports


# get hashes and file size from files matching the regexes;
# if for one regex multiple different values are found, do *NOT* include them
def get_file_features(finished_regexes, files):
    def get_features(regex, file, file_sizes, file_hashes, str_lengths):
        try:
            full_path = f"{file['0']['parent_directory_str']}/{file['0']['name']}"
            match = re.match(regex, full_path)
            if match:
                for group_id, string in match.groupdict().items():
                    lengths = str_lengths.get(group_id, [])
                    if len(string) not in lengths:
                        lengths.append(len(string))
                    str_lengths[group_id] = lengths
        except Exception:
            pass

    file_sizes = {}
    file_hashes = {}
    str_lengths = {}
    for regex in finished_regexes:
        for file in files:
            get_features(regex, file, file_sizes, file_hashes, str_lengths)
        if regex in file_sizes:
            for _item in list(file_sizes[regex]):
                if regex in file_sizes and (
                    len(list(set(file_sizes[regex]))) != 1
                    or "unknown" in list(file_sizes[regex])
                ):
                    del file_sizes[regex]

        if regex in file_hashes:
            if "unknown" in file_hashes[regex]:
                del file_hashes[regex]
            else:
                for hash_type in list(file_hashes[regex].keys()):
                    if regex in file_hashes and len(file_hashes[regex][hash_type]) != 1:
                        del file_hashes[regex]
                        break
    return file_sizes, file_hashes, str_lengths
