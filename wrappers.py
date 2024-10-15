import os
import command
import re
from typing import Optional
import pandas as pd
import io
import sys

from text import Report, parse_float, parse_int
from ihm import print_debug

CYCLES = "cycles"
SLOTS = "slots"
RETIRING = "topdown-retiring"
FE_BOUND = "topdown-fe-bound"
BE_BOUND = "topdown-be-bound"
BAD_SPEC = "topdown-bad-spec"
GUS_REPORT = "Gus report"
TAM_REPORT = "TAM report"
SENS_REPORT = "Sens report"

POCC_TIMEOUT = 120 # two minutes
GUS_TIMEOUT = 300 # five minutes
SENS_TIMEOUT = 900

counters = [
    CYCLES,
    SLOTS,
    RETIRING,
    BE_BOUND,
    FE_BOUND,
    BAD_SPEC,
]

# Thresholds from
# https://cdrdv2-public.intel.com/766317/vtune-profiler_cookbook_2023.0-766316-766317.pdf
tma_thresholds = {RETIRING: 70.0, BE_BOUND: 40.0, FE_BOUND: 10.0, BAD_SPEC: 5.0}


def perf_tam_l1(
    executable_path: str,
    kernel: str,
    tma_scope_dir: str,
    report_path: str,
    reuse_perf_reports: bool,
    use_huge_pages: bool,
    lib_huge: str,
    core: int,
    debug: bool,
):
    #
    if tma_scope_dir:
        command_list = [
            f"{tma_scope_dir}/DynamoRIO-Linux-10.93.20000/bin64/drrun",
            "-c",
            f"{tma_scope_dir}/build/libtmascope.so",
            "--",
            executable_path,
        ]
        env_vars={
                "TMA_FUNCTION": kernel,
                "TMA_OUTPUT_FILE": report_path,
                "TMA_LEVEL": "TopdownL1",
                "TMA_CORE": str(core),
        }
    else:
        command_list = [
            "perf",
            "stat",
            executable_path,
        ]
        env_vars = {}

    if use_huge_pages:
        env_vars['LD_PRELOAD'] = lib_huge
        
    if reuse_perf_reports:
        if os.path.exists(report_path):
            f = open(report_path,'r')
            report = f.read()
            success = True
            f.close()
        else:
            return Report(success=False, desc=TAM_REPORT, benchmark=executable_path)
    else:
        res = command.execute(
            command_list,
            env_vars=env_vars,
            target_file=report_path,
            debug=debug,
        )
        report = res.message
        success = res.success
    
    #
    metrics = {}
    for m in counters:
        v = parse_int("(.*)" + m, report)
        if v == None:
            return Report(success=False, desc=TAM_REPORT, benchmark=executable_path)
        metrics[m] = v
    #
    bottlenecks = []
    for counter, threshold in tma_thresholds.items():
        percent = (metrics[counter] / metrics[SLOTS]) * 100
        metrics[counter + "-percent"] = round(percent, 2)
        print_debug(
            debug,
            f"{counter} is {percent}% bt vs {threshold}% (threshold) "
            + f"so counter >= threshold is {percent >= threshold}",
        )
        if percent >= threshold:
            print_debug(debug, f"{counter} is a bottleneck for {executable_path}")
            bottlenecks.append(counter)
    #
    report = Report(
        success=True,
        desc=TAM_REPORT,
        bottlenecks=bottlenecks,
        metrics=metrics,
        report=report,
        benchmark=executable_path,
    )
    return report


def gus_detailed(
    executable_path: str,
    kernel: str,
    gus_report_path: str,
    l1_size: str,
    l2_size: str,
    l3_size: str,
    use_cache: bool,
    debug: bool,
):

    command_list = [
        "gus",
        "--L1-size",
        l1_size,
        "--L2-size",
        l2_size,
        "--L3-size",
        l3_size,
        "--kernel",
        kernel,
        executable_path,
    ]

    if use_cache and os.path.exists(gus_report_path):
        f = open(gus_report_path, "r")
        gus_report = f.read()
        f.close()
    else:
        res_detailed = command.execute(
            command_list,
            target_file=gus_report_path,
            timeout = GUS_TIMEOUT,
            debug=debug,
        )
        if not res_detailed.success:
            return Report(success=False, desc=GUS_REPORT, benchmark=executable_path)
        gus_report = res_detailed.message

    cycles = parse_int("EXECUTION TIME:(.*)cycles", gus_report)
    metrics: dict[str, int | None] = {CYCLES: cycles}
    return Report(
        success=True,
        desc=GUS_REPORT,
        metrics=metrics,
        report=gus_report,
        benchmark=executable_path,
    )


def gus_sensitivity(
    executable_path: str,
    kernel: str,
    sens_report_path: str,
    l1_size: str,
    l2_size: str,
    l3_size: str,
    use_cache: bool,
    debug: bool,
    sensitivity_threshold: float = 0.0,
):
    base_name = os.path.basename(executable_path)
    command_list = [
        "gus",
        "--L1-size",
        l1_size,
        "--L2-size",
        l2_size,
        "--L3-size",
        l3_size,
        "--kernel",
        kernel,
        executable_path,
        "-s",
        "--pdf-out",
        "/tmp/out.pdf",
    ]
    if use_cache and os.path.exists(sens_report_path):
        f = open(sens_report_path, "r")
        sens_report = f.read()
        f.close()
    else:
        res = command.execute(
            command_list,
            target_file=sens_report_path,
            timeout=SENS_TIMEOUT,
            debug=debug
        )
        if not res.success:
            return Report(success=False, desc=SENS_REPORT, benchmark=executable_path)
        sens_report = res.message

    #
    # Remove comments
    clean_output = "\n".join(sens_report.splitlines()[1:])
    # Remove semicolon at eol
    clean_output = clean_output.replace(";", "")
    # Parse the csv
    try:
        df = pd.read_csv(io.StringIO(clean_output))
    except (pd.errors.ParserError, pd.errors.EmptyDataError):
        print_debug(
            debug,
            f"Fail to parse the sensitivity report for {executable_path}",
        )
        return Report(success=False, desc=SENS_REPORT, benchmark=executable_path)
    # Convert strings to floats
    df.iloc[:, -1] = pd.to_numeric(df.iloc[:, -1], errors="coerce")
    #
    metrics = {}
    for r, m in zip(df.iloc[:, 0], df.iloc[:, -1]):
        metrics[r] = m
    # Filter the sensible resources
    filtered_df = df[df.iloc[:, -1] > sensitivity_threshold]
    # Iterate
    bottlenecks = []
    for r, m in zip(filtered_df.iloc[:, 0], filtered_df.iloc[:, -1]):
        bottlenecks.append(r)
    #
    report = Report(
        success=True,
        desc=SENS_REPORT,
        bottlenecks=bottlenecks,
        metrics=metrics,
        report=sens_report,
        benchmark=executable_path,
    )
    return report


def gus_report_and_sensitivity(
    executable_path: str,
    kernel: str,
    l1_size: str,
    l2_size: str,
    l3_size: str,
    gus_report_path: str,
    sens_report_path: str,
    use_cache: bool,
    debug: bool,
    sensitivity_threshold: float = 0.0,
):
    gus_report = gus_detailed(
        executable_path=executable_path,
        kernel=kernel,
        l1_size = l1_size,
        l2_size = l2_size,
        l3_size = l3_size,
        gus_report_path=gus_report_path,
        use_cache=use_cache,
        debug=debug,
    )

    if not gus_report.success:
        return gus_report

    metrics = gus_report.metrics

    sens_report = gus_sensitivity(
        executable_path=executable_path,
        kernel=kernel,
        l1_size = l1_size,
        l2_size = l2_size,
        l3_size = l3_size,
        sens_report_path=sens_report_path,
        use_cache=use_cache,
        debug=debug,
    )

    if not sens_report.success:
        return sens_report

    assert(gus_report.report)
    assert(sens_report.report)
    final_report = Report(
        success=True,
        desc="+".join([GUS_REPORT, SENS_REPORT]),
        bottlenecks=sens_report.bottlenecks,
        metrics={**gus_report.metrics, **sens_report.metrics},
        report=gus_report.report + sens_report.report,
        benchmark=executable_path,
    )
    return final_report


def pocc_compile(
    source: str,
    destination: str,
    compiler: str,
    compiler_options: list[str],
    debug: bool,
):
    return compile(
        source=source,
        destination=destination,
        include=[],
        compile_with=[],
        compiler=compiler,
        compiler_options=compiler_options,
        linker_options=[],
        debug=debug,
        timeout = POCC_TIMEOUT,
    )


def compile(
    source: str,
    destination: str,
    include: list[str],
    compile_with: list[str],
    compiler: str,
    compiler_options: list[str],
    linker_options: list[str],
    debug: bool,
    timeout: int | None = None,
):

    inclusions = []
    for i in include:
        inclusions += ["-I"] + [i]
    command_list = (
        [compiler]
        + compiler_options
        + inclusions
        + [source]
        + compile_with
        + ["-o", destination]
        + linker_options
    )
    res = command.execute(
        command_list=command_list,
        message_if_success=destination,
        capture_output=False,
        debug=debug,
        timeout=timeout,
    )
    return res
