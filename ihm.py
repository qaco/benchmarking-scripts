import argparse
import sys
from typing import Union


def print_debug(debug: bool, message: Union[str, None] = None):
    if debug:
        print(message, file=sys.stderr)

def get_args():
    parser = argparse.ArgumentParser(
        description="Highlight microarchitectural bottlenecks.",
    )
    group_samples = parser.add_mutually_exclusive_group(required=True)
    group_samples.add_argument(
        "--sources", nargs="+", default=[], help="The C files to be analyzed"
    )
    group_samples.add_argument(
        "--sources-conf", type=str, default=None, help="The C files to be analyzed"
    )
    parser.add_argument(
        "--versions-conf", type=str, default=None, help="The versions to generate"
    )
    parser.add_argument(
        "--lib-huge", type=str, default="libhugelbfs-2.23.so", help="The huge pages library to use"
    )
    parser.add_argument("--kernels", nargs="+", help="The symbols to be inspected")
    group_cc = parser.add_mutually_exclusive_group(required=False)
    group_cc.add_argument(
        "--compiler",
        type=str,
        default="clang -w -O3 -g -fno-inline -march=native",
        help="The compiler to use",
    )
    group_cc.add_argument(
        "--compilers-conf", type=str, default=None, help="The compilers to use"
    )
    parser.add_argument(
        "--always-link-with",
        nargs="*",
        default=[],
        help="The auxiliary C files required to produce the executable",
    )
    parser.add_argument(
        "--include-dir",
        nargs="*",
        default=[],
        help="The directory where header files live",
    )
    parser.add_argument(
        "--linker-options",
        nargs="*",
        default=["-lm"],
        help="The options to feed the linker with",
    )
    parser.add_argument(
        "--build-directory",
        type=str,
        default="/tmp",
        help="The directory in which to generate binaries",
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
        "--tma-scope-install-dir",
        type=str,
        default=None,
        help="The install dir of Alban Dutilleul's tma-scope",
    )
    parser.add_argument(
        "--fuzz-directory",
        type=str,
        default="/tmp",
        help="The directory in which to generate versions",
    )
    parser.add_argument(
        "--reports-directory",
        type=str,
        default="/tmp",
        help="The directory in which to save versions",
    )
    parser.add_argument(
        "--use-cache", action="store_true", help="Cache intermediate files"
    )
    parser.add_argument(
        "--reuse-perf-reports", action="store_true", help="Reuse perf reports"
    )
    parser.add_argument(
        "--csv-output",
        type=str,
        default=None,
        help="The CSV file in which write the results",
    )
    parser.add_argument(
        "--sample", type=int, default=0, help="Sample N blueprints (don't sample if 0)"
    )
    parser.add_argument(
        "--fool-gus", action="store_true", help="Try to fool the results of Gus"
    )
    group_tam = parser.add_mutually_exclusive_group(required=False)
    group_tam.add_argument(
        "--fool-tam", action="store_true", help="Try to fool the results of TAM"
    )
    group_tam.add_argument("--disable-tam", action="store_true", help="Disable TAM")
    parser.add_argument(
        "--perf-core",
        type=int,
        default=0,
        help="The core on which perf should run"
    )
    parser.add_argument(
        "--enable-gus", action="store_true", help="Enable Gus detailed report"
    )
    parser.add_argument(
        "--enable-sensitivity",
        action="store_true",
        help="Enable Gus sensitivity report",
    )
    parser.add_argument(
        "--use-huge-pages",
        action="store_true",
        help="Perf uses huge pages",
    )
    parser.add_argument("--debug", action="store_true", help="Print debug messages")
    parser.add_argument(
        "--verbose-output", action="store_true", help="Print results on stdout"
    )
    args = parser.parse_args()
    if args.fool_gus is not None and args.enable_sensitivity is None:
        parser.error("--fool-gus requires --enable-sensitivity")
    return args
