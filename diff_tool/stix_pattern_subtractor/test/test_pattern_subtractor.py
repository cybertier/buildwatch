import json
from pathlib import Path

import stix2

from diff_tool.stix_pattern_subtractor import (
    parse_stix_objects,
    pattern_is_one_expression,
    split_pattern,
    find_all_objects_to_delete,
    find_stix_objects,
    find_stix_object_by_type,
    remove_matching_objects,
)


def test_parse_stix_objects():
    stix_report_file = Path(__file__).with_name("stix2.json")
    stix_report = stix2.parse(json.load(stix_report_file.open()), allow_custom=True)
    stix_objects = parse_stix_objects(stix_report.objects)
    assert len(stix_objects["domain-name"]) == 1
    assert len(stix_objects["file"]) == 3
    assert len(stix_objects["process"]) == 1


def test_pattern_is_one_expression():
    pattern_file = Path(__file__).with_name("sample_dir.json")
    patterns = stix2.parse(json.load(pattern_file.open()), allow_custom=True)
    assert not pattern_is_one_expression(patterns.objects[0].pattern)
    assert pattern_is_one_expression(patterns.objects[1].pattern)
    assert not pattern_is_one_expression(patterns.objects[2].pattern)


def test_find_stix_objects():
    pattern_file = Path(__file__).with_name("sample_dir.json")
    patterns = stix2.parse(json.load(pattern_file.open()), allow_custom=True)

    stix_report_file = Path(__file__).with_name("stix2.json")
    stix_report = stix2.parse(json.load(stix_report_file.open()), allow_custom=True)
    stix_objects = parse_stix_objects(stix_report.objects)

    found_objects = []
    for indicator in patterns.objects:
        if pattern_is_one_expression(indicator.pattern):
            found_objects.extend(find_stix_objects(stix_objects, indicator.pattern))
    assert found_objects == [
        "file:parent_directory_str MATCHES "
        "'/var/run/docker/runtime-runc/moby/643891a6098c437715d8cba505b2d49440f3d6e6c9da99400b1d4788bce5b6d1' "
        "AND file:name MATCHES 'runc.BOduQP'",
        "file:parent_directory_str MATCHES "
        "'/var/run/docker/runtime-runc/moby/643891a6098c437715d8cba505b2d49440f3d6e6c9da99400b1d4788bce5b6d1' "
        "AND file:name MATCHES 'evil1.BOduQP'",
        "file:parent_directory_str MATCHES '/komplett/mega/neu' AND file:name MATCHES "
        "'randomevil'",
    ]


def test_split_pattern():
    pattern = (
        "["
        "file:parent_directory_str MATCHES '/var/run/docker/runtime-runc/moby/643891a6098c437715d8cba505b2d49440f3d6e6c9da99400b1d4788bce5b6d1' "
        "AND "
        "file:name MATCHES 'evil1.BOduQP'"
        "] AND ["
        "file:parent_directory_str MATCHES '/var/run/docker/runtime-runc/moby/643891a6098c437715d8cba505b2d49440f3d6e6c9da99400b1d4788bce5b6d1' "
        "AND "
        "file:name MATCHES 'runc.BOduQP'"
        "]"
    )
    patterns = split_pattern(pattern)
    assert patterns == [
        "file:parent_directory_str MATCHES '/var/run/docker/runtime-runc/moby/643891a6098c437715d8cba505b2d49440f3d6e6c9da99400b1d4788bce5b6d1' AND file:name MATCHES 'evil1.BOduQP'",
        "file:parent_directory_str MATCHES '/var/run/docker/runtime-runc/moby/643891a6098c437715d8cba505b2d49440f3d6e6c9da99400b1d4788bce5b6d1' AND file:name MATCHES 'runc.BOduQP'",
    ]


def test_find_all_objects_to_delete():
    patterns = (
        "["
        "file:parent_directory_str MATCHES '/var/run/docker/runtime-runc/moby/643891a6098c437715d8cba505b2d49440f3d6e6c9da99400b1d4788bce5b6d1' "
        "AND "
        "file:name MATCHES 'evil1.BOduQP'"
        "] AND ["
        "file:parent_directory_str MATCHES '/var/run/docker/runtime-runc/moby/643891a6098c437715d8cba505b2d49440f3d6e6c9da99400b1d4788bce5b6d1' "
        "AND "
        "file:name MATCHES 'runc.BOduQP'"
        "]"
    )
    patterns = split_pattern(patterns)
    stix_report_file = Path(__file__).with_name("stix2.json")
    stix_report = stix2.parse(json.load(stix_report_file.open()), allow_custom=True)
    stix_objects = parse_stix_objects(stix_report.objects)

    objects_to_delete = find_all_objects_to_delete(stix_objects, patterns)
    assert objects_to_delete == [
        "file:parent_directory_str MATCHES "
        "'/var/run/docker/runtime-runc/moby/643891a6098c437715d8cba505b2d49440f3d6e6c9da99400b1d4788bce5b6d1' "
        "AND file:name MATCHES 'evil1.BOduQP'",
        "file:parent_directory_str MATCHES "
        "'/var/run/docker/runtime-runc/moby/643891a6098c437715d8cba505b2d49440f3d6e6c9da99400b1d4788bce5b6d1' "
        "AND file:name MATCHES 'runc.BOduQP'",
    ]


def test_find_stix_object_by_type():
    pattern = (
        "file:parent_directory_str MATCHES '/var/run/docker/runtime-runc/moby/643891a6098c437715d8cba505b2d49440f3d6e6c9da99400b1d4788bce5b6d1' "
        "AND file:name MATCHES 'evil1.BOduQP'"
    )
    stix_report_file = Path(__file__).with_name("stix2.json")
    stix_report = stix2.parse(json.load(stix_report_file.open()), allow_custom=True)
    stix_objects = parse_stix_objects(stix_report.objects)
    objects_to_delete = find_stix_object_by_type(stix_objects, "file", pattern)
    assert objects_to_delete == [
        "file:parent_directory_str MATCHES "
        "'/var/run/docker/runtime-runc/moby/643891a6098c437715d8cba505b2d49440f3d6e6c9da99400b1d4788bce5b6d1' "
        "AND file:name MATCHES 'evil1.BOduQP'"
    ]


def test_remove_matching_objects():
    stix_report_file = Path(__file__).with_name("stix2.json")
    stix_report = stix2.parse(json.load(stix_report_file.open()), allow_custom=True)
    stix_objects = parse_stix_objects(stix_report.objects)
    objects_to_delete = [
        "file:parent_directory_str MATCHES "
        "'/var/run/docker/runtime-runc/moby/643891a6098c437715d8cba505b2d49440f3d6e6c9da99400b1d4788bce5b6d1' "
        "AND file:name MATCHES 'evil1.BOduQP'"
    ]
    actual_objects = remove_matching_objects(stix_objects, objects_to_delete)
    assert objects_to_delete[0] not in actual_objects["file"]
