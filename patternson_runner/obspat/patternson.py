import json
import logging
import os
from logging import FileHandler
from multiprocessing import Value, cpu_count
from pathlib import Path
from typing import List, Dict, Tuple

import click
import stix2

from .pattern_generation.helper_functions import FileData, ProcessData, DomainData
from .pattern_generation.process_reports import pattern_generation

# setup logging
# fh = logging.handlers.RotatingFileHandler(conf.log_file, maxBytes=conf.max_log_size)
# fh.setLevel(conf.log_level_logfile)
# ch = logging.StreamHandler(sys.stdout)
# ch.setLevel(conf.log_level_stdout)
# fh.setFormatter(logging.Formatter(conf.log_format))
# ch.setFormatter(logging.Formatter(conf.log_format))
log = logging.getLogger()
# log.setLevel(conf.log_level_stdout)
# log.addHandler(fh)
# log.addHandler(ch)


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
    # if verbose:
    #    ch.setLevel(10)
    #    log.setLevel(10)
    #    log.addHandler(ch)
    output_dir = Path(options["output"])
    output_dir.mkdir(exist_ok=True, parents=True)
    output_file = output_dir / f"patterns.json"

    start = datetime.now()
    process_reports(options, output_file, total_reports)
    end = datetime.now()
    print(f"Time taken: {end-start}")

    # with ProcessPool(max_workers=processes, max_tasks=1) as pool:
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
        file_path = (
            Path(__file__).parent.parent.with_name("storage")
            / "run"
            / f"{run_id}"
            / "patternson.log"
        )
        handler = FileHandler(file_path)
        handler.setLevel("DEBUG")
        log.addHandler(handler)

    output_dir = Path(options["output"])
    output_dir.mkdir(exist_ok=True, parents=True)
    output_file = output_dir / f"patterns.json"
    process_reports(options, output_file, total_reports)


def process_reports(options, output_file, total_reports=None):
    log.info(f"Processing {total_reports} files : {os.listdir(options['input'])}")
    objects_per_type, objects_per_run = load_stix_reports(options)
    pattern_generation(objects_per_type, objects_per_run, output_file)


def load_stix_reports(options) -> Tuple[Dict[str, List], Dict[int, Dict[str, List]]]:
    objects_per_type = {"file": [], "process": [], "domain-name": []}
    objects_per_run = {}
    run_counter = 1
    for runtime in Path(options["input"]).glob("stix_*"):
        stix_obj = load_stix_obj_from_file(runtime)
        observed_data_objects = extract_data_from_stix_bundle(stix_obj)
        objects_per_run.update({run_counter: observed_data_objects})
        objects_per_type["file"].extend(observed_data_objects["file"])
        objects_per_type["process"].extend(observed_data_objects["process"])
        objects_per_type["domain-name"].extend(observed_data_objects["domain-name"])
        run_counter += 1
    return objects_per_type, objects_per_run


def load_stix_obj_from_file(file: Path):
    data = json.load(file.open())
    stix_obj = stix2.parse(data, allow_custom=True)
    return stix_obj


def extract_data_from_stix_bundle(
    stix_bundle: stix2.Bundle,
) -> Dict[str, List]:
    observed_data_objects: Dict[str, List] = {"file": [], "process": [], "domain-name": []}
    for obj in stix_bundle.objects:
        _type = obj["type"]
        if _type != "malware-analysis" and _type != "grouping":
            if _type == "file":
                new_file = FileData(obj["parent_directory_str"], obj["name"])
                if new_file not in observed_data_objects["file"]:
                    observed_data_objects["file"].append(new_file)
            if _type == "process":
                new_process = ProcessData(obj["executable_path"], obj["command_line"])
                if new_process not in observed_data_objects["process"]:
                    observed_data_objects["process"].append(new_process)
            if _type == "domain-name":
                new_domain = DomainData(obj["value"], obj["resolves_to_str"])
                if new_domain not in observed_data_objects["domain-name"]:
                    observed_data_objects["domain-name"].append(new_domain)
    return observed_data_objects


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
