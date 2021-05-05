import logging
import os
import pickle
import re

from simple_settings import LazySettings
from ..gibberish_detector.gib_detect_train import train, avg_transition_prob

log = logging.getLogger(__name__)
conf = LazySettings(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "conf.yml"))

gibberish_model_data_file = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "gibberish_detector",
        "gib_model.pki",
    )
)
if not os.path.exists(gibberish_model_data_file):
    log.info("Training gibberish model...")
    train()
else:
    log.info("Gibberish detector is already trained: Let's go!")
gibberish_model_data = pickle.load(open(gibberish_model_data_file, "rb"))
gibberish_model_mat = gibberish_model_data["mat"]
gibberish_threshold = gibberish_model_data["thresh"]


def is_gibberish(string):
    if len(string) <= 3:
        return False
    if has_file_ending(string) and len(".".join(string.split(".")[:-1])) <= 3:
        return False
    if string.isdecimal():
        return True
    return not avg_transition_prob(string, gibberish_model_mat) > gibberish_threshold


# HELPER FUNCTIONS
def safe_list_get(list_to_look_at, index, default):
    try:
        return list_to_look_at[index]
    except KeyError:
        return default


def get_from_dict(data_dict, path_list):
    for k in path_list:
        data_dict = data_dict[k]
    return data_dict


def nested_set_for_processes(dic, keys, value):
    for key in keys[:-1]:
        dic = dic.setdefault(key, {})
    dic[keys[-1]] = value


def nested_set_for_files(dic, keys):
    for key in keys:
        dic = dic.setdefault(key, {})


def is_windows_path(string):
    if re.fullmatch(
        r"^(?:[A-Z]\:|\.|(?:file\:\/\/|\\\\)[^\\\/\:\*\?\<\>\""
        r"\|]+)(?:(?:\\|\/)[^\\\/\:\*\?\<\>\"\|]+)*(?:\\|\/)?$",
        string,
    ):
        return True
    return False


def contains_windows_path(string):
    if re.search(
        r"(?:[A-Z]\:|\.|(?:file\:\/\/|\\\\)[^\\\/\:\*\?\<\>\""
        r"\|]+)(?:(?:\\|\/)[^\\\/\:\*\?\<\>\"\|]+)*(?:\\|\/)?",
        string,
    ):
        return True
    return False


def has_file_ending(string):
    if re.match(r".+\.[0-9a-zA-z]{1-3}$", string):
        return True
    return False


# removes a leaf from a nested dict (leaf is an array of the nodes)
def delete_leaf_from_nested_dict(nested_dict, leaf):
    l_dict = nested_dict
    for node in leaf:
        try:
            if len(l_dict[node]) == 1:
                del l_dict[node]
                break
            else:
                l_dict = l_dict[node]
        except KeyError:
            pass
    return nested_dict
