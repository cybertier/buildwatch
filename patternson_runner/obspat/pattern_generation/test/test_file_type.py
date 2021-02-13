from stix2 import File

from ..file_type import build_tree


def test_build_tree():
    files = [
        {
            "0": File(
                type="file",
                spec_version="2.1",
                name="file-name1",
                id="file--9e9a6d0e-653a-11eb-8fc6-edd1fd8b9760",
                full_output="full-output",
                parent_directory_str="/etc",
                timestamp="2020-02-13T10:20:12",
                allow_custom=True,
            )
        },
        {
            "0": File(
                type="file",
                spec_version="2.1",
                name="file-name2",
                id="file--9e9a6d0e-653a-11eb-8fc6-edd1fd8b9760",
                full_output="full-output",
                parent_directory_str="/etc",
                timestamp="2020-02-13T10:20:12",
                allow_custom=True,
            )
        },
        {
            "0": File(
                type="file",
                spec_version="2.1",
                name="file-name1",
                id="file--9e9a6d0e-653a-11eb-8fc6-edd1fd8b9760",
                full_output="full-output",
                parent_directory_str="/etc2",
                timestamp="2020-02-13T10:20:12",
                allow_custom=True,
            )
        },
        {
            "0": File(
                type="file",
                spec_version="2.1",
                name="file-name2",
                id="file--9e9a6d0e-653a-11eb-8fc6-edd1fd8b9760",
                full_output="full-output",
                parent_directory_str="/etc2",
                timestamp="2020-02-13T10:20:12",
                allow_custom=True,
            )
        },
    ]
    tree = build_tree(files, [])
    assert tree == {
        "": {
            "etc": {"file-name1": {}, "file-name2": {}},
            "etc2": {"file-name1": {}, "file-name2": {}},
        }
    }
