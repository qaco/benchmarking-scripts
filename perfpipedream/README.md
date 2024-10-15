Perf-Pipedream
==============
Linux' perf event, but with a PAPI-like interface.

# Author
- Nicolas Derumigny <nicolas.derumigny@inria.fr>

# Usage
Same as PAPI, but functions are instead prefixed by `perf_pipedream_`.

# Requirements
- CMake 3.14+
- Perf

# Installation
```sh
mkdir -p build
cd build
cmake ..
sudo make install
```

Note that
```sh
export LD_LIBRARY_PATH=/usr/local/lib
```
may be necessary to allow execution of programs using Perf-Pipedream.
