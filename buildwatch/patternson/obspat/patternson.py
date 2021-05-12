import json
import logging
import click
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from .pattern_generation.helper_functions import conf
from .pattern_generation.process_reports import pattern_generation

# setup logging
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(conf.log_level_stdout)
ch.setFormatter(logging.Formatter(conf.log_format))
log = logging.getLogger()
log.setLevel(conf.log_level_stdout)
log.addHandler(ch)


@click.command()
@click.option(
    '-i',
    '--input',
    'input_dir',
    required=True,
    help='Specify the input directory.',
)
@click.option(
    '-o',
    '--output',
    'output_dir',
    required=True,
    help='Specify the output '
    'directory [will be created, if it does not exist already]. '
    'For each specimen, one file will be generated (if possible).',
)
@click.option('-v', '--verbose', is_flag=True)
def main(input_dir, output_dir, verbose):
    if verbose:
        ch.setLevel(10)
        log.setLevel(10)
        log.addHandler(ch)
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    output_file = output_dir / 'patterns.json'
    log.info('working on reports in %s', input_dir)
    files = [str(_) for _ in Path(input_dir).glob('*_cleaned.json')]
    log.debug('found these files: %s', files)
    process_reports(input_dir, output_file, None)


def start_patternson(input_dir, output_dir, run_id, old_patterns_file, verbose=True):
    if verbose:
        log.setLevel(10)

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    output_file = output_dir / 'patterns.json'
    process_reports(input_dir, output_file, old_patterns_file)


def process_reports(input_dir, output_file, old_patterns_file):
    objects_per_type, objects_per_run = load_input(input_dir)
    pattern_generation(objects_per_type, objects_per_run, output_file, old_patterns_file)


def load_input(
        input_dir) -> Tuple[Dict[str, List], Dict[int, Dict[str, List]]]:
    objects_per_type = {
        'files_written': [],
        'files_read': [],
        'files_removed': [],
        'processes_created': [],
        'domains_connected': [],
    }
    objects_per_run = {}
    run_counter = 1
    for runtime in Path(input_dir).glob('*_cleaned.json'):
        data = json.load(runtime.open())

        objects_per_run.update({run_counter: data})
        objects_per_type['files_written'].extend(data['files_written'])
        objects_per_type['files_read'].extend(data['files_read'])
        objects_per_type['files_removed'].extend(data['files_removed'])
        objects_per_type['processes_created'].extend(data['processes_created'])
        objects_per_type['domains_connected'].extend(data['domains_connected'])
        run_counter += 1
    return objects_per_type, objects_per_run


if __name__ == '__main__':
    main()  # pylint: disable=no-value-for-parameter
