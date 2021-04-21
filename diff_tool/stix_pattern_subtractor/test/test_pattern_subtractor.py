import json
from pathlib import Path

import stix2
from stix2.v21 import File, Process, DomainName, Bundle

from diff_tool.stix_pattern_subtractor.pattern_subtractor import (
    find_stix_objects,
    parse_stix_objects,
    load_stix_report_and_patterns,
    find_objects_matching_patterns,
    delete_objects,
)


def test_load_stix_report_and_patterns():
    report = Path("/home/ruben/Desktop/cuckoo/stix_1.json")
    patterns_path = Path("/home/ruben/Desktop/cuckoo/patterns.json")
    objects, patterns = load_stix_report_and_patterns(report, patterns_path)
    assert len(patterns.objects) == 1037
    assert objects


def test_parse_stix_objects():
    stix_objects = [
        File(
            name="rpc-socket.md",
            full_output='Mon Feb  1 08:11:06 2021.507489 |npm@7f526098adae[17717] openat(AT_FDCWD, "/tmpomWnSX/package/doc/api/rpc-socket.md", O_RDONLY|O_CLOEXEC) = 10',
            timestamp="Tue Feb  2 09:32:26 2021",
            container_id="",
            id="file--18288093-6465-11eb-adcb-ef638f602075",
            parent_directory_str="/tmpomWnSX/package/doc/api",
            allow_custom=True,
        ),
        File(
            name="refs",
            full_output='Tue Feb  2 09:32:26 2021.204445 |git@7fa8813c7bb7[17731] mkdir("/tmp/npm-17709-ab210a8e/git-cache-2ea60dab/9b9240619cc3c20ef596323de36a0330ece42180/.git/logs/refs", 0777) = 0',
            timestamp="Mon Feb  1 08:11:06 2021",
            container_id="",
            id="file--c6cd744d-6539-11eb-8fc6-edd1fd8b9760",
            parent_directory_str="/tmp/npm-17709-ab210a8e/git-cache-2ea60dab/9b9240619cc3c20ef596323de36a0330ece42180/.git/logs",
            allow_custom=True,
        ),
        Process(
            full_output='Mon Feb  1 08:11:07 2021.977686 |git@7fb2ac106cdd[17728] execve("/usr/lib/git-core/git", ["/usr/lib/git-core/git", "index-pack", "--stdin", "--fix-thin", "--keep=fetch-pack 17724 on buildwatch", "--check-self-contained-and-connected"], ["GIT_ASKPASS=echo", "GIT_DIR=/root/.npm/_git-remotes/git-github-com-eriksank-EventEmitter4-git-c533a4e5", "HOME=/root", "JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64", "LANG=en_US", "LANGUAGE=en_US:", "LOGNAME=root", "MAIL=/var/mail/root", "PATH=/usr/lib/git-core:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin", ")',
            timestamp="Mon Feb  1 08:11:07 2021",
            container_id="",
            command_line="/usr/lib/git-core/git index-pack --stdin --fix-thin --keep=fetch-pack 17724 on buildwatch --check-self-contained-and-connected",
            id="process--18b252f2-6465-11eb-adcb-ef638f602075",
            executable_path="/usr/lib/git-core/git",
            allow_custom=True,
        ),
        DomainName(
            resolves_to_refs=["ipv6-addr--09dc677d-648e-11eb-adcb-ef638f602075"],
            full_output="Mon Feb  1 13:04:10 2021.045493 |git@7fb679d9c741[17730] connect(3, {AF_INET, 127.0.0.53, 53}, 16) = 0",
            timestamp="Mon Feb  1 13:04:10 2021",
            container_id="",
            value="localhost",
            resolves_to_str="127.0.0.53",
            id="domain-name--09dc677c-648e-11eb-adcb-ef638f602075",
            allow_custom=True,
        ),
    ]

    results = parse_stix_objects(stix_objects)
    assert (
        list(results["file"].keys())[0]
        == "file:parent_directory_str MATCHES '/tmpomWnSX/package/doc/api' AND file:name MATCHES 'rpc-socket.md'"
    )
    assert (
        list(results["file"].keys())[1]
        == "file:parent_directory_str MATCHES '/tmp/npm-17709-ab210a8e/git-cache-2ea60dab/9b9240619cc3c20ef596323de36a0330ece42180/.git/logs' AND file:name MATCHES 'refs'"
    )
    assert (
        list(results["process"].keys())[0]
        == "process:command_line MATCHES '/usr/lib/git-core/git index-pack --stdin --fix-thin --keep=fetch-pack 17724 on buildwatch --check-self-contained-and-connected'"
    )
    assert (
        list(results["domain-name"].keys())[0]
        == "domain-name:value = 'localhost' OR domain-name:resolves_to_str = '127.0.0.53'"
    )


def test_find_stix_objects():
    stix_objects = {
        "domain-name": {
            "domain-name:value = 'localhost' OR domain-name:resolves_to_str = '127.0.0.53'": [
                DomainName(
                    resolves_to_refs=["ipv6-addr--09dc677d-648e-11eb-adcb-ef638f602075"],
                    full_output="Mon Feb  1 13:04:10 2021.045493 |git@7fb679d9c741[17730] connect(3, {AF_INET, 127.0.0.53, 53}, 16) = 0",
                    timestamp="Mon Feb  1 13:04:10 2021",
                    container_id="",
                    value="localhost",
                    resolves_to_str="127.0.0.53",
                    id="domain-name--09dc677c-648e-11eb-adcb-ef638f602075",
                    allow_custom=True,
                )
            ]
        },
        "file": {
            "file:parent_directory_str MATCHES '/tmpomWnSX/package/doc/api' AND file:name MATCHES 'rpc-socket.md'": [
                File(
                    id="file--18288093-6465-11eb-adcb-ef638f602075",
                    name="rpc-socket.md",
                    full_output='Mon Feb  1 08:11:06 2021.507489 |npm@7f526098adae[17717] openat(AT_FDCWD, "/tmpomWnSX/package/doc/api/rpc-socket.md", O_RDONLY|O_CLOEXEC) = 10',
                    parent_directory_str="/tmpomWnSX/package/doc/api",
                    timestamp="Mon Feb  1 08:11:06 2021",
                    allow_custom=True,
                )
            ],
            "file:parent_directory_str MATCHES '/tmpTuVDQZ' AND file:name MATCHES 'shallow'": [
                File(
                    name="shallow",
                    full_output='Tue Feb  2 09:33:32 2021.007100 |git-upload-pack@7f59d6a4cc8e[17746] openat(AT_FDCWD, "shallow", O_RDONLY) = -2 (ENOENT)',
                    timestamp="Tue Feb  2 09:33:32 2021",
                    container_id="",
                    id="file--c67bcea7-6539-11eb-8fc6-edd1fd8b9760",
                    parent_directory_str="/tmpTuVDQZ",
                    allow_custom=True,
                )
            ],
        },
        "process": {
            "process:command_line MATCHES '/usr/lib/git-core/git index-pack --stdin --fix-thin --keep=fetch-pack 17724 on buildwatch --check-self-contained-and-connected'": [
                Process(
                    id="process--18b252f2-6465-11eb-adcb-ef638f602075",
                    full_output='Mon Feb  1 08:11:07 2021.977686 |git@7fb2ac106cdd[17728] execve("/usr/lib/git-core/git", ["/usr/lib/git-core/git", "index-pack", "--stdin", "--fix-thin", "--keep=fetch-pack 17724 on buildwatch", "--check-self-contained-and-connected"], ["GIT_ASKPASS=echo", "GIT_DIR=/root/.npm/_git-remotes/git-github-com-eriksank-EventEmitter4-git-c533a4e5", "HOME=/root", "JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64", "LANG=en_US", "LANGUAGE=en_US:", "LOGNAME=root", "MAIL=/var/mail/root", "PATH=/usr/lib/git-core:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin", ")',
                    timestamp="Mon Feb  1 08:11:07 2021",
                    container_id="",
                    command_line="/usr/lib/git-core/git index-pack --stdin --fix-thin --keep=fetch-pack 17724 on buildwatch --check-self-contained-and-connected",
                    executable_path="/usr/lib/git-core/git",
                    allow_custom=True,
                )
            ],
            "process:command_line MATCHES 'sh -c /tmph5wu7q/.buildwatch.sh'": [
                Process(
                    full_output='Mon Feb  1 16:55:37 2021.369439 |python2.7@7f1e4be30e37[17699] execve("/usr/bin/sh", ["sh", "-c", "/tmph5wu7q/.buildwatch.sh"], ["LANGUAGE=en_US:", "HOME=/root", "LOGNAME=root", "PATH=/usr/bin:/bin", "LANG=en_US", "SHELL=/bin/sh", "JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64", "PWD=/root"]) = -2 (ENOENT)',
                    timestamp="Mon Feb  1 16:55:37 2021",
                    container_id="",
                    command_line="sh -c /tmph5wu7q/.buildwatch.sh",
                    id="process--6dc9ba7e-64ae-11eb-9377-ffdad63e1e3e",
                    type="process",
                    executable_path="/usr/bin/sh",
                    allow_custom=True,
                )
            ],
        },
    }

    file_object = find_stix_objects(
        stix_objects,
        "file:parent_directory_str MATCHES '/tmpomWnSX/package/doc/api' AND file:name MATCHES 'rpc\\-socket\\.md'",
    )
    second_file_object = find_stix_objects(
        stix_objects,
        "file:parent_directory_str MATCHES '/tmp[0-9a-zA-Z_]+' AND file:name MATCHES 'shallow'",
    )
    process_object = find_stix_objects(
        stix_objects,
        "process:command_line MATCHES '/usr/lib/git\\-core/git\\ index\\-pack\\ \\-\\-stdin\\ \\-\\-fix\\-thin\\ \\-\\-keep=fetch\\-pack\\ 177[\\d]+\\ on\\ buildwatch\\ \\-\\-check\\-self\\-contained\\-and\\-connected'",
    )
    second_process_object = find_stix_objects(
        stix_objects,
        "process:command_line MATCHES '[a-z\\-\\ ]+\\ /tmp[0-9a-zA-Z]+/\\.buildwatch\\.sh'",
    )
    domain_object = find_stix_objects(
        stix_objects,
        "domain-name:value = 'localhost' OR domain-name:resolves_to_str = '127\\.0\\.0\\.53'",
    )

    assert file_object[0].type == "file"
    assert second_file_object[0].type == "file"
    assert process_object[0].type == "process"
    assert second_process_object[0].type == "process"
    assert domain_object[0].type == "domain-name"


def test_find_objects_matching_patterns():
    stix_objects = {
        "domain-name": {
            "domain-name:value = 'localhost' OR domain-name:resolves_to_str = '127.0.0.53'": [
                DomainName(
                    resolves_to_refs=["ipv6-addr--09dc677d-648e-11eb-adcb-ef638f602075"],
                    full_output="Mon Feb  1 13:04:10 2021.045493 |git@7fb679d9c741[17730] connect(3, {AF_INET, 127.0.0.53, 53}, 16) = 0",
                    timestamp="Mon Feb  1 13:04:10 2021",
                    container_id="",
                    value="localhost",
                    resolves_to_str="127.0.0.53",
                    id="domain-name--09dc677c-648e-11eb-adcb-ef638f602075",
                    allow_custom=True,
                )
            ]
        },
        "file": {
            "file:parent_directory_str MATCHES '/tmpomWnSX/package/doc/api' AND file:name MATCHES 'rpc-socket.md'": [
                File(
                    id="file--18288093-6465-11eb-adcb-ef638f602075",
                    name="rpc-socket.md",
                    full_output='Mon Feb  1 08:11:06 2021.507489 |npm@7f526098adae[17717] openat(AT_FDCWD, "/tmpomWnSX/package/doc/api/rpc-socket.md", O_RDONLY|O_CLOEXEC) = 10',
                    parent_directory_str="/tmpomWnSX/package/doc/api",
                    timestamp="Mon Feb  1 08:11:06 2021",
                    allow_custom=True,
                )
            ]
        },
        "process": {
            "process:command_line MATCHES '/usr/lib/git-core/git index-pack --stdin --fix-thin --keep=fetch-pack 17724 on buildwatch --check-self-contained-and-connected'": [
                Process(
                    id="process--18b252f2-6465-11eb-adcb-ef638f602075",
                    full_output='Mon Feb  1 08:11:07 2021.977686 |git@7fb2ac106cdd[17728] execve("/usr/lib/git-core/git", ["/usr/lib/git-core/git", "index-pack", "--stdin", "--fix-thin", "--keep=fetch-pack 17724 on buildwatch", "--check-self-contained-and-connected"], ["GIT_ASKPASS=echo", "GIT_DIR=/root/.npm/_git-remotes/git-github-com-eriksank-EventEmitter4-git-c533a4e5", "HOME=/root", "JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64", "LANG=en_US", "LANGUAGE=en_US:", "LOGNAME=root", "MAIL=/var/mail/root", "PATH=/usr/lib/git-core:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin", ")',
                    timestamp="Mon Feb  1 08:11:07 2021",
                    container_id="",
                    command_line="/usr/lib/git-core/git index-pack --stdin --fix-thin --keep=fetch-pack 17724 on buildwatch --check-self-contained-and-connected",
                    executable_path="/usr/lib/git-core/git",
                    allow_custom=True,
                )
            ],
            "process:command_line MATCHES 'sh -c /tmph5wu7q/.buildwatch.sh'": [
                Process(
                    full_output='Mon Feb  1 16:55:37 2021.369439 |python2.7@7f1e4be30e37[17699] execve("/usr/bin/sh", ["sh", "-c", "/tmph5wu7q/.buildwatch.sh"], ["LANGUAGE=en_US:", "HOME=/root", "LOGNAME=root", "PATH=/usr/bin:/bin", "LANG=en_US", "SHELL=/bin/sh", "JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64", "PWD=/root"]) = -2 (ENOENT)',
                    timestamp="Mon Feb  1 16:55:37 2021",
                    container_id="",
                    command_line="sh -c /tmph5wu7q/.buildwatch.sh",
                    id="process--6dc9ba7e-64ae-11eb-9377-ffdad63e1e3e",
                    type="process",
                    executable_path="/usr/bin/sh",
                    allow_custom=True,
                )
            ],
        },
    }

    patterns = stix2.parse(
        json.load(Path(__file__).with_name("test_patterns.json").open("r")), allow_custom=True
    )
    objects = find_objects_matching_patterns(stix_objects, patterns)

    assert len(objects) == 2
    for obj in objects:
        assert obj.type == "process"


def test_delete_objects():
    objects_to_delete = [
        File(
            id="file--38288093-6465-11eb-adcb-ef638f602075",
            name="rpc-socket.md",
            full_output='Mon Feb  1 08:11:06 2021.507489 |npm@7f526098adae[17717] openat(AT_FDCWD, "/tmpomWnSX/package/doc/api/rpc-socket.md", O_RDONLY|O_CLOEXEC) = 10',
            parent_directory_str="/tmpomWnSX/package/doc/api",
            timestamp="Mon Feb  1 08:11:06 2021",
            allow_custom=True,
        ),
        File(
            id="file--28288093-6465-11eb-adcb-ef638f602075",
            name="rpc-server.md",
            full_output='Mon Feb  1 08:11:06 2021.507489 |npm@7f526098adae[17717] openat(AT_FDCWD, "/tmpomWnSX/package/doc/api/rpc-socket.md", O_RDONLY|O_CLOEXEC) = 10',
            parent_directory_str="/tmpomWnSX/package/doc/api",
            timestamp="Mon Feb  1 08:11:06 2021",
            allow_custom=True,
        ),
    ]
    stix_objects = [
        File(
            name="tmpomWnSX",
            id="file--c6cd740e-6539-11eb-8fc6-edd1fd8b9760",
            container_id="",
            parent_directory_str="/",
            timestamp="Tue Feb  2 09:32:23 2021",
            full_output='Tue Feb  2 09:32:23 2021.248256 |npm@7f0c81d13bb7[17718] mkdir("/tmpomWnSX", 0755) = -17 (EEXIST)',
            allow_custom=True,
        ),
        File(
            id="file--38288093-6465-11eb-adcb-ef638f602075",
            name="rpc-socket.md",
            full_output='Mon Feb  1 08:11:06 2021.507489 |npm@7f526098adae[17717] openat(AT_FDCWD, "/tmpomWnSX/package/doc/api/rpc-socket.md", O_RDONLY|O_CLOEXEC) = 10',
            parent_directory_str="/tmpomWnSX/package/doc/api",
            timestamp="Mon Feb  1 08:11:06 2021",
            allow_custom=True,
        ),
        File(
            id="file--22288093-6465-11eb-adcb-ef638f602075",
            name="package",
            full_output='Mon Feb  1 08:11:06 2021.507489 |npm@7f526098adae[17717] openat(AT_FDCWD, "/tmpomWnSX/package/doc/api/rpc-socket.md", O_RDONLY|O_CLOEXEC) = 10',
            parent_directory_str="/tmpomWnSX",
            timestamp="Mon Feb  1 08:11:06 2021",
            allow_custom=True,
        ),
        File(
            id="file--18288093-6465-11eb-adcb-ef638f602075",
            name="doc",
            full_output='Mon Feb  1 08:11:06 2021.507489 |npm@7f526098adae[17717] openat(AT_FDCWD, "/tmpomWnSX/package/doc/api/rpc-socket.md", O_RDONLY|O_CLOEXEC) = 10',
            parent_directory_str="/tmpomWnSX/package",
            timestamp="Mon Feb  1 08:11:06 2021",
            allow_custom=True,
        ),
        File(
            id="file--48288093-6465-11eb-adcb-ef638f602075",
            name="api",
            full_output='Mon Feb  1 08:11:06 2021.507489 |npm@7f526098adae[17717] openat(AT_FDCWD, "/tmpomWnSX/package/doc/api/rpc-socket.md", O_RDONLY|O_CLOEXEC) = 10',
            parent_directory_str="/tmpomWnSX/package/doc",
            timestamp="Mon Feb  1 08:11:06 2021",
            allow_custom=True,
        ),
        File(
            id="file--48288093-6465-11eb-adcb-ef638f602075",
            name="api",
            full_output='Mon Feb  1 08:11:06 2021.507489 |npm@7f526098adae[17717] openat(AT_FDCWD, "/tmpomWnSX/package/doc/api/rpc-socket.md", O_RDONLY|O_CLOEXEC) = 10',
            parent_directory_str="/tmpomWnSX/package/doc",
            timestamp="Mon Feb  1 08:11:06 2021",
            allow_custom=True,
        ),
        File(
            id="file--28288093-6465-11eb-adcb-ef638f602075",
            name="rpc-server.md",
            full_output='Mon Feb  1 08:11:06 2021.507489 |npm@7f526098adae[17717] openat(AT_FDCWD, "/tmpomWnSX/package/doc/api/rpc-socket.md", O_RDONLY|O_CLOEXEC) = 10',
            parent_directory_str="/tmpomWnSX/package/doc/api",
            timestamp="Mon Feb  1 08:11:06 2021",
            allow_custom=True,
        ),
        File(
            id="file--18288093-6465-11eb-adcb-ef638f602075",
            name="doc",
            full_output='Mon Feb  1 08:11:06 2021.507489 |npm@7f526098adae[17717] openat(AT_FDCWD, "/tmpomWnSX/package/doc/api/rpc-socket.md", O_RDONLY|O_CLOEXEC) = 10',
            parent_directory_str="/tmpomWnSX/package",
            timestamp="Mon Feb  1 08:11:06 2021",
            allow_custom=True,
        ),
    ]
    bundle = Bundle(objects=stix_objects, allow_custom=True)
    remaining_objects = delete_objects(objects_to_delete, bundle)
    assert not remaining_objects


def test_sth():
    file = (
        Path(__file__).parent.parent.parent.with_name("patternson_runner")
        / "obspat"
        / "patterns.json"
    )
    patterns = stix2.parse(json.load(file.open("r")), allow_custom=True)
    for p in patterns.objects:
        print(p.pattern)

    raise ValueError

    stix_objects = {"file": {}}
    assert find_objects_matching_patterns(stix_objects, patterns)
