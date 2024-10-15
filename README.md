# Shifumi

Shifumi is a harness which:
+ Generates a lot of benchmarks from input files
+ Compile them (in different flavours)
+ Apply TAM and/or Gus and/or Gus's sensitivity analysis on the resulting
  binaries
+ Optionnaly tries to identify benchmarks on which TAM says bullshit.

## Installation

The TL;DR is:
+ ```Gus```and ```perf``` are needed, and (optionnally) using ```tma-scope```
requires patching it with ```patches/simpler_tma_scope.patch```.
+ The testing environment is set by disabling the hyperthreading in BIOS and
  executing ```sudo ./setup_test_env.sh```
+ Have fun ! Examples of commands are in ```./launch_evaluation.sh```.

### Dependencies rationale

The polybenches are embedded in the repo.

We use ```perf``` because ```papi``` relies on libpfm4, which does not support
some recent microarchitectures, including AlderLake
([not true anymore](https://github.com/icl-utk-edu/papi/blob/master/ChangeLogP720b1.txt)).
On the other side, ```vtune``` is obviously not portable (we intend to do
experiments on ARM and AMD chips).

We also need to profile a section of the code (a function call) instead of the
whole program, because in this case the results are polluted by initialization
stuff. Two approaches are possible (we choose the first):
+ Run ```perf``` in a different process launched at the beginning of the
  function and killed when the latter returns, as [here](https://muehe.org/posts/profiling-only-parts-of-your-code-with-perf/).
  The library ```tma-scope``` implements this principle.
  **Important warning here**: if you use it in the context of ```shifumi```,
  please patch it with ```patches/simpler_tma_scope.patch``` in order to make
  its output understandable by ```shifumi```.
+ Use the perf API, either [a wrapper library](https://github.com/AlexGustafsson/perf/tree/main)
  or the syscall ```perf_event_open``` directly. This approach would require to write
  an alternate ```polybench/utilities/polybench.c``` file.

### Making things executable

In the root directory:
```
chmod +x shifumi.py
git submodule update --init
pip install -r requirements.txt
```

## Test environment

Here we explain the script ```./setup_test_env.sh```.

### The frequency

First, we have to set the frequency. On recent Linux distributions,
a pilot preventing the use of ```cpufreq-set``` is the default.
To disable it, append ```intel_pstate=disable``` to ```GRUB_CMDLINE_LINUX```
option in ```/etc/default/grub```, and reboot. It is shown
[here](https://stackoverflow.com/questions/23526671/how-to-solve-the-cpufreqset-errors).

Once it is done, you can set the frequency by doing:
```
sudo cpufreq-set -g userspace
sudo cpufreq-set -f 2.5Ghz
```
It is shown [here](https://www.thinkwiki.org/wiki/How_to_use_cpufrequtils).

### The huge pages

Then, we have to provide huge pages. We follow [this tutorial](https://paolozaino.wordpress.com/2016/10/02/how-to-force-any-linux-application-to-use-hugepages-without-modifying-the-source-code/).

First, install:
```
sudo apt install libhugelbfs-bin
apt install libhugetlbfs0
```

Check the Huge Page configuration:
```
$ grep HugePages_Total /proc/meminfo
HugePages_Total:   0
```

Then check the size of Huge Pages:
```
$ grep Hugepagesize /proc/meminfo
Hugepagesize:     2048 kB
```

Allocate 2048 Huge Pages (4GB of Huge Pages) in root:
```
# echo 2048 > /proc/sys/vm/nr_hugepages
```

Check the allocation with
```
$ grep HugePages_Total /proc/meminfo
$ grep HugePages_Free /proc/meminfo # how many are free
```

List all huge page pools available:
```
$ hugeadm --pool-list
```

Now we need to mount hugetlbfs (the chown is because the app is non-root;
of course, postfix is needed):
```
# mkdir -p /mnt/hugetlbfs
# mount -t hugetlbfs none /mnt/hugetlbfs
# chown postfix:postfix /mnt/hugetlbfs
```

Each mounting point is associated with a page size. To override the default:
```
# mkdir -p /mnt/hugetlbfs-64K
# mount -t hugetlbfs none -opagesize=64k /mnt/hugetlbfs-64K
# chown postfix:postfix /mnt/hugetlbfs-64k
```

Set the recommended Shared Memory Max:
```
# hugeadm --set-recommended-shmmax
```

Report of the configuration:
```
$ hugeadm --explain
```

Now you have just to launch your app (in our case, it is done in the
Python script when the flag ```use-huge-pages``` is set):
```
LD_PRELOAD=libhugetlbfs-2.23.so HUGETLB_MORECORE=yes <myapp>
```
The name ```libhugetlbfs-2.23.so``` can be found using
```apt-file list libhugetlbfs0```. For now it is hard-coded in 
```wrappers.py```. Feel free to modify.

## Useful commands

Some of these commands rely on the files config/cc.list, config/versions.list,
config/benchmarks.list. Please look at them, they describe respectively
the C compilers triggered, the polyhedral compilers and the benchmarks processed.

They may also rely on the directories ```__fuzz__```, ```__build__``` and
```__reports__``` which need to be created by hand before launching the thing.
If they are not specified, temporary files go to ```/tmp```.

Also, please note that the fuzzing harness may trigger some compilation errors.
It is normal (the corresponding benchmarks are obviously not used) since Pluto
sometimes produces broken C files.

The minimal thing (apply TAM on a benchmark):
```
./shifumi.py --include polybench/utilities/ --sources './polybench/linear-algebra/kernels/2mm/2mm.c' --kernels 'kernel_2mm' --compiler 'clang -w -O3 -g -fno-inline -march=native' --always-link-with 'polybench/utilities/polybench_stub.c' --tma-scope-install-dir ~/src/projects/tma-scope/ --verbose-output
```

Try to fool TAM working on a single benchmark:
```
./shifumi.py --include polybench/utilities/ --sources './polybench/linear-algebra/kernels/2mm/2mm.c' --kernels 'kernel_2mm' --versions-conf='config/versions.list' --compilers-conf=config/cc.list --always-link-with 'polybench/utilities/polybench_stub.c' --tma-scope-install-dir ~/src/projects/tma-scope/ --fool-tam --build-directory=__build__ --fuzz-directory=__fuzz__ --reports-directory=__reports__ --use-cache --csv-output full_report.csv --verbose-output
```

Try to fool TAM working on all benchmarks:
```
./shifumi.py --include polybench/utilities/ --sources-conf='config/benchmarks.list' --versions-conf='config/versions.list' --compilers-conf=config/cc.list --always-link-with 'polybench/utilities/polybench_stub.c' --tma-scope-install-dir ~/src/projects/tma-scope/ --fool-tam --use-huge-pages --build-directory=__build__ --fuzz-directory=__fuzz__ --reports-directory=__reports__ --use-cache --csv-output full_report.csv --verbose-output
```

The same as above but with a single compiler:
```
./shifumi.py --include polybench/utilities/ --sources-conf='config/benchmarks.list' --versions-conf='config/versions.list' --compiler 'clang -w -O3 -g -fno-inline -march=native -DSMALL_DATASET' --always-link-with 'polybench/utilities/polybench_stub.c' --tma-scope-install-dir ~/src/projects/tma-scope/ --fool-tam --build-directory=__build__ --fuzz-directory=__fuzz__ --reports-directory=__reports__ --use-cache --csv-output full_report.csv --verbose-output
```

Compare GUS prediction with Perf with the whole set of benchmarks:
```
./shifumi.py --include polybench/utilities/ --sources-conf='config/benchmarks.list' --versions-conf='config/versions.list' --compilers-conf=config/cc.list --always-link-with 'polybench/utilities/polybench_stub.c' --tma-scope-install-dir ~/src/projects/tma-scope/ --enable-gus --build-directory=__build__ --fuzz-directory=__fuzz__ --reports-directory=__reports__ --use-cache --csv-output full_report.csv --verbose-output
```

Compare GUS prediction with Perf with a subset (sampling) of benchmarks:
```
./shifumi.py --include polybench/utilities/ --sources-conf='config/benchmarks.list' --versions-conf='config/versions.list' --compilers-conf=config/cc.list --always-link-with 'polybench/utilities/polybench_stub.c' --tma-scope-install-dir ~/src/projects/tma-scope/ --sample 10 --enable-gus --build-directory=__build__ --fuzz-directory=__fuzz__ --reports-directory=__reports__ --use-cache --csv-output full_report.csv --verbose-output
```

Compare GUS prediction with a single family of benchmarks:
```
./shifumi.py --include polybench/utilities/ --sources './polybench/linear-algebra/kernels/2mm/2mm.c' --kernels 'kernel_2mm' --versions-conf='config/versions.list' --compiler 'clang -w -O3 -g -fno-inline -march=native -DSMALL_DATASET' --always-link-with 'polybench/utilities/polybench_stub.c' --tma-scope-install-dir ~/src/projects/tma-scope/ --enable-gus --build-directory=__build__ --fuzz-directory=__fuzz__ --reports-directory=__reports__ --use-cache --csv-output full_report.csv --verbose-output
```

Help:
```
./shifumi.py --help
```

## Additionnal commands for manual exploration

The ```tma-scope```-based calls to ```perf```:
```
TMA_FUNCTION=kernel_lu TMA_OUTPUT_FILE=__reports__/lu.pocc.regtiling8.gcc.O3.medium.perf TMA_LEVEL=TopdownL1 TMA_CORE=0 /home/hpompougnac/src/projects/tma-scope//DynamoRIO-Linux-10.93.20000/bin64/drrun -c /home/hpompougnac/src/projects/tma-scope//build/libtmascope.so -- __build__/lu.pocc.regtiling8.gcc.O3.medium
```

With huge pages:
```
LD_PRELOAD=libhugetlbfs-2.23.so HUGETLB_MORECORE=yes TMA_FUNCTION=kernel_lu TMA_OUTPUT_FILE=__reports__/lu.pocc.regtiling8.gcc.O3.medium.perf TMA_LEVEL=TopdownL1 TMA_CORE=0 /home/hpompougnac/src/projects/tma-scope//DynamoRIO-Linux-10.93.20000/bin64/drrun -c /home/hpompougnac/src/projects/tma-scope//build/libtmascope.so -- __build__/lu.pocc.regtiling8.gcc.O3.medium
```

Produce a pretty disassembled kernel:
```
objdump --disassemble=kernel_3mm --disassembler-color=on --visualize-jumps=color --no-show-raw-insn --no-addresses -M intel64 __build__/3mm.pluto.tiling
```

Add the valuable ```perf``` annotations to the assembly:
```
perf record <myapp>
perf annotate -Mintel
```

## To do

+ Try to fool Gus as well
