#!/bin/sh

# ./shifumi.py --include polybench/utilities/ --sources-conf='config/benchmarks.list' --versions-conf='config/versions.list' --compilers-conf=config/cc.list --always-link-with 'polybench/utilities/polybench_stub.c' --build-directory=/home/hpompougnac/Documents/alp_data/build --fuzz-directory=/home/hpompougnac/Documents/alp_data/build/fuzz --reports-directory=/home/hpompougnac/Documents/alp_data/reports --use-cache --csv-output /home/hpompougnac/Documents/alp_data/just_tam_report.csv --verbose-output --debug

./shifumi.py --include polybench/utilities/ --sources-conf='config/benchmarks.list' --versions-conf='config/versions-ellana.list' --compilers-conf=config/cc.list --always-link-with 'polybench/utilities/polybench_stub.c' --build-directory=__build__ --fuzz-directory=__fuzz__ --reports-directory=__reports__ --use-cache --disable-tam --verbose-output --debug

# Look for odd bottlenecks in the wole experiments space

# Sensitivity
# ./shifumi.py --include polybench/utilities/ --sources-conf='config/benchmarks.list' --versions-conf='config/versions.list' --compilers-conf=config/cc_gus.list --always-link-with 'polybench/utilities/polybench_stub.c' --build-directory=/home/hpompougnac/Documents/alp_data/build --fuzz-directory=/home/hpompougnac/Documents/alp_data/fuzz --reports-directory=/home/hpompougnac/Documents/alp_data/reports --use-cache --csv-output /home/hpompougnac/Documents/alp_data/just_sens_report.csv --verbose-output --reuse-perf-reports --disable-tam --enable-sensitivity --verbose-output --debug --fool-gus

# TAM
# ./shifumi.py --include polybench/utilities/ --sources-conf='config/benchmarks.list' --versions-conf='config/versions.list' --compilers-conf=config/cc.list --always-link-with 'polybench/utilities/polybench_stub.c' --tma-scope-install-dir ~/src/projects/tma-scope/ --perf-core 1 --use-huge-pages --build-directory=/home/hpompougnac/Documents/alp_data/build --fuzz-directory=/home/hpompougnac/Documents/alp_data/fuzz --reports-directory=/home/hpompougnac/Documents/alp_data/reports --use-cache --csv-output /home/hpompougnac/Documents/alp_data/just_tam_report.csv --verbose-output --reuse-perf-reports --fool-tam

# ./shifumi.py --include polybench/utilities/ --sources-conf='config/benchmarks.list' --versions-conf='config/versions.list' --compilers-conf=config/cc.list --always-link-with 'polybench/utilities/polybench_stub.c' --tma-scope-install-dir ~/src/projects/tma-scope/ --perf-core 1 --use-huge-pages --build-directory=/home/hpompougnac/Documents/alp_data/build --fuzz-directory=/home/hpompougnac/Documents/alp_data/fuzz --reports-directory=/home/hpompougnac/Documents/alp_data/reports --use-cache --csv-output /home/hpompougnac/Documents/alp_data/just_tam_report.csv --verbose-output

# Process the whole experiments space and compare Gus against perf

# ./shifumi.py --include polybench/utilities/ --sources-conf='config/benchmarks.list' --versions-conf='config/versions.list' --compilers-conf=config/cc.list --always-link-with 'polybench/utilities/polybench_stub.c' --tma-scope-install-dir ~/src/projects/tma-scope/ --use-huge-pages --enable-gus --l1-size=80k --l2-size=1250k --l3-size=18m --build-directory=__clean_run__/build --fuzz-directory=__clean_run__/fuzz --reports-directory=__clean_run__/reports --use-cache --csv-output gus_evaluation_report.csv --verbose-output --reuse-perf-reports

# Sample 500 benchmarks in the whole experiments space and compare Gus against
# perf

# ./shifumi.py --include polybench/utilities/ --sources-conf='config/benchmarks.list' --versions-conf='config/versions.list' --compilers-conf=config/cc.list --always-link-with 'polybench/utilities/polybench_stub.c' --tma-scope-install-dir ~/src/projects/tma-scope/ --use-huge-pages --enable-gus --build-directory=clean_run/build --fuzz-directory=clean_run/fuzz --reports-directory=clean_run/reports --use-cache --csv-output full_report.csv --verbose-output --sample 500

# The same as above but with an only one compiler command

# ./shifumi.py --include polybench/utilities/ --sources-conf='config/benchmarks.list' --versions-conf='config/versions.list' --compiler='clang -w -O3 -g -fno-inline -march=native -DMEDIUM_DATASET' --always-link-with 'polybench/utilities/polybench_stub.c' --tma-scope-install-dir ~/src/projects/tma-scope/ --use-huge-pages --enable-gus --build-directory=clean_run/build --fuzz-directory=clean_run/fuzz --reports-directory=clean_run/reports --use-cache --csv-output full_report.csv --verbose-output --sample 500
