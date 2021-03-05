from ...patternson import get_accumulated_objects
from stix2 import ObservedData, File
from datetime import datetime


def test_get_accumulated_objects():
    timestamp = datetime(2020, 2, 2, 14, 13, 23)
    accumulated_reports = [
        [
            ObservedData(
                first_observed=timestamp,
                last_observed=timestamp,
                number_observed=1,
                objects={
                    "0": File(
                        type="file",
                        spec_version="2.1",
                        name="file-name1",
                        id="file--109a6d0e-653a-11eb-8fc6-edd1fd8b9760",
                        full_output="full-output",
                        parent_directory_str="/root",
                        timestamp="2020-02-13T10:20:12",
                        allow_custom=True,
                    )
                },
                allow_custom=True,
            )
        ],
        [
            ObservedData(
                first_observed=timestamp,
                last_observed=timestamp,
                number_observed=1,
                objects={
                    "0": File(
                        type="file",
                        spec_version="2.1",
                        name="not-a-name",
                        id="file--209a6d0e-653a-11eb-8fc6-edd1fd8b9760",
                        full_output="full-output",
                        parent_directory_str="/etc",
                        timestamp="2020-02-13T10:20:12",
                        allow_custom=True,
                    )
                },
                allow_custom=True,
            )
        ],
        [
            ObservedData(
                first_observed=timestamp,
                last_observed=timestamp,
                number_observed=1,
                objects={
                    "0": File(
                        type="file",
                        spec_version="2.1",
                        name="no-name-either",
                        id="file--309a6d0e-653a-11eb-8fc6-edd1fd8b9760",
                        full_output="full-output",
                        parent_directory_str="/etc",
                        timestamp="2020-02-13T10:20:12",
                        allow_custom=True,
                    )
                },
                allow_custom=True,
            ),
            ObservedData(
                first_observed=timestamp,
                last_observed=timestamp,
                number_observed=1,
                objects={
                    "0": File(
                        type="file",
                        spec_version="2.1",
                        name="some-other-name",
                        id="file--319a6d0e-653a-11eb-8fc6-edd1fd8b9760",
                        full_output="full-output",
                        parent_directory_str="/usr",
                        timestamp="2020-02-13T10:20:12",
                        allow_custom=True,
                    )
                },
                allow_custom=True,
            ),
        ],
    ]
    accumulated_objects = get_accumulated_objects(accumulated_reports)
    assert list(accumulated_objects.keys()) == ["file", 0, 1, 2]
    assert len(accumulated_objects["file"]) == 4
    assert len(accumulated_objects[0]["file"]) == 1
    assert len(accumulated_objects[1]["file"]) == 1
    assert len(accumulated_objects[2]["file"]) == 2
