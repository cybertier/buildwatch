from ..gen_regex import regex_from_tree, generate_expressions, merge_two_subtrees_with_same_root
import json
from pathlib import Path


def test_regex_from_tree_files():
    path_to_tree = Path("/home/ruben/Desktop/file-type/regex-tree.txt")
    tree_data = json.load(path_to_tree.open("r"))
    finished_patterns = []
    regex_from_tree(tree_data, finished_patterns)
    assert finished_patterns == ['/[0-9a-zA-Z]+/test/\\.gitattributes', '/[0-9a-zA-Z]+/test/[0-9a-zA-Z\\-]+\\.js']


def test_generate_expressions():
    list_of_str = ['root', 'tmp', 'tmp7s5cwK', 'tmpokitXR', 'tmplJnxZf', 'tmp1q9dss', 'tmpVYCtOn', 'tmpt3FV4G', 'tmp8iTVYp', 'tmplnl8ne', 'tmpzq8Fv7', 'tmppui1EC']
    generated_patterns, rest = generate_expressions(list_of_str)
    assert generated_patterns == ['tm[0-9a-zA-Z]+']
    assert rest == ["root"]


def test_regex_from_tree_processes():
    path_to_tree = Path(__file__).with_name("process-tree.txt")
    tree_data = json.load(path_to_tree.open("r"))
    finished_patterns = []
    regex_from_tree(tree_data, finished_patterns)
    assert finished_patterns == [
        'git\\ checkout\\ 745e9b7314064e66a7257f9b361030e6055980b8',
        '/usr/lib/git\\-core/git\\ index\\-pack\\ \\-\\-stdin\\ \\-\\-fix\\-thin\\ \\-\\-keep=fetch\\-pack\\ 177[\\d]+\\ on\\ buildwatch\\ \\-\\-check\\-self\\-contained\\-and\\-connected',
        '/bin/sh\\ \\-c\\ git\\-upload\\-pack\\ /root/[a-z\\.]+/_git\\-remotes/git\\-github\\-com\\-jashkenas\\-underscore\\-git\\-e8740c92\\ git\\-upload\\-pack\\ /root/[a-z\\.]+/_git\\-remotes/git\\-github\\-com\\-jashkenas\\-underscore\\-git\\-e8740c92',
        '/tmp[0-9a-zA-Z_]+/\\.buildwatch\\.sh',
        '[a-z\\ \\-]+\\ /root/[a-z\\.]+/_git\\-remotes/git\\-github\\-com\\-jashkenas\\-underscore\\-git\\-e8740c92',
        '[a-z\\ \\-]+\\ /root/[a-z\\.]+/_git\\-remotes/git\\-github\\-com\\-[0-9a-zA-Z\\-]+\\-git\\-[0-9a-f]+\\ /tmp/npm\\-1[0-9a-f\\-]+/git\\-cache\\-[0-9a-f]+/9b9240619cc3c20ef596323de36a0330ece42180',
        '[a-z\\ \\-]+\\ /root/[a-z\\.]+/_git\\-remotes/git\\-github\\-com\\-[0-9a-zA-Z\\-]+\\-git\\-[0-9a-f]+\\ /tmp/npm\\-1[0-9a-f\\-]+/git\\-cache\\-[0-9a-f]+/2238043c465090cd4303450d6c048520562179ea',
        '[a-z\\ \\-]+\\ /root/[a-z\\.]+/_git\\-remotes/git\\-github\\-com\\-[0-9a-zA-Z\\-]+\\-git\\-[0-9a-f]+\\ /tmp/npm\\-1[0-9a-f\\-]+/git\\-cache\\-[0-9a-f]+/[0-9a-f]+',
        '[a-z\\ \\-]+\\ /tmp[0-9a-zA-Z_]+/\\.buildwatch\\.sh'
    ]


def test_merge_two_subtrees_with_same_root():
    tree_1 = {
        "root": {
            "tree_1a": {},
            "tree_1b": {}
        }
    }
    tree_2 = {"root": {"tree_2a": {}, "tree_2b": {}, "tree_2c": {}}}
    _expected_tree = merge_two_subtrees_with_same_root(tree_1, tree_2)
    assert _expected_tree == {
        "root": {
            "tree_1a": {},
            "tree_1b": {},
            "tree_2a": {},
            "tree_2b": {},
            "tree_2c": {}
        }
    }