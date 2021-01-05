import copy
import re
import itertools
import logging
import yaml

from .helper_functions import conf
from .file_type import FilePattern

log = logging.getLogger(__name__)


def update_objects(
    accumulated_reports, patterns, same_value_across_reports, same_value_within_report
):
    # replace regex with string, if string is the same over all reports
    for re_id, values in same_value_across_reports.items():
        for typ in [
            "file_patterns",
            "mutex_patterns",
            "process_patterns",
            "windows_registry_key_patterns",
        ]:
            create_new_objects_with_regex(
                accumulated_reports, patterns.get(typ, []), values, re_id
            )

    # set ids, to reflect which RegEx corespond to the same value instances
    for s in same_value_within_report:
        for group_id in s:
            for obj in patterns.get("file_patterns", []) + patterns.get(
                "process_patterns", []
            ):  # noqa, bc indent and line length fight each other
                if obj.regex and re.search(r"\(\?P<" + group_id + ">", obj.regex):
                    obj.regex = obj.regex.replace(
                        "(?P<" + group_id + ">", "(?P<" + list(s)[0] + ">"
                    )
                    resolve_duplicate_groups(obj)
            for obj in patterns.get("process_patterns", []):
                if obj.name:
                    if re.search(r"\(\?P<" + group_id + ">", obj.name):
                        obj.name = obj.name.replace(
                            "(?P<" + group_id + ">", "(?P<" + list(s)[0] + ">"
                        )
                        resolve_duplicate_groups(obj)

    process_substrings_within_intra_obs(accumulated_reports, patterns)


def process_substrings_within_intra_obs(accumulated_reports, patterns):
    # get same substrings across groups... example:
    # group id_1 matches on 'aevoc',
    #       id_2 matches on 'aevock',
    #       id_3 matches on 'aevocka'
    # [behaviour observed in sample 25d936e87d745ce19748a11fb1b6cff1a6605768]
    regex_groups, group_to_regex = get_regex_groups(accumulated_reports, patterns)
    overlaps = {}
    for group_1, group_2 in itertools.combinations(regex_groups.keys(), 2):
        g1_in_g2 = True
        g2_in_g1 = True
        for report_id in list(
            set(list(regex_groups[group_1].keys()) + list(regex_groups[group_2].keys()))
        ):  # noqa
            str1_in_str2 = []
            str2_in_str1 = []
            if (
                report_id not in regex_groups[group_1] or report_id not in regex_groups[group_2]
            ):  # noqa
                continue
            for str_1 in regex_groups[group_1][report_id]:
                for str_2 in regex_groups[group_2][report_id]:
                    if str_1 != str_2:
                        str1_in_str2.append(str_1.lower() in str_2.lower())
                        str2_in_str1.append(str_2.lower() in str_1.lower())
            if True not in str1_in_str2:
                g1_in_g2 = False
            if True not in str2_in_str1:
                g2_in_g1 = False
        if g1_in_g2 and not g2_in_g1:
            entry = overlaps.get(group_1, [])
            entry.append(group_2)
            overlaps[group_1] = entry
        if g2_in_g1 and not g1_in_g2:
            entry = overlaps.get(group_2, [])
            entry.append(group_1)
            overlaps[group_2] = entry

    if len(overlaps.keys()) > 1:
        for group_1, group_2 in itertools.combinations(overlaps.keys(), 2):
            if group_1 in overlaps and group_2 in overlaps and group_1 in overlaps[group_2]:
                overlaps[group_2] = list(set(overlaps[group_1] + overlaps[group_2]))
                del overlaps[group_1]
            if group_1 in overlaps and group_2 in overlaps and group_2 in overlaps[group_1]:
                overlaps[group_1] = list(set(overlaps[group_1] + overlaps[group_2]))
                del overlaps[group_2]
    log.debug(f"Overlaps: {overlaps}")
    process_overlaps(patterns, overlaps, regex_groups, group_to_regex)


def process_overlaps(patterns, overlaps, regex_groups, group_to_regex):
    # process overlaps; the idea is to insert the overlapping regex
    # into the current processed regex
    for group, overlap in overlaps.items():
        re_smallest_part = group_to_regex.get(group)
        quantifier_1 = re.search(r"(?P<quant>\+|\{.+\})", re_smallest_part).group(1)
        for gid in overlap:
            re_other_part = group_to_regex.get(gid)
            container = []
            for report, values in regex_groups[gid].items():
                for value in values:
                    if report in regex_groups[group]:
                        for string in regex_groups[group][report]:
                            if string == value:
                                continue
                            pos = value.lower().find(string.lower())
                            if pos == 0:
                                # same string @start
                                container.append((0, len(value) - len(string)))
                            elif pos != -1 and pos == len(value) - len(string):
                                # same string @end
                                container.append((-1, len(value) - len(string)))
                            elif pos != -1:
                                # same string between
                                container.append((pos, len(value) - len(string)))
            container = list(set(container))
            if len(container) > 1:
                positions = [p for (p, _) in container]
                positions = list(set(positions))
                min_len = min([l for (_, l) in container])
                max_len = max([l for (_, l) in container])
                if len(positions) == 1:
                    if min_len == max_len:
                        element = (positions[0], f"{min_len}")
                    else:
                        element = (positions[0], f"{min_len},{max_len}")
                else:
                    log.debug("[NotImplemented]: complex case of " "inter-observable RegEx")
                    continue
            elif len(container) == 1:
                element = container[0]
            else:
                continue
            create_expression_from_overlaps(
                patterns,
                gid,
                group,
                element,
                re_smallest_part,
                re_other_part,
                quantifier_1,
            )


# pylint: disable=undefined-loop-variable
def create_expression_from_overlaps(
    patterns, gid, group, element, re_smallest_part, re_other_part, quantifier_1
):
    def create_new_expressions():
        new_expressions = []
        if element[0] == 0:
            if re_smallest_part[-1] == "+":
                new_expression = f"(?P<{group}>" f"{character_class_other_part}+)"
            else:
                new_expression = f"(?P<{group}>" f"{character_class_other_part}" f"{quantifier_1})"
            if re_other_part[-1] == "+":
                new_expression += re_other_part
            else:
                new_expression += "{".join(re_other_part.split("{")[0:-1])
            if new_expression[-1] != "+":
                new_expression += f"{{{element[1]}}}"
            new_expressions.append(new_expression)
        elif element[0] == -1:
            new_expression = (
                character_class_other_part + f"{{{element[1]}}}" f"(?P<{group}>{re_smallest_part})"
            )
            new_expressions.append(new_expression)
        else:
            quant = element[1]
            if "," in str(quant):
                quant = int(quant.split(",")[0])
            new_expression = (
                character_class_other_part + f"{{{element[0]}}}"
                f"(?P<{group}>{re_smallest_part})"
                + character_class_other_part
                + f"{{{quant - element[0]}}}"
            )
            new_expressions.append(new_expression)
        return new_expressions

    if re_other_part[-1] == "+":
        character_class_other_part = re_other_part[0:-1]
    else:
        character_class_other_part = "{".join(re_other_part.split("{")[0:-1])
    new_expressions = create_new_expressions()

    for new_expression in new_expressions:
        for obj in (
            patterns.get("file_patterns", [])
            + patterns.get("mutex_patterns", [])
            + patterns.get("process_patterns", [])
            + patterns.get(  # noqa, bc indent and line length fight each other
                "windows_registry_key_patterns", []
            )
        ):
            for attr in ["regex", "name"]:
                if (
                    hasattr(obj, attr)
                    and getattr(obj, attr)
                    and re.search(r"\(\?P<" + gid + ">", getattr(obj, attr))
                ):
                    setattr(
                        obj,
                        attr,
                        re.sub(
                            r"\(\?P<" + gid + r">([^\)]|(?<=\\)\))+\)",
                            f"{new_expression}",
                            getattr(obj, attr),
                        ),
                    )
                    resolve_duplicate_groups(obj)
        for obj in patterns.get("windows_registry_key_patterns", []):
            if obj.value:
                val_0 = obj.value[0]
                val_2 = obj.value[2]
                if re.search(r"\(\?P<" + gid + ">", obj.value[0]):
                    val_0 = re.sub(
                        r"\(\?P<id_" + group + r">([^\)]|(?<=\\)\))+\)",
                        f"{new_expression}",
                        obj.value[0],
                    )
                if re.search(r"\(\?P<" + gid + ">", obj.value[2]):
                    val_2 = re.sub(
                        r"\(\?P<id_" + group + r">([^\)]|(?<=\\)\))+\)",
                        f"{new_expression}",
                        obj.value[2],
                    )
                obj.value = (val_0, obj.value[1], val_2)
                resolve_duplicate_groups(obj)


# gather values from observables, which occur for regex-groups
def get_regex_groups(accumulated_reports, patterns):
    regex_groups = {}
    group_to_regex = {}
    group_matcher_regex = re.compile(r"\(\?P<(?P<id>id_\d+)>(?P<regex>([^\)]|(?<=\\)\))+)\)")
    # following code checks regex-attribute of patterns
    for typ in [
        "file_patterns",
        "process_patterns",
    ]:
        for obj in patterns.get(typ, []):
            if obj.match_ratio() < conf.match_ratio_threshold:
                continue
            for attr in ["regex", "name"]:
                if (
                    hasattr(obj, attr)
                    and getattr(obj, attr)
                    and re.search(r"\(\?P<id_\d+>", getattr(obj, attr))
                ):
                    for report_id, report in enumerate(accumulated_reports):
                        for observed_data in report:
                            observable = observed_data.objects
                            if observable["0"].type != "-".join(typ.split("_")[0:-1]):
                                continue
                            obj.get_re_groups(observable, regex_groups, report_id)
                            groups_matcher = [
                                m.groupdict()
                                for m in group_matcher_regex.finditer(getattr(obj, attr))
                            ]
                            for item in groups_matcher:
                                group_to_regex[item["id"]] = item["regex"]
            if hasattr(obj, "value") and getattr(obj, "value"):
                for val in [getattr(obj, "value")[0], getattr(obj, "value")[2]]:
                    if re.search(r"\(\?P<id_\d+>", val):
                        for report_id, report in enumerate(accumulated_reports):
                            for observed_data in report:
                                observable = observed_data.objects
                                if observable["0"].type != "-".join(typ.split("_")[0:-1]):
                                    continue
                                obj.get_re_groups(observable, regex_groups, report_id)
                                groups_matcher = [
                                    m.groupdict() for m in group_matcher_regex.finditer(val)
                                ]
                                for item in groups_matcher:
                                    group_to_regex[item["id"]] = item["regex"]
    return regex_groups, group_to_regex


# if a named group occurs multiple times in a RE, it needs to be replaced with
# a subpattern group [else the RE is invalid bc duplicate named group!]
def resolve_duplicate_groups(obj):
    def has_multiples_of_same_id(obj_str):
        r = re.compile(r"\(\?P<id_(?P<group>\d+)>(\\\)|[^\)])+\)")
        groups = [m.group("group") for m in r.finditer(obj_str)]
        if len(set(groups)) != len(groups):
            duplicate_groups = list({x for x in groups if groups.count(x) > 1})
            return duplicate_groups
        return []

    # replace old with new in string, after the first occurence of old
    def replace_after_first_occurence(string, regex, new):
        first_occurence = re.search(regex, string)[0]
        left_join = string.split(first_occurence)[:1][0] + first_occurence
        right_join = first_occurence.join(string.split(first_occurence)[1:])
        right_join = re.sub(regex, new, right_join)
        return left_join + right_join

    for attr in ["regex", "name"]:
        if hasattr(obj, attr) and getattr(obj, attr):
            container = []
            if isinstance(obj, FilePattern) and attr == "regex":
                re_str = getattr(obj, attr)
                container.append(r"\\".join(re_str.split(r"\\")[:-1]))
                container.append(re_str.split(r"\\")[-1])
            else:
                container.append(getattr(obj, attr))
            for str_obj in container:
                duplicate_groups = has_multiples_of_same_id(str_obj)
                if duplicate_groups:
                    log.debug(f"duplicate_groups: {duplicate_groups}")
                    for group_id in duplicate_groups:
                        sub_regex = r"\(\?P<id_" + str(group_id) + r">(\\\)|[^\)])+\)"
                        setattr(
                            obj,
                            attr,
                            replace_after_first_occurence(
                                getattr(obj, attr),
                                sub_regex,
                                "(?P=id_" + str(group_id) + ")",
                            ),
                        )
    if hasattr(obj, "value") and obj.value:
        for index in [0, 2]:
            duplicate_groups = has_multiples_of_same_id(obj.value[index])
            if duplicate_groups:
                log.debug(f"duplicate_groups: {duplicate_groups}")
                for group_id in duplicate_groups:
                    sub_regex = r"\(\?P<id_" + str(group_id) + r">(\\\)|[^\)])+\)"
                    val_lst = list(obj.value)
                    val_lst[index] = replace_after_first_occurence(
                        obj.value[index], sub_regex, "(?P=id_" + str(group_id) + ")"
                    )
                    obj.value = tuple(val_lst)


def create_new_objects_with_regex(accumulated_reports, patterns, values, re_id):
    changed = True
    while changed:
        for obj in patterns[:]:
            for attr in ["regex", "name"]:
                if (
                    hasattr(obj, attr)
                    and getattr(obj, attr)
                    and re.search(r"\(\?P<" + re_id + ">", getattr(obj, attr))
                ):
                    for v in values:
                        new_obj = copy.deepcopy(obj)
                        new_obj.matched_reports = []
                        setattr(
                            new_obj,
                            attr,
                            re.sub(
                                r"\(\?P<" + re_id + r">\[[^\)]+\](\+|\{\d+(,\d+)?\})\)",
                                v,
                                new_obj.regex,
                            ),
                        )
                        resolve_duplicate_groups(new_obj)
                        new_obj.update_matched_reports(accumulated_reports)
                        if new_obj not in patterns:
                            patterns.append(new_obj)
                        if obj in patterns:
                            patterns.remove(obj)
                        changed = True
                if changed:
                    break
            if hasattr(obj, "value") and obj.value:
                if re.search(r"\(\?P<" + re_id + ">", obj.value[0]) or re.search(
                    r"\(\?P<" + re_id + ">", obj.value[2]
                ):
                    for v in values:
                        new_obj = copy.deepcopy(obj)
                        new_obj.matched_reports = []
                        val_0 = new_obj.value[0]
                        val_2 = new_obj.value[2]
                        val_0 = re.sub(
                            r"\(\?P<" + re_id + r">\[[^\)]+\](\+|\{\d+(,\d+)?\})\)",
                            v,
                            val_0,
                        )
                        val_2 = re.sub(
                            r"\(\?P<" + re_id + r">\[[^\)]+\](\+|\{\d+(,\d+)?\})\)",
                            v,
                            val_2,
                        )
                        new_obj.value = (val_0, new_obj.value[1], val_2)
                        resolve_duplicate_groups(new_obj)
                        new_obj.update_matched_reports(accumulated_reports)
                        if new_obj not in patterns:
                            patterns.append(new_obj)
                        if obj in patterns:
                            patterns.remove(obj)
                        changed = True
            if changed:
                break
        changed = False


# remove named capture groups from regex, if they are unique within all patterns
def clean_unique_groups(patterns):
    counted_groups = {}
    regex = r"(?P<exp>\(\?P<(?P<id>id_\d+)>\[(\\\)|[^\)])+\](\+|\{\d+(,\d+)?\})\))"  # noqa
    for pattern in patterns:
        for attr in ["regex", "name"]:
            if hasattr(pattern, attr) and getattr(pattern, attr):
                for expression in re.findall(regex, getattr(pattern, attr)):
                    counted = counted_groups.get(expression[1], 0)
                    counted_groups[expression[1]] = counted + 1
        if isinstance(pattern, WinRegistryKeyPattern) and pattern.value:
            for index in [0, 2]:
                for expression in re.findall(regex, pattern.value[index]):
                    counted = counted_groups.get(expression[1], 0)
                    counted_groups[expression[1]] = counted + 1
    log.debug(f"counted groups: {counted_groups}")

    unique_groups = [g for g, count in counted_groups.items() if count == 1]
    for pattern in patterns:
        for attr in ["regex", "name"]:
            if hasattr(pattern, attr) and getattr(pattern, attr):
                for expression in re.findall(regex, getattr(pattern, attr)):
                    if expression[1] in unique_groups:
                        replacer = re.sub(r"\(\?P<id_\d+>", "", expression[0])[0:-1]
                        new_regex = re.sub(
                            re.escape(expression[0]), replacer, getattr(pattern, attr)
                        )
                        setattr(pattern, attr, new_regex)
        if isinstance(pattern, WinRegistryKeyPattern) and pattern.value:
            val_0 = pattern.value[0]
            val_2 = pattern.value[2]
            for expression in re.findall(regex, val_0):
                if expression[1] in unique_groups:
                    replacer = re.sub(r"\(\?P<id_\d+>", "", expression[0])[0:-1]
                    new_regex = re.sub(re.escape(expression[0]), replacer, val_0)
                    val_0 = new_regex
            for expression in re.findall(regex, val_2):
                if expression[1] in unique_groups:
                    replacer = re.sub(r"\(\?P<id_\d+>", "", expression[0])[0:-1]
                    new_regex = re.sub(re.escape(expression[0]), replacer, val_2)
                    val_2 = new_regex
            pattern.value = (val_0, pattern.value[1], val_2)


def contains_inter_obs_pat(stix_pkg):
    regex = r"(?P<exp>\(\?P<(?P<id>id_\d+)>\[[^\)]+\](\+|\{\d+(,\d+)?\})\))"
    return True if re.search(regex, stix_pkg) else False
