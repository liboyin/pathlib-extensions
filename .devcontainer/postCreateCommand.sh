#! /bin/bash
pip3 --disable-pip-version-check --no-cache-dir install -e .[dev]
pip3 freeze | grep -v pathlib-extensions > requirements.dev.txt
