import json
import logging
import os
import click
import sys
from logging import FileHandler
from pathlib import Path
from typing import List, Dict, Tuple
from .pattern_generation.helper_functions import conf
from .pattern_generation.process_reports import pattern_generation

# setup logging
fh = logging.handlers.RotatingFileHandler(conf.log_file, maxBytes=conf.max_log_size)
fh.setLevel(conf.log_level_logfile)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(conf.log_level_stdout)
fh.setFormatter(logging.Formatter(conf.log_format))
ch.setFormatter(logging.Formatter(conf.log_format))
log = logging.getLogger()
log.setLevel(conf.log_level_stdout)
log.addHandler(fh)
log.addHandler(ch)


@click.command()
@click.option(
    "-i",
    "--input",
    "input_dir",
    required=True,
    help="Specify the input directory.",
)
@click.option(
    "-o",
    "--output",
    "output_dir",
    required=True,
    help="Specify the output "
    "directory [will be created, if it does not exist already]. "
    "For each specimen, one file will be generated (if possible).",
)
@click.option("-v", "--verbose", is_flag=True)
def main(input_dir, output_dir, verbose):
    reports = os.listdir(input_dir)
    total_reports = len(reports)
    if verbose:
       ch.setLevel(10)
       log.setLevel(10)
       log.addHandler(ch)
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    output_file = output_dir / f"patterns.json"
    process_reports(input_dir, output_file, total_reports)


def start_patternson(input_dir, output_dir, run_id, verbose=True):
    reports = os.listdir(input_dir)
    total_reports = len(reports)
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

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    output_file = output_dir / f"patterns.json"
    process_reports(input_dir, output_file, total_reports)


def process_reports(input_dir, output_file, total_reports=None):
    log.info(f"Processing {total_reports} files : {os.listdir(input_dir)}")
    objects_per_type, objects_per_run = load_input(input_dir)
    pattern_generation(objects_per_type, objects_per_run, output_file)


def load_input(input_dir) -> Tuple[Dict[str, List], Dict[int, Dict[str, List]]]:
    objects_per_type = {
        "files_written": [],
        "files_read": [],
        "files_removed": [],
        "processes_created": [],
        "domains_connected": [],
    }
    objects_per_run = {}
    run_counter = 1
    for runtime in Path(input_dir).glob("*_cleaned.json"):
        data = json.load(runtime.open())

        objects_per_run.update({run_counter: data})
        objects_per_type["files_written"].extend(data["files_written"])
        objects_per_type["files_read"].extend(data["files_read"])
        objects_per_type["files_removed"].extend(data["files_removed"])
        objects_per_type["processes_created"].extend(data["processes_created"])
        objects_per_type["domains_connected"].extend(data["domains_connected"])
        run_counter += 1
    return objects_per_type, objects_per_run


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
