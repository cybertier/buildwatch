import logging
import itertools
import re
from typing import List, Dict
from .gen_regex import regex_from_tree, resolve_quantifier
from .helper_functions import nested_set_for_files

log = logging.getLogger(__name__)


def process_domain_type(
    domains: List[str], objects_per_run: Dict[int, Dict[str, List]]
) -> List[str]:
    same_across_reports = get_same_domains_across_reports(objects_per_run)
    same_domains = filter_too_rare_objects(same_across_reports, len(objects_per_run.keys()))

    tree = {}
    regex_domains = []
    for domain in domains:
        if domain not in same_domains:
            nested_set_for_files(tree, domain.split("."))
    regex_from_tree(tree, regex_domains, seperator=".")

    for cmd in same_domains:
        regex_domains.append(re.escape(cmd))

    return regex_domains


def get_same_domains_across_reports(
    objects_per_run: Dict[int, Dict[str, List]]
) -> Dict[str, Dict[str, List[int]]]:
    same_across_reports = {}
    for id_1, id_2 in itertools.combinations(objects_per_run.keys(), 2):
        if id_1 != id_2:
            domain_1 = objects_per_run[id_1]["domains_connected"]
            domain_2 = objects_per_run[id_2]["domains_connected"]
            for d1 in domain_1:
                for d2 in domain_2:
                    if d1 == d2:
                        ocurred_reports = same_across_reports.get(d1, [])
                        if id_1 not in ocurred_reports:
                            ocurred_reports.append(id_1)
                        if id_2 not in ocurred_reports:
                            ocurred_reports.append(id_2)
                        same_across_reports[d1] = ocurred_reports
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
