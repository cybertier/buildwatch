import itertools
import logging
import re
from typing import List, Dict, Tuple, Set

from .gen_regex import regex_from_tree, resolve_quantifier
from .helper_functions import nested_set_for_files, conf, FileData

log = logging.getLogger(__name__)


def process_file_type(
    files: List[FileData], objects_per_run: Dict[int, Dict[str, List]]
) -> List[str]:
    # directly use file paths, if they are the same across multiple reports
    same_across_reports = get_same_files_across_reports(objects_per_run)
    same_across_reports, finished_regexes = filter_too_rare_objects(
        same_across_reports, len(objects_per_run.keys())
    )

    # build regexes on file paths
    tree = build_tree(files, same_across_reports)
    regex_from_tree(tree, finished_regexes)
    finished_regexes = list(set(finished_regexes))

    # get secondary features
    str_lengths = get_file_features(finished_regexes, files)
    return return_observation_expressions(finished_regexes, str_lengths)


def filter_too_rare_objects(
    same_across_reports: Dict[str, List[int]], number_of_reports: int
) -> Tuple[Dict[str, List[int]], List[str]]:
    finished_regexes = []
    for file in same_across_reports.keys():
        if len(same_across_reports[file]) < number_of_reports * conf.fix_value_threshold:
            del same_across_reports[file]
        else:
            finished_regexes.append("/".join([re.escape(x) for x in file.split("/")]))
    return same_across_reports, finished_regexes


def get_same_files_across_reports(
    objects_per_run: Dict[int, Dict[str, List]]
) -> Dict[str, List[int]]:
    same_across_reports = {}
    for id_1, id_2 in itertools.combinations(objects_per_run.keys(), 2):
        if id_1 != id_2:
            for file1, file2 in itertools.product(
                objects_per_run[id_1]["file"], objects_per_run[id_2]["file"]
            ):
                if are_equal_files(file1, file2):
                    filepath = f"{file1.dir}/{file1.name}"
                    same_across_reports[filepath] = add_report_ids_where_file_occured(
                        same_across_reports.get(filepath, []), id_1, id_2
                    )
    return same_across_reports


def add_report_ids_where_file_occured(ocurred_reports: List, id_1: int, id_2: int) -> List[int]:
    if id_1 not in ocurred_reports:
        ocurred_reports.append(id_1)
    if id_2 not in ocurred_reports:
        ocurred_reports.append(id_2)
    return ocurred_reports


def are_equal_files(file1, file2):
    return file1.dir == file2.dir and file1.name == file2.name


# builds tree-like structure for observed files over all reports
def build_tree(
    files: List[FileData], same_across_reports: Dict[str, List[int]]
) -> Dict[str, Dict]:
    tree = {}
    for file in files:
        if file.dir == "/":
            file.dir = ""
        if f"{file.dir}/{file.name}" in same_across_reports:
            continue
        nested_set_for_files(tree, f"{file.dir}/{file.name}".split("/"))
    return tree


# get hashes and file size from files matching the regexes;
# if for one regex multiple different values are found, do *NOT* include them
def get_file_features(finished_regexes: List[str], files: List[FileData]) -> Dict[str, Set[int]]:
    str_lengths = {}
    for regex, file in itertools.product(finished_regexes, files):
        str_lengths = get_features(regex, file, str_lengths)
    return str_lengths


def get_features(
    _regex: str, _file: FileData, str_lengths: Dict[str, Set[int]]
) -> Dict[str, Set[int]]:
    match = re.match(_regex, f"{_file.dir}/{_file.name}")
    if match:
        return add_lengths_of_group_id(str_lengths, match)
    return str_lengths


def add_lengths_of_group_id(
    str_lengths: Dict[str, Set[int]], match: re.Match
) -> Dict[str, Set[int]]:
    for group_id, string in match.groupdict().items():
        lengths = str_lengths.get(group_id, ())
        lengths.add(len(string))
        str_lengths[group_id] = lengths
    return str_lengths


def return_observation_expressions(finished_regexes: List[str], str_lengths) -> List[str]:
    observation_expressions = []
    for regex in finished_regexes:
        regex = resolve_quantifier(regex, str_lengths)
        path = r"/".join(regex.split(r"/")[0:-1])
        file_name = regex.split(r"/")[-1]
        observation_expressions.append(
            f"[file:parent_directory_str MATCHES '{path}' AND file:name MATCHES '{file_name}']"
        )
    return observation_expressions
