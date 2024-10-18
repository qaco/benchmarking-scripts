#!/usr/bin/env python3

from typing import Tuple
import argparse
import os
import sys
import subprocess
import concurrent.futures

from helpers import print_warning, run_command

DYNAMORIO_DIR_NAME = "DynamoRIO-Linux-10.93.20000"

def gus_it(binary,args) -> Tuple[bool,str]:
    load_from_cache = args.use_cache or args.use_cache_only
    skip_if_no_in_cache = args.use_cache_only
    # Report path
    bb = os.path.basename(binary)
    radical,ext = os.path.splitext(bb)
    report_path = f"{args.target_dir}/{bb}.gus"
    if load_from_cache and os.path.exists(report_path):
        print_warning(args.verbose, f"{report_path} reloaded from disk")
        return True,report_path
    elif skip_if_no_in_cache:
        print_warning(args.verbose, f"{report_path} no on disk")
        return False,report_path
    # Kernel
    bbs = bb.split('.')
    kernel = "kernel_" + bbs[0].replace('-','_')
    # Default command
    cache_sizes = " ".join([
        "--L1-size",
        args.l1_size,
        "--L2-size",
        args.l2_size,
        "--L3-size",
        args.l3_size
    ])
    full_command = f"gus {cache_sizes} --kernel {kernel} {binary}"
    print_warning(args.verbose, f"Launching: {full_command}")
    # Go
    correct = True
    try:
        stdout,stderr = run_command(
            command = full_command,
            timeout = args.timeout,
        )
        with open(report_path,'w') as f:
            f.write(stdout)
            print_warning(args.very_verbose, f"{stdout}")
    except subprocess.CalledProcessError as e:
        print_warning(args.verbose,f"Failure: {full_command}")
        correct=False
    except subprocess.TimeoutExpired as e:
        print_warning(args.verbose,f"Timeout: {full_command}")
        correct=False
    print_warning(args.verbose, f"Success on producting {report_path}")
    return correct,report_path

def main():
    #
    parser = argparse.ArgumentParser(
        description="Produces perf reports on each input binaries.",
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
        "--l1-size",
        type=str,
        default="49152",
        help="The size in bytes, kilobytes (k), megabytes (m) or gigabytes (g) of the L1 cache.",
    )
    parser.add_argument(
        "--l2-size",
        type=str,
        default="524288",
        help="The size in bytes, kilobytes (k), megabytes (m) or gigabytes (g) of the L2 cache.",
    )
    parser.add_argument(
        "--l3-size",
        type=str,
        default="16777216",
        help="The size in bytes, kilobytes (k), megabytes (m) or gigabytes (g) of the L2 cache.",
    )
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="Use cache",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Use cache",
    )
    parser.add_argument(
        "--threads_max",
        type=int,
        default=8,
        help="Threads max",
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
        default=120,
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
        if os.path.exists(args.source_dir):
            binaries = os.listdir(args.source_dir)
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
    # The big loop
    num_errors = 0
    count = 0
    if args.parallel:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(gus_it, binary, args)
                for binary in binaries
            }
            for future in concurrent.futures.as_completed(futures):
                correct, report_path = future.result()
                if not correct:
                    print(correct)
                    assert(False)
                    num_errors += 1
    else:
        for binary in binaries:
            count += 1
            print_warning(args.verbose, f"{count}/{len(binaries)} - Analyzing {binary}")
            correct,report_path = gus_it(binary,args)
            if not correct:
                num_errors += 1
    print_warning(args.verbose,f"Total number of errors: {num_errors}")

if __name__ == "__main__":
    main()
