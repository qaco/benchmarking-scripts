#!/usr/bin/env python3

import argparse
import os
import sys
import subprocess

from helpers import print_warning, run_command

DYNAMORIO_DIR_NAME = "DynamoRIO-Linux-10.93.20000"

def main():
    #
    parser = argparse.ArgumentParser(
        description="Produces perf reports on each input binaries.",
        epilog = '''Example:
        ./run_perf.py --binaries-dir __inputs__ --target-dir __outputs__ --tma-scope-install-dir ~/src/projects/tma-scope/ --perf-core 1 --verbose --very-verbose
        '''
    )
    group_binaries = parser.add_mutually_exclusive_group(required=True)
    group_binaries.add_argument(
        "--binaries", nargs="+", help="The binaries to be analyzed"
    )
    group_binaries.add_argument(
        "--binaries-dir", type=str, help="The binaries to be analyzed"
    )
    group_binaries.add_argument(
        "--binaries-conf", type=str, help="The binaries to be analyzed"
    )
    parser.add_argument(
        "--target-dir",
        type=str,
        help="The directory in which to generate output files",
        required=True,
    )
    parser.add_argument(
        "--use-huge-pages",
        action="store_true",
        help="Use huse pages",
    )
    parser.add_argument(
        "--lib-hugepages",
        type=str, default="libhugelbfs-2.23.so",
        help="The huge pages library to use"
    )
    parser.add_argument(
        "--tma-scope-install-dir",
        type=str,
        default=None,
        help="The install dir of Alban Dutilleul's tma-scope",
    )
    parser.add_argument(
        "--perf-core",
        type=int,
        default=0,
        help="The core on which perf should run"
    )
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="Use cache",
    )
    parser.add_argument(
        "--use-cache-only",
        action="store_true",
        help="Use cache only",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print stuff",
    )
    parser.add_argument(
        "--very-verbose",
        action="store_true",
        help="Print more stuff",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout of the commands",
    )
    args = parser.parse_args()
    # Binaries
    binaries: list[str] = []
    # Grab the names listed in the configuration file
    if args.binaries_conf:
        if os.path.exists(args.source_conf):
            with open(args.source_conf,'r') as f:
                for l in f.readlines():
                    l = l.replace(' ','')
                    if not l.startswith('#'):
                        binaries.append(l)
        else:
            parser.error(f"{args.source_conf} does not exist.")
    # Grab the names contained in the directory
    elif args.binaries_dir:
        if os.path.exists(args.binaries_dir):
            binaries_tmp = os.listdir(args.binaries_dir)
            binaries = []
            for b in binaries_tmp:
                binary = f"{args.binaries_dir}/{b}"
                binaries.append(binary)
        else:
            parser.error(f"{args.source_dir} does not exist.")
    # Grab the names provided by the command line
    else:
        for s in args.binaries:
            if not os.path.exists(s):
                parser.error(f"{s} does not exist.")
            binaries = args.binaries
    # Target dir
    if args.target_dir:
        if not os.path.exists(args.target_dir):
            parser.error(f"{args.target_dir} does not exist.")
    # tma-scope install dir
    if args.tma_scope_install_dir:
        if not os.path.exists(args.tma_scope_install_dir):
            parser.error(f"{args.tma_scope_install_dir} does not exist.")
    # The big loop
    num_errors = 0
    count = 0
    load_from_cache = args.use_cache or args.use_cache_only
    skip_if_no_in_cache = args.use_cache_only
    for binary in binaries:
        count += 1
        print_warning(args.verbose, f"{count}/{len(binaries)} - Analyzing {binary}")
        # Report path
        bb = os.path.basename(binary)
        radical,ext = os.path.splitext(bb)
        report_path = f"{args.target_dir}/{bb}.perf"
        if load_from_cache and os.path.exists(report_path):
            print_warning(args.verbose, f"{report_path} reloaded from disk")
            continue
        elif skip_if_no_in_cache:
            print_warning(args.verbose, f"{report_path} no on disk")
            continue
        # Kernel
        bbs = bb.split('.')
        kernel = "kernel_" + bbs[0].replace('-','_')
        # Default command
        command_list = [
                "perf",
                "stat",
                binary,
        ]
        env_vars = {}
        if args.use_huge_pages:
            env_vars['LD_PRELOAD'] = args.lib_hugepages
        # If tma-scope
        if args.tma_scope_install_dir:
            command_list = [
                f"{args.tma_scope_install_dir}/{DYNAMORIO_DIR_NAME}/bin64/drrun",
                "-c",
                f"{args.tma_scope_install_dir}/build/libtmascope.so",
                "--",
                binary,
            ]
            env_vars["TMA_FUNCTION"] = kernel
            env_vars["TMA_OUTPUT_FILE"] = report_path
            env_vars["TMA_LEVEL"] = "TopdownL1"
            env_vars["TMA_CORE"] = str(args.perf_core)
        #
        command = " ".join(command_list)
        env_str = ""
        for k in env_vars:
            env_str += f"{k}={env_vars[k]} "
        full_command = f"{env_str} {command}"
        print_warning(args.verbose, f"Launching: {full_command}")
        # Go
        try:
            stdout,stderr = run_command(
                command = full_command,
                timeout = args.timeout,
            )
        except subprocess.CalledProcessError as e:
            print_warning(args.verbose,f"Failure: {full_command}")
            num_errors += 1
        except subprocess.TimeoutExpired as e:
            print_warning(args.verbose,f"Timeout: {full_command}")
            num_errors += 1
        print_warning(args.verbose, f"Success on producing {report_path}")
        with open(report_path,'w') as f:
            f.write(stderr)
        print_warning(args.very_verbose, f"{stderr}")
    print_warning(args.verbose,f"Total number of errors: {num_errors}")

if __name__ == "__main__":
    main()
