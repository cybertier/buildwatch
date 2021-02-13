import json
import logging
import os
from datetime import datetime
from logging import FileHandler
from multiprocessing import Value, cpu_count
from pathlib import Path
from typing import List, Dict, Any

import click
import stix2

from .pattern_generation.process_reports import pattern_generation

# setup logging
#fh = logging.handlers.RotatingFileHandler(conf.log_file, maxBytes=conf.max_log_size)
#fh.setLevel(conf.log_level_logfile)
#ch = logging.StreamHandler(sys.stdout)
#ch.setLevel(conf.log_level_stdout)
#fh.setFormatter(logging.Formatter(conf.log_format))
#ch.setFormatter(logging.Formatter(conf.log_format))
log = logging.getLogger()
#log.setLevel(conf.log_level_stdout)
#log.addHandler(fh)
#log.addHandler(ch)


@click.command()
@click.option(
    "-i",
    "--input",
    "input_",
    required=True,
    help="Specify the input"
    " directory. This program expects a structure like "
    '"input_dir/specimen_dir/runtime_instances_dir/stix2.json".',
)
@click.option(
    "-o",
    "--output",
    required=True,
    help="Specify the output "
    "directory [will be created, if it does not exist already]. "
    "For each specimen, one file will be generated (if possible).",
)
@click.option(
    "-p",
    "--processes",
    default=cpu_count(),
    help="Specify how "
    "many cores should be used. Only useful if multiple samples are "
    f"present. Default={cpu_count()} [your cpu count]",
)
@click.option(
    "--timeout",
    default=6000,
    help="Set a timeout [in seconds] after "
    "a process is being stopped. No pattern will be generated for "
    "the processed specimen. Default=360",
)
@click.option("-v", "--verbose", is_flag=True)
def main(input_, output, processes, timeout, verbose):
    global counter  # pylint: disable=global-variable-undefined
    reports = os.listdir(input_)
    total_reports = len(reports)
    counter = Value("i", 1)
    options = {"input": input_, "output": output}
    #if verbose:
    #    ch.setLevel(10)
    #    log.setLevel(10)
    #    log.addHandler(ch)
    output_dir = Path(options["output"])
    output_dir.mkdir(exist_ok=True, parents=True)
    output_file = output_dir / f"patterns.json"
    process_reports(output_file, options, total_reports)

    #with ProcessPool(max_workers=processes, max_tasks=1) as pool:
    #    for directory in reports:
    #        pool.schedule(
    #            process_reports,
    #            args=[directory, options, total_reports],
    #            timeout=timeout,
    #        )


def start_patternson(input_, output, run_id, verbose=True):
    global counter  # pylint: disable=global-variable-undefined
    reports = os.listdir(input_)
    total_reports = len(reports)
    counter = Value("i", 1)
    options = {"input": input_, "output": output}
    if verbose:
        log.setLevel(10)
        file_path = Path(__file__).parent.parent.with_name("storage") / "run" / f"{run_id}" / "patternson.log"
        handler = FileHandler(file_path)
        handler.setLevel("DEBUG")
        log.addHandler(handler)

    output_dir = Path(options["output"])
    output_dir.mkdir(exist_ok=True, parents=True)
    output_file = output_dir / f"patterns.json"
    process_reports(options, output_file, total_reports)


def process_reports(options, output_file, total_reports=None):
    log.info(f"Processing {total_reports} files : {os.listdir(options['input'])}")
    accumulated_reports = load_stix_reports(options)
    if accumulated_reports:
        accumulated_objects = get_accumulated_objects(accumulated_reports)
        pattern_generation(accumulated_objects, accumulated_reports, output_file)
    else:
        log.warning(f"Could not gather any objects from reports.")


def load_stix_reports(options) -> List[List[stix2.ObservedData]]:
    accumulated_objects = []
    dir = Path(options["input"])
    for runtime in dir.glob("stix_*"):
        try:
            stix_obj = load_stix_obj_from_file(runtime)
        except Exception as e:
            log.debug(f"Could not load file {runtime}. {e}")
            continue

        observed_data_objects = extract_data_from_stix_object(stix_obj)
        if not observed_data_objects:
            log.warning(f"No usable objects found in file {runtime}")
            continue
        accumulated_objects.append(observed_data_objects)
    return accumulated_objects


def load_stix_obj_from_file(file: Path):
    data = json.load(file.open())
    stix_obj = stix2.parse(data, allow_custom=True)
    return stix_obj


def extract_data_from_stix_object(stix_object) -> List[stix2.ObservedData]:
    observed_data_objects = []
    if stix_object.type == "bundle":
        observed_data_objects.extend(extract_data_from_stix_bundle(stix_object))
    elif stix_object.type == "observed-data":
        observed_data_objects.append(stix_object)
    return observed_data_objects


def extract_data_from_stix_bundle(
    stix_bundle: stix2.Bundle,
) -> List[stix2.ObservedData]:
    observed_data_objects = []
    for obj in stix_bundle.objects:
        if obj["type"] == "observed-data":
            observed_data_objects.append(obj)
        if obj["type"] != "malware-analysis" and obj["type"] != "grouping":
            timestamp = datetime.strptime(obj["timestamp"], "%a %b %d %H:%M:%S %Y")
            observed_data_objects.append(
                stix2.ObservedData(
                    first_observed=timestamp,
                    last_observed=timestamp,
                    number_observed=1,
                    objects={"0": obj},
                    allow_custom=True,
                )
            )
    return observed_data_objects


def get_accumulated_objects(accumulated_reports: List[List[stix2.ObservedData]]):
    accumulated_objects = {}
    for report_index, report in enumerate(accumulated_reports):
        for observed_data_object in report:
            obj_type = observed_data_object.objects["0"].type
            # global accumulated
            accumulated_objects = accumulate_objects_globally(accumulated_objects, observed_data_object, obj_type)
            # per report accumulated
            accumulated_objects = accumulate_objects_per_report(accumulated_objects, observed_data_object, obj_type,
                                                                report_index)
    return accumulated_objects


def accumulate_objects_per_report(accumulated_objects, observed_data_object, obj_type, report_index) -> Dict[str, List[Dict[str, Any]]]:
    objects_per_report = accumulated_objects.get(report_index, {})
    objects = objects_per_report.get(obj_type, [])
    if observed_data_object.objects not in objects:
        objects.append(observed_data_object.objects)
    objects_per_report[obj_type] = objects
    accumulated_objects[report_index] = objects_per_report
    return accumulated_objects


def accumulate_objects_globally(accumulated_objects, observed_data_object, obj_type) -> Dict[str, List[Dict[str, Any]]]:
    objects = accumulated_objects.get(obj_type, [])
    if observed_data_object.objects not in objects:
        objects.append(observed_data_object.objects)
    accumulated_objects[obj_type] = objects
    return accumulated_objects


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
