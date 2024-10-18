#!/usr/bin/env python3

import argparse
import os
import sys
import subprocess

from helpers import print_warning, run_command_output_free

def main():
    #
    parser = argparse.ArgumentParser(
        description="Generate code from initial benchmarks.",
    )
    group_sources = parser.add_mutually_exclusive_group(required=True)
    group_sources.add_argument(
        "--sources", nargs="+", help="The C files to transform"
    )
    group_sources.add_argument(
        "--sources-conf", type=str, help="The C files to transform"
    )
    group_versions = parser.add_mutually_exclusive_group(required=True)
    group_versions.add_argument(
        "--versions", nargs="+", help="The versions to generate"
    )
    group_versions.add_argument(
        "--versions-conf", type=str, help="The versions to generate"
    )
    parser.add_argument(
        "--target-dir",
        type=str,
        help="The directory in which to generate output files",
        required=True,
    )
    parser.add_argument(
        "--compile-with",
        nargs="*",
        default=[],
        help="The auxiliary C files required to produce the executable",
    )
    parser.add_argument(
        "--linker-options",
        nargs="*",
        default=["-lm"],
        help="The options to feed the linker with",
    )
    parser.add_argument(
        "--include-dirs",
        nargs="*",
        default=[],
        help="The directories where header files live",
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
    # Sources
    sources_filenames: list[str] = []
    # Graph the names listed in the configuration file
    if args.sources_conf:
        if os.path.exists(args.source_conf):
            with open(args.source_conf,'r') as f:
                for l in f.readlines():
                    l = l.replace(' ','')
                    if not l.startswith('#'):
                        sources_filenames.append(l)
        else:
            parser.error(f"{args.source_conf} does not exist.")
    # Graph the names contained in the directory
    elif args.sources_dir:
        if os.path.exists(args.source_dir):
            source_filenames = os.listdir(args.source_dir)
        else:
            parser.error(f"{args.source_dir} does not exist.")
    # Graph the names provided by the command line
    else:
        for s in args.sources:
            if not os.path.exists(s):
                parser.error(f"{s} does not exist.")
            sources_filenames = args.sources
    # Fuzzer file
    fuzzers: dict[str,str] = {}
    if args.versions_conf:
        if os.path.exists(args.versions_conf):
            with open(args.versions_conf,'r') as f:
                for l in f.readlines():
                    if not l.startswith('#'):
                        splitted = l.split('=')
                        if len(splitted) == 0:
                            parser.error(f"{args.versions_conf}: {l} should contain =")
                        name = splitted[0]
                        command = "=".join(splitted[1:])
                        fuzzers[name] = command
        else:
            parser.error(f"{args.versions_conf} does not exist.")
    #
    for s in args.compile_with:
        if not os.path.exists(s):
            parser.error(f"{s} does not exist.")
    #
    for s in args.include_dirs:
        if not os.path.exists(s):
            parser.error(f"{s} does not exist.")
    # Target dir
    if args.target_dir:
        if not os.path.exists(args.target_dir):
            parser.error(f"{args.target_dir} does not exist.")
    #
    num_errors = 0
    for s in sources_filenames:
        basename = os.path.basename(s)
        radical,ext = os.path.splitext(basename)
        for f,c in fuzzers.items():
            target = f"{args.target_dir}/{radical}.{f}{ext}"
            try:
                aux_c = " ".join(args.compile_with)
                includes = "-I " + "-I ".join(args.include_dirs)
                command = f"{c} {s} {aux_c} {includes} -o {target} {args.linker_options}"
                run_command_output_free(command,args.timeout)
            except subprocess.CalledProcessError as e:
                print_warning(args.debug,f"Failure: {c}")
                num_errors += 1
            except subprocess.TimeoutExpired as e:
                print_warning(args.debug,f"Timeout: {c}")
                num_errors += 1
    print_warning(args.debug,f"Total number of errors: {num_errors}")

if __name__ == "__main__":
    main()
