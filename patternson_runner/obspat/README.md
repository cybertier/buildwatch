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
  -i, --input TEXT         Specify the input directory  [required]
  -o, --output TEXT        Specify the output directory, which will be created, if
                           it does not exist already  [required]
  -v, --verbose
  --help                   Show this message and exit.
```