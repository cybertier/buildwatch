# Patternson

Creating (Inter) Observable Patterns

### Setup
 * `virtualenv -p python3.6 venv`
 * `. venv/bin/activate`
 * `pip install -r requirements.txt`
 * `git submodule sync --recursive`
 * `git submodule update --init --recursive`
 * `cp conf.yml.dist conf.yml` and change to suit your needs
 
### Usage
```
Usage: patternson.py [OPTIONS]

Options:
  -i, --input TEXT         Specify the input directory. This program expects a
                           structure like "input_dir/specimen_dir/runtime_inst
                           ances_dir/stix2.json".  [required]
  -o, --output TEXT        Specify the output directory [will be created, if
                           it does not exist already]. For each specimen, one
                           file will be generated (if possible).  [required]
  -p, --processes INTEGER  Specify how many cores should be used. Only useful
                           if multiple samples are present. Default=8 [your
                           cpu count]
  --timeout INTEGER        Set a timeout [in seconds] after a process is being
                           stopped. No pattern will be generated for the
                           processed specimen. Default=360
  -v, --verbose
  --help                   Show this message and exit.
```