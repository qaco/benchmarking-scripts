#!/usr/bin/env python3

import argparse
import os
import sys
import subprocess

from helpers import print_warning, run_command_output_free

def main():
    #
    parser = argparse.ArgumentParser(
        description="Generate mutants from a initial benchmarks.",
    )
    group_binaries = parser.add_mutually_exclusive_group(required=True)
    group_binaries.add_argument(
        "--binaries", nargs="+", help="The binaries to be analyzed"
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
        "--debug",
        action="store_true",
        help="Print warnings",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        help="Timeout of the commands",
    )
    args = parser.parse_args()
    # Binaries
    binaries_filenames: list[str] = []
    # Grab the names listed in the configuration file
    if args.binaries_conf:
        if os.path.exists(args.source_conf):
            with open(args.source_conf,'r') as f:
                for l in f.readlines():
                    l = l.replace(' ','')
                    if not l.startswith('#'):
                        binaries_filenames.append(l)
        else:
            parser.error(f"{args.source_conf} does not exist.")
    # Grab the names contained in the directory
    elif args.binaries_dir:
        if os.path.exists(args.source_dir):
            source_filenames = os.listdir(args.source_dir)
        else:
            parser.error(f"{args.source_dir} does not exist.")
    # Grab the names provided by the command line
    else:
        for s in args.binaries:
            if not os.path.exists(s):
                parser.error(f"{s} does not exist.")
            binaries_filenames = args.binaries
    # Target dir
    if args.target_dir:
        if not os.path.exists(args.target_dir):
            parser.error(f"{args.target_dir} does not exist.")
    # tma-scop install dir
    if args.tma_scope_install_dir:
        if not os.path.exists(args.tma_scope_install_dir):
            parser.error(f"{args.target_dir} does not exist.")
    #
    num_errors = 0
    for b in binaries_filenames:
        ...
        # basename = os.path.basename(s)
    #     radical,ext = os.path.splitext(basename)
    #     for f,c in fuzzers.items():
    #         target = f"{args.target_dir}/{radical}.{f}{ext}"
    #         try:
    #             command = f"{c} {s} -o {target}"
    #             run_command_output_free(command,args.timeout)
    #         except subprocess.CalledProcessError as e:
    #             print_warning(args.debug,f"Failure: {c}")
    #             num_errors += 1
    #         except subprocess.TimeoutExpired as e:
    #             print_warning(args.debug,f"Timeout: {c}")
    #             num_errors += 1
    # print_warning(args.debug,f"Total number of errors: {num_errors}")
