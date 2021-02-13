import os
import re
import itertools
import logging
from difflib import SequenceMatcher
from functools import partial
from alignment.sequence import Sequence
from alignment.vocabulary import Vocabulary
from alignment.sequencealigner import SimpleScoring, GlobalSequenceAligner
from alignment.profile import Profile
from .helper_functions import conf, has_file_ending, is_gibberish

log = logging.getLogger(__name__)
directory = os.path.dirname(os.path.abspath(__file__))
group_ctr = 0


# This function takes a dict in the form of a tree/directory structure, e.g.:
# 'C:':
#   Users:
#     Administrator:
#       Desktop:
#         File101: {}
#         Internet.lnk: {}
#       AppData:
#           Local:
#             Temp:
#               7zS1281.tmp:
#                 malicious.exe: {}
#               7zSAFFE.tmp:
#                 malicious.exe: {}
#               7zS9B60.tmp:
#                 malicious.exe: {}
# It traverses each level, checking if regular expressions can be generated from
# strings on the same level.
# The tree will be changed during this function! Example:
# Temp:
#  7zS1281.tmp:
#    malicious.exe: {}
#  7zSAFFE.tmp:
#    malicious.exe: {}
#  7zS9B60.tmp:
#    malicious.exe: {}
# will be merged to something like this:
# Temp:
#  7zS[0-9a-fA-F]{4}\.tmp:
#    malicious.exe: {}
# and generate a pattern like this:
# Temp\\7zS[0-9a-fA-F]{4}\.tmp\\malicious\.exe
# Each pattern will be stored in finished_patterns, which needs to be an array
# and has to be provided to the function.
def regex_from_tree(dictionary, finished_patterns, seperator="/", path=None):
    if path is None:
        path = []

    if not dictionary and path:
        # top level reached, this is the finished pattern
        finished_patterns.append(seperator.join(path))
        return

    if len(dictionary.keys()) == 1:
        # only one element on this level
        key = list(dictionary.keys())[0]
        if is_gibberish(key):
            # generate regex if this is gibberish, then continue to next level
            pattern = regex_from_list([key])
            dictionary[pattern] = dict(dictionary[key])
            del dictionary[key]
            new_path = list(path)
            new_path.append(pattern)
            regex_from_tree(dictionary[pattern], finished_patterns, seperator, new_path)
        else:
            # looks normal, continue to next level
            new_path = list(path)
            new_path.append(re.escape(key))
            regex_from_tree(dictionary[key], finished_patterns, seperator, new_path)
    else:
        # multiple elements on this level. see if regexes can be generated to
        # merge elements. Differentiate between files and directories.
        candidates_dict = {}
        candidates_dict["files"] = []
        candidates_dict["dirs"] = []
        for key in dictionary.keys():
            if dictionary[key]:
                candidates_dict["dirs"].append(key)
            if not dictionary[key]:
                candidates_dict["files"].append(key)

        for type_ in candidates_dict:
            candidates = candidates_dict[type_]
            no_substrings = []

            # do not gen regex on some system directories and env-variables
            for candidate in candidates[:]:
                if re.fullmatch(r"\%\w+\%", candidate) or candidate in conf.system_dirs:
                    candidates.remove(candidate)
                    no_substrings.append(candidate)

            patterns, no_subs = generate_expressions(list(candidates))
            # print(patterns, no_subs)
            no_substrings += no_subs
            no_substrings = list(no_substrings)

            # check if gibberish. if so, generate regex, then proceed to next
            # level.
            new_patterns = []
            for element in no_substrings:
                if is_gibberish(element):
                    pattern = regex_from_list([element])
                    new_path = list(path)
                    new_path.append(pattern)
                    for candidate in candidates[:]:
                        if re.match(pattern + "$", candidate):
                            candidates.remove(candidate)
                            entry = dictionary.get(pattern, {})
                            try:
                                for key in list(dictionary[candidate].keys()):
                                    if key in entry.keys():
                                        entry[key] = merge_two_subtrees_with_same_root(entry[key], dictionary[candidate][key])
                                    else:
                                        entry[key] = dictionary[candidate].get(key, {})
                            except KeyError:
                                pass
                            if pattern not in new_patterns:
                                new_patterns.append(pattern)
                            dictionary[pattern] = entry
                            del dictionary[candidate]
                else:
                    new_path = list(path)
                    new_path.append(re.escape(element))
                    try:
                        regex_from_tree(
                            dictionary[element], finished_patterns, seperator, new_path
                        )
                    except KeyError:
                        pass
            for pattern in new_patterns:
                new_path = list(path)
                new_path.append(pattern)
                regex_from_tree(dictionary[pattern], finished_patterns, seperator, new_path)

            patterns = sorted(patterns, key=len, reverse=True)
            if patterns:
                # if substrings are shared between strings, process patterns.
                remaining_strings = list(dictionary.keys())
                for pattern in patterns:
                    matched = False
                    if remaining_strings:
                        for string in list(dictionary.keys()):
                            if string in remaining_strings and re.fullmatch(pattern, string):
                                matched = True
                    if matched:
                        # pattern matched on something. summarise subfolders of
                        # matching folders and proceed to next level.
                        new_path = list(path)
                        new_path.append(pattern)
                        for candidate in candidates[:]:
                            if re.match(pattern + "$", candidate):
                                candidates.remove(candidate)
                                entry = dictionary.get(pattern, {})
                                try:
                                    for key in list(dictionary[candidate].keys()):
                                        if key in entry.keys():
                                            entry[key] = merge_two_subtrees_with_same_root(entry[key], dictionary[candidate][key])
                                        else:
                                            entry[key] = dictionary[candidate].get(key, {})
                                except KeyError:
                                    pass
                                dictionary[pattern] = entry
                                del dictionary[candidate]
                        if (
                            pattern not in dictionary.keys() or not dictionary[pattern]
                        ) and new_path:
                            # top level reached, this is the finished pattern
                            # print(new_path)
                            finished_patterns.append(seperator.join(new_path))
                            continue
                        regex_from_tree(
                            dictionary[pattern], finished_patterns, seperator, new_path
                        )


def merge_two_subtrees_with_same_root(tree_1, tree_2):
    _new = tree_1.copy()
    for first_key in tree_1.keys():
        if first_key in tree_2.keys():
            _new[first_key] = merge_two_subtrees_with_same_root(tree_1[first_key], tree_2[first_key])
        else:
            _new.update({first_key: tree_1[first_key]})

    for second_key in tree_2.keys():
        if not second_key in tree_1.keys():
            _new.update({second_key: tree_2[second_key]})

    return _new

# Input:
#    list of strings
# Output:
#    list of regexes inferred from strings
#    list of strings for which no regex could be inferred
def generate_expressions(strings):
    # first round: split by file extension and length, then use
    # Global Sequence Alignment
    finished_patterns = detect_string_similarities(strings)

    # remove strings, for which a pattern could be generated
    for pattern in finished_patterns:
        for string in strings[:]:
            if re.fullmatch(pattern, string):
                strings.remove(string)

    # second round: Global Sequence Alignment over the remaining strings
    patterns, no_matches = regex_from_gsa(strings)
    return finished_patterns + patterns, no_matches


# Given a list of strings.
# Split each string by its file-extension, if available.
# Then generate regular expressions using global sequence alignment,
# re-introduce file-extension afterwards.
# Only compares strings with same file-extension with other strings.
def detect_string_similarities(strings):
    # group by file-extensions (string ends with a dot followed by not more
    # than 4 letters)
    def group_by_extensions():
        extensions = {}
        for string in strings:
            if has_file_ending(string):
                ext = string.split(".")[-1]
                name = ".".join(string.split(".")[:-1])
                entry = extensions.get(ext, [])
                entry.append(name)
                extensions[ext] = entry
            else:
                entry = extensions.get("no_extension", [])
                entry.append(string)
                extensions["no_extension"] = entry
        return extensions

    def process_gibberish(str_list_types, ext, str_list):
        gibberish = []
        for s in str_list_types:
            if is_gibberish(s):
                gibberish.append(s)

        for pat in regex_from_gsa(gibberish)[0]:
            matches = [s for s in str_list if re.fullmatch(pat, s)]
            if len(matches) == len(str_list) or len(matches) > 4:
                if ext != "no_extension":
                    patterns.append(r"\.".join([pat, re.escape(ext)]))
                else:
                    patterns.append(pat)

    patterns = []
    for ext, str_list in group_by_extensions().items():
        contains_special_char = []
        str_types = {}

        # further divide groups:
        # - by special chars, if present
        # - by string type, if no special chars are present
        for string in str_list:
            if re.search(r"[.,;+_\-!=@§$%&()#\[\]{}€*]", string):
                contains_special_char.append(string)
            else:
                str_type = regex_type_from_string(string)[0]
                entries = str_types.get(str_type, [])
                entries.append(string)
                str_types[str_type] = entries

        for pat in regex_from_gsa(contains_special_char)[0]:
            matches = [s for s in str_list if re.fullmatch(pat, s)]
            if len(matches) == len(str_list) or len(matches) > 4:
                if ext != "no_extension":
                    patterns.append(r"\.".join([pat, re.escape(ext)]))
                else:
                    patterns.append(pat)

        for _, str_list_types in str_types.items():
            process_gibberish(str_list_types, ext, str_list)

    return patterns


# try to create a regex from 2 strings, which matches on both strings
# this function is used as a a fallback, if 2 strings are too large
# to be compared with GSA
def regex_from_sequencer(s1, s2):
    # find substrings between pairs of strings
    def get_common_substrings():
        common_substrings = {"start": [], "middle": [], "end": []}
        s = SequenceMatcher(None, s1, s2)
        for match in s.get_matching_blocks():
            if match.size < 3:
                continue
            if match.a == 0 and match.b == 0:
                common_substrings["start"].append(s1[match.a : match.a + match.size])
            elif match.a + match.size == len(s1) and match.b + match.size == len(s2):
                common_substrings["end"].append(s1[match.a : match.a + match.size])
            elif match.a == match.b:
                common_substrings["middle"].append(s1[match.a : match.a + match.size])
        common_substrings["start"] = list(set(common_substrings["start"]))
        common_substrings["middle"] = list(set(common_substrings["middle"]))
        common_substrings["end"] = list(set(common_substrings["end"]))
        return common_substrings

    common_substrings = get_common_substrings()
    if not (common_substrings["start"] or common_substrings["middle"] or common_substrings["end"]):
        return None

    # build blueprint expression with substrings
    pat = ""
    remainder_1 = s1
    remainder_2 = s2
    for start in common_substrings["start"]:
        if re.match(re.escape(start), remainder_1) and re.match(re.escape(start), remainder_2):
            pat = re.escape(start)
            if not common_substrings["middle"] and not common_substrings["end"]:
                pat += r"(.)*"
                remainder_1 = "".join(remainder_1.split(start)[1:])
                remainder_2 = "".join(remainder_2.split(start)[1:])
            break
    for middle in common_substrings["middle"]:
        if pat != "":
            if re.search("^.+" + re.escape(middle) + ".+$", remainder_1) and re.search(
                "^.+" + re.escape(middle) + ".+$", remainder_2
            ):
                pat += "(.)*" + re.escape(middle)
                remainder_1 = "".join(remainder_1.split(middle)[1:])
                remainder_2 = "".join(remainder_2.split(middle)[1:])
                break
            elif re.match(re.escape(middle) + ".+$", remainder_1) and re.match(
                re.escape(middle) + ".+$", remainder_2
            ):
                pat += re.escape(middle)
                remainder_1 = "".join(remainder_1.split(middle)[1:])
                remainder_2 = "".join(remainder_2.split(middle)[1:])
                break
        elif re.search("^.+" + re.escape(middle) + ".+$", remainder_1) and re.search(
            "^.+" + re.escape(middle) + ".+$", remainder_2
        ):
            pat = "(.)*" + re.escape(middle)
            remainder_1 = "".join(remainder_1.split(middle)[1:])
            remainder_2 = "".join(remainder_2.split(middle)[1:])
            break
    if common_substrings["end"]:
        for end in common_substrings["end"]:
            if pat != "":
                if re.search("^.+" + re.escape(end) + "$", remainder_1) and re.search(
                    "^.+" + re.escape(end) + "$", remainder_2
                ):
                    pat += "(.)*" + re.escape(end)
                elif re.match(re.escape(end) + "$", remainder_1) and re.match(
                    re.escape(end) + "$", remainder_2
                ):
                    pat += re.escape(end)
            elif re.search("^.+" + re.escape(end) + "$", remainder_1) and re.search(
                "^.+" + re.escape(end) + "$", remainder_2
            ):
                pat = "(.)*" + re.escape(end)
                break
    elif remainder_1 and remainder_2:
        pat += "(.)*"
    if pat != "" and pat != "(.)*" and re.match(pat + "$", s1) and re.match(pat + "$", s2):
        return pat
    return None


# input:
#   list of strings
# output:
#   list of regexes inferred from global sequence alignment,
#   list of strings without matching regex
def regex_from_gsa(strings):
    def eval_regex(patterns_dict, pattern_re):
        # on how many strings does the regex match?
        for s in strings:
            if re.fullmatch(pattern_re, s):
                str_matches = patterns_dict.get(pattern_re, [])
                if s not in str_matches:
                    str_matches.append(s)
                    patterns_dict[pattern_re] = str_matches

    def do_alignment(s1, s2):
        # Create sequences to be aligned.
        str1 = Sequence(re.escape(s1))
        str2 = Sequence(re.escape(s2))

        # Create a vocabulary and encode the sequences.
        v = Vocabulary()
        str1_encoded = v.encodeSequence(str1)
        str2_encoded = v.encodeSequence(str2)

        # Create a scoring and align the sequences using global aligner.
        scoring = SimpleScoring(2, -1)
        aligner = GlobalSequenceAligner(scoring, -1)
        _, alignments = aligner.align(str1_encoded, str2_encoded, backtrace=True)

        # Create sequence profiles out of alignments.
        profiles = [Profile.fromSequenceAlignment(a) for a in alignments]
        for encoded in profiles:
            profile = v.decodeProfile(encoded)
            # print(profile.pattern())
            # profiles look something like this:
            # "s o m e p a * * * * t * * * t * * e r n"
            # clean this up and replace groups of * with regex,
            # so the result looks like this: "somepa(.)*ern"
            pattern = re.sub("(?<! ) {1}(?! )| (?= )", "", profile.pattern())
            if re.fullmatch(r"[,.;+_\-!=@§$%&()#\[\]{}€ a-zA-Z0-9*]+", pattern):
                # if pattern does not contain 'exotic' chars, keep
                # special chars in place
                pattern = re.sub(r"([\*]+)([a-zA-Z0-9]{0,2}[\*]+)*", "(.)*", pattern)
            else:
                # if pattern contains 'exotic' chars, i.e. han or kanji,
                # disregard special chars if they appear alone
                pattern = re.sub(r"([\*]+)([^\*]{0,2}[\*]+)*", "(.)*", pattern)
            try:
                # do NOT use the universal matching group on its own!!
                if re.match(r"\(\.\)\*$", pattern) or pattern == "":
                    continue
                eval_regex(patterns, pattern)
            except:  # noqa
                pass

    patterns = {}
    for s1, s2 in itertools.combinations(strings, 2):
        if len(max([s1, s2], key=len)) > 512:
            # string is too long
            regex = regex_from_sequencer(s1, s2)
            if regex:
                eval_regex(patterns, regex)
            continue
        do_alignment(s1, s2)

    remove_too_specific_patterns(patterns)

    finished_patterns = {}
    for pattern, string_list in patterns.items():
        # if the pattern does not match at least on three input strings
        # it is considered too specific and ignored (rule of three)
        if len(string_list) < 3:
            continue
        pat = resolve_to_more_specific_regex(string_list, pattern)
        finished_patterns[pat] = []

    # find strings, which have no matching pattern
    no_matches = []
    for string in strings:
        matched = False
        for pattern in finished_patterns:
            if re.match(pattern + "$", string):
                matched = True
                finished_patterns[pattern].append(string)
        if not matched:
            no_matches.append(string)

    finished_patterns = list(finished_patterns.keys())
    if finished_patterns != [""]:
        return finished_patterns, no_matches
    return None, no_matches


# Given a dict of regular expressions [keys] and the strings they matched on
# [values]. Compare them with each other and remove more specific ones, then
# join their lists of strings they matched on - the more generic expression will
# match on both lists.
# Example:
# Input:
#    {'\~(.)*': ['~aclywlmm',
#                '~csrukx',
#                '~gugar'],
#     '\~(.)*k': ['~aevock', '~biqjbuk'],
#     '\~a(.)*': ['~aclywlmm', '~aevock', '~avualwy'],
#     '\~kw(.)*': ['~kwcfoa', '~kwvpeene']}
# Output:
#    {'\~(.)*': [ *joined list of all strings from lists above, since '\~(.)*' matches on all other keys* ]}  # noqa
def remove_too_specific_patterns(patterns):
    for p1, p2 in itertools.combinations(patterns.keys(), 2):
        if (len(p1) > 8 or len(p2) > 8) and (
            len(p1) * 2 / 3 > len(p2) or len(p2) * 2 / 3 > len(p1)
        ):
            continue
        p1_test_regex = "(.)*".join([re.escape(x) for x in p1.split("(.)*")])
        p2_test_regex = "(.)*".join([re.escape(x) for x in p2.split("(.)*")])
        if re.fullmatch(p1_test_regex, p2):
            # p2 is a more specific pattern of p1
            try:
                # remove p2
                patterns[p1] = list(set(patterns[p1] + patterns[p2]))
                # print("DEL:", p2, p1)
                del patterns[p2]
            except KeyError:
                pass
        elif re.fullmatch(p2_test_regex, p1):
            # p1 is a more specific pattern of p2
            try:
                patterns[p2] = list(set(patterns[p2] + patterns[p1]))
                # print("DEL:", p1, p2)
                del patterns[p1]
            except KeyError:
                pass
    for key in list(patterns.keys()):
        if not patterns[key]:
            del patterns[key]


def resolve_quantifier(regex, str_lengths):
    for group_id, lengths in str_lengths.items():
        if f"(?P<{group_id}>" not in regex:
            continue
        if conf.include_re_len:
            regex = re.sub(
                r"\(\?P<" + group_id + r">(\[[^\]]+\]|\.)(\+)",
                partial(replace_quantifier, lengths),
                regex,
            )
    return regex


def replace_quantifier(lengths, match):
    if len(lengths) == 1:
        return match.group().replace("+", "{" + str(lengths[0]) + "}")
    if conf.get_min_max_len:
        return match.group().replace("+", "{" + str(min(lengths)) + "," + str(max(lengths)) + "}")
    return match.group()


# resolve "(.)*" to more specific regex
def resolve_to_more_specific_regex(strings, pattern):
    group_count = pattern.count("(.)*")
    group_pattern = pattern
    for i in range(0, group_count):
        group_pattern = group_pattern.replace("(.)*", "(?P<grp" + str(i) + ">(.*))", 1)

    groups = {}
    for i in range(0, group_count):
        groups[i] = []
        for string in strings:
            if re.match(group_pattern, string):
                groups[i].append(re.match(group_pattern, string).group("grp" + str(i)))

    for key in groups:
        if list(set(groups[key])) == [""]:
            group_pattern = group_pattern.replace("(?P<grp" + str(key) + ">(.*))", "")
        else:
            regex = regex_from_list(list(set(groups[key])))
            group_pattern = group_pattern.replace("(?P<grp" + str(key) + ">(.*))", regex)
    return group_pattern


# convert a list of strings to a regular expression based on what the most
# generic observed string type, e.g:
# ['123', '456'] --> string type is number, output '\d+' or '\d{3}'
# ['DE4D', 'beef', '1234'] --> string type is hex, output '[0-9a-fA-F]+' or '[0-9a-fA-F]{4}'  # noqa
# ['123', 'beef', 'random string'] --> string type is alphanumeric, output '\w+'
def regex_from_list(strings):
    types = []
    special_chars = {}
    prefix = ""
    suffix = ""
    all_have_file_ending = True
    file_endings = []

    for string in strings:
        if not has_file_ending(string):
            all_have_file_ending = False
            break
        else:
            file_endings.append(string.split(".")[-1])
    if all_have_file_ending and len(file_endings) == 1:
        # if all strings have the same ending, use it as suffix
        suffix = r"\." + file_endings[0]
        for i, s in enumerate(strings):
            strings[i] = ".".join(s.split(".")[0:-1])

    for string in strings:
        typ, chars = regex_type_from_string(string)
        if typ not in types:
            types.append(typ)
        for char in chars:
            if char in special_chars.keys():
                special_chars[char] += 1
            else:
                special_chars[char] = 1

    # too many special characters?
    # can happen, if different special chars appear between reports
    # in such a case, use universal matching dot, as we can not know if we
    # ever got all chars which are possible to appear...
    # Note: fixed special chars, e.g. brackets or those which always appear at
    # the same position are already accounted for! these here are variable parts
    # TODO: what is 'too many'??
    global group_ctr
    if len(special_chars.keys()) >= 4:
        if conf.inter_observables_enabled:
            group_ctr += 1
            return prefix + "(?P<id_" + str(group_ctr) + ">.+)" + suffix
        return prefix + ".+" + suffix

    return str_type_to_regex(types, list(special_chars.keys()), prefix, suffix)


def regex_type_from_string(string):
    # get special chars
    special_chars = list(re.sub(r"[a-zA-Z0-9]", "", string))

    # remove special chars
    if special_chars:
        string = re.sub("[" + re.escape("".join(special_chars)) + "]", "", string)

    # return most specific type, not considering special chars
    if re.match(r"^[0-9]+$", string):
        return "number", special_chars

    if re.match(r"^[0-9a-f]+$", string):
        return "hex_l", special_chars
    if re.match(r"^[0-9A-F]+$", string):
        return "hex_u", special_chars
    if re.match(r"^[0-9a-fA-F]+$", string):
        return "hex", special_chars

    if re.match(r"^[a-z]+$", string):
        return "letters_l", special_chars
    if re.match(r"^[A-Z]+$", string):
        return "letters_u", special_chars
    if re.match(r"^[a-zA-Z]+$", string):
        return "letters", special_chars

    if re.match(r"^[0-9a-z]+$", string):
        return "alphanumeric_l", special_chars
    if re.match(r"^[0-9A-Z]+$", string):
        return "alphanumeric_u", special_chars
    if re.match(r"^[0-9a-zA-Z]+$", string):
        return "alphanumeric", special_chars

    return "unknown", special_chars


# input:
#    list of types as strings, e.g. ['hex', 'number']
#    list of special characters, e.g. [';', '!']
#    prefix-string, e.g. 'foo'
#    suffix-string, e.g. 'bar'
# output:
#    string with RegEx derived from prefix, types, special chars and suffix
#    e.g. 'foo[0-9a-f;!]+bar'
def str_type_to_regex(types, special_chars, prefix, suffix):
    global group_ctr
    if "alphanumeric" in types or ("letters" in types and "number" in types and len(types) == 2):
        if conf.inter_observables_enabled:
            group_ctr += 1
            return (
                prefix
                + "(?P<id_"
                + str(group_ctr)
                + ">[0-9a-zA-Z"
                + re.escape("".join(special_chars))
                + "]"
                + "+"
                + ")"
                + suffix
            )
        return prefix + "[0-9a-zA-Z" + re.escape("".join(special_chars)) + "]" + "+" + suffix
    if "alphanumeric_l" in types or (
        "letters_l" in types and "number" in types and len(types) == 2
    ):
        if conf.inter_observables_enabled:
            group_ctr += 1
            return (
                prefix
                + "(?P<id_"
                + str(group_ctr)
                + ">[0-9a-z"
                + re.escape("".join(special_chars))
                + "]"
                + "+"
                + ")"
                + suffix
            )
        return prefix + "[0-9a-z" + re.escape("".join(special_chars)) + "]" + "+" + suffix
    if "alphanumeric_u" in types or (
        "letters_u" in types and "number" in types and len(types) == 2
    ):
        if conf.inter_observables_enabled:
            group_ctr += 1
            return (
                prefix
                + "(?P<id_"
                + str(group_ctr)
                + ">[0-9A-Z"
                + re.escape("".join(special_chars))
                + "]"
                + "+"
                + ")"
                + suffix
            )
        return prefix + "[0-9A-Z" + re.escape("".join(special_chars)) + "]" + "+" + suffix
    if "letters" in types:
        if conf.inter_observables_enabled:
            group_ctr += 1
            return (
                prefix
                + "(?P<id_"
                + str(group_ctr)
                + ">[a-zA-Z"
                + re.escape("".join(special_chars))
                + "]"
                + "+"
                + ")"
                + suffix
            )
        return prefix + "[a-zA-Z" + re.escape("".join(special_chars)) + "]" + "+" + suffix
    if "letters_l" in types:
        if conf.inter_observables_enabled:
            group_ctr += 1
            return (
                prefix
                + "(?P<id_"
                + str(group_ctr)
                + ">[a-z"
                + re.escape("".join(special_chars))
                + "]"
                + "+"
                + ")"
                + suffix
            )
        return prefix + "[a-z" + re.escape("".join(special_chars)) + "]" + "+" + suffix
    if "letters_u" in types:
        if conf.inter_observables_enabled:
            group_ctr += 1
            return (
                prefix
                + "(?P<id_"
                + str(group_ctr)
                + ">[A-Z"
                + re.escape("".join(special_chars))
                + "]"
                + "+"
                + ")"
                + suffix
            )
        return prefix + "[A-Z" + re.escape("".join(special_chars)) + "]" + "+" + suffix
    if "hex" in types:
        if conf.inter_observables_enabled:
            group_ctr += 1
            return (
                prefix
                + "(?P<id_"
                + str(group_ctr)
                + ">[0-9a-fA-F"
                + re.escape("".join(special_chars))
                + "]"
                + "+"
                + ")"
                + suffix
            )
        return prefix + "[0-9a-fA-F" + re.escape("".join(special_chars)) + "]" + "+" + suffix
    if "hex_l" in types:
        if conf.inter_observables_enabled:
            group_ctr += 1
            return (
                prefix
                + "(?P<id_"
                + str(group_ctr)
                + ">[0-9a-f"
                + re.escape("".join(special_chars))
                + "]"
                + "+"
                + ")"
                + suffix
            )
        return prefix + "[0-9a-f" + re.escape("".join(special_chars)) + "]" + "+" + suffix
    if "hex_u" in types:
        if conf.inter_observables_enabled:
            group_ctr += 1
            return (
                prefix
                + "(?P<id_"
                + str(group_ctr)
                + ">[0-9A-F"
                + re.escape("".join(special_chars))
                + "]"
                + "+"
                + ")"
                + suffix
            )
        return prefix + "[0-9A-F" + re.escape("".join(special_chars)) + "]" + "+" + suffix
    if "number" in types:
        if conf.inter_observables_enabled:
            group_ctr += 1
            return (
                prefix
                + "(?P<id_"
                + str(group_ctr)
                + r">[\d"
                + re.escape("".join(special_chars))
                + "]"
                + "+"
                + ")"
                + suffix
            )
        return prefix + r"[\d" + re.escape("".join(special_chars)) + "]" + "+" + suffix
    if conf.inter_observables_enabled:
        group_ctr += 1
        return prefix + "(?P<id_" + str(group_ctr) + ">[^\\\\]" + "+" + ")" + suffix
    return prefix + "[^\\\\]" + "+" + suffix
