#!/bin/bash

cd /benchmarks
make deps
make docker-build-binaries-gem5

git clone https://github.com/adutilleul/gem5-exps
python standalone/generate-gem5-reports.py /benchmarks/__build__ /benchmarks/gem5-exps /benchmarks/gem5-reports /gem5/gem5 $1