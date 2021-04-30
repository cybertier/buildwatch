import itertools
import logging
import re
import os
from typing import List, Dict
from .gen_regex import regex_from_tree, resolve_quantifier
from .helper_functions import nested_set_for_files, conf

log = logging.getLogger(__name__)


def process_file_type(files: List[str], objects_per_run: Dict[int, Dict[str, List]], file_op: str):
    # directly use file paths, if they are the same across multiple reports, depending on conf.fix_value_threshold
    finished_regexes = []
    same_across_reports = get_same_files_across_reports(objects_per_run, file_op)
    for obj in list(same_across_reports.keys()):
        if len(same_across_reports[obj]) < len(objects_per_run.keys()) * conf.fix_value_threshold:
            del same_across_reports[obj]
        else:
            finished_regexes.append("/".join([re.escape(x) for x in obj.split("/")]))

    # build regexes on file paths
    tree = build_tree(files, same_across_reports)
    regex_from_tree(tree, finished_regexes)
    finished_regexes = list(set(finished_regexes))

    # get secondary features
    finished_regexes = sanitize_regexes(finished_regexes, files)
    return finished_regexes


def get_same_files_across_reports(
    objects_per_run: Dict[int, Dict[str, List]], file_op: str
) -> Dict[str, List[int]]:
    same_across_reports = {}
    for runtime_1, runtime_2 in itertools.combinations(objects_per_run.keys(), 2):
        if runtime_1 != runtime_2:
            files_1 = objects_per_run[runtime_1][file_op]
            files_2 = objects_per_run[runtime_2][file_op]
            for f1 in files_1:
                for f2 in files_2:
                    if f1 == f2:
                        ocurred_reports = same_across_reports.get(f1, [])
                        if runtime_1 not in ocurred_reports:
                            ocurred_reports.append(runtime_1)
                        if runtime_2 not in ocurred_reports:
                            ocurred_reports.append(runtime_2)
                        same_across_reports[f1] = ocurred_reports
    return same_across_reports


# builds tree-like structure for observed files over all reports
def build_tree(files: List[str], same_across_reports: Dict[str, List[int]]) -> Dict[str, Dict]:
    tree = {}
    for file in files:
        if os.path.dirname(file) == "/":
            file = os.path.basename(file)
        if file in same_across_reports:
            continue
        nested_set_for_files(tree, file.split("/"))
    return tree


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
