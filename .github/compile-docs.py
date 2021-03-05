#!/usr/bin/env python3
import errno
import os
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

env = Environment(
    loader=FileSystemLoader('../templates'),
    autoescape=select_autoescape(['html', 'xml'])
)
template = env.get_template('docs.html')
result = template.render()
if not os.path.exists("./out"):
    os.makedirs("./out")

with Path("./out/index.html").open("w") as file:
    file.write(result)
try:
    shutil.copytree("../static", "./out/static")
except OSError as exc:  # python >2.5
    if exc.errno == errno.ENOTDIR:
        shutil.copy("../static", "./out/static")
    else:
        raise
