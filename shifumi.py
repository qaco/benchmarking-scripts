#!/usr/bin/env python3

from os import path
import os
import sys
import random
import pandas
from typing import Union, Tuple, cast
from dataclasses import dataclass
import concurrent.futures
import time
import shutil

import ihm
from ihm import print_debug
import wrappers
from text import Report

TAM_MARGIN_FRACTION = 5
LIFT_MRE_DISMISS_BEYOND = 10.0

NAME_KW = "Benchmark"
TAM_BT_BUGGY_KW = "Odd TAM bottlenecks"
GUS_BT_BUGGY_KW = "Odd Gus bottlenecks"
TAM_BT_KW = "TAM bottlenecks"
GUS_BT_KW = "gus sens. bottlenecks"
PERF_CYCLES_KW = "perf cycles"
GUS_CYCLES_KW = "gus cycles"
GUS_RE_KW = "gus relative error"

CC_TIMEOUT = 120  # two minutes


@dataclass
class Blueprint:
    source_original: str
    original_binary: str
    kernel: str
    fuzz_command_list: list[str] | None
    source: str
    compile_command_string: str
    binary: str
    gus_report_path: str
    sens_report_path: str
    perf_report_path: str
    original_perf_report_path: str

    def __eq__(self, other):
        return self.binary == self.binary


def fuzz_it(
    blueprint: Blueprint,
    use_cache: bool,
):
    if (
        not path.exists(blueprint.source_original)
        or blueprint.fuzz_command_list == None
    ):
        return
    if use_cache and path.exists(blueprint.source):
        pass
    else:
        res = wrappers.pocc_compile(
            source=blueprint.source_original,
            destination=blueprint.source,
            compiler=blueprint.fuzz_command_list[0],
            compiler_options=blueprint.fuzz_command_list[1:],
            debug=args.debug,
        )
    return


def compile_it(
    blueprint: Blueprint,
    include_dir: list[str],
    compile_with: list[str],
    use_cache: bool,
    linker_options: list[str],
    debug: bool,
):
    if not path.exists(blueprint.source):
        print_debug(debug, f"CC aborted: {blueprint.source} does not exist.")
    elif use_cache and path.exists(blueprint.binary):
        print_debug(debug, f"CC skipped: {blueprint.binary} exists.")
    else:
        dir_name = path.dirname(blueprint.source_original)
        compile_command_list = blueprint.compile_command_string.split()
        res = wrappers.compile(
            source=blueprint.source,
            destination=blueprint.binary,
            include=include_dir + [dir_name],
            compile_with=compile_with,
            compiler=compile_command_list[0],
            compiler_options=compile_command_list[1:],
            linker_options=linker_options,
            timeout=CC_TIMEOUT,
            debug=debug,
        )
    return


def compile_it_parallel(blueprint, args):
    compile_it(
        blueprint=blueprint,
        include_dir=args.include_dir,
        compile_with=args.always_link_with,
        use_cache=args.use_cache,
        linker_options=args.linker_options,
        debug=args.debug,
    )


def gus_it(
    blueprint: Blueprint,
    l1_size: str,
    l2_size: str,
    l3_size: str,
    use_cache: bool,
    debug: bool,
) -> Report:
    if not path.exists(blueprint.binary):
        print_debug(debug, f"Gus aborted: {blueprint.binary} does not exist.")
        gus_report = Report(
            success=False,
            desc=wrappers.GUS_REPORT,
            benchmark=blueprint.binary,
        )
    else:
        print_debug(debug, f"Gus report on {blueprint.binary}.")
        gus_report = wrappers.gus_detailed(
            executable_path=blueprint.binary,
            l1_size=l1_size,
            l2_size=l2_size,
            l3_size=l3_size,
            kernel=blueprint.kernel,
            gus_report_path=blueprint.gus_report_path,
            use_cache=use_cache,
            debug=debug,
        )
    return gus_report


def gus_it_parallel(blueprint, args):
    gus_report = gus_it(
        blueprint=blueprint,
        l1_size=args.l1_size,
        l2_size=args.l2_size,
        l3_size=args.l3_size,
        use_cache=args.use_cache,
        debug=args.debug,
    )
    return blueprint.binary, gus_report


def tam_it(
    blueprint: Blueprint,
    disable_tam: bool,
    tma_scope_install_dir: str,
    reuse_perf_reports: bool,
    use_huge_pages: bool,
    lib_huge: str,
    core: int,
    debug: bool,
) -> Report:
    if disable_tam:
        tam_report = Report(
            success=False, desc=wrappers.TAM_REPORT, benchmark=blueprint.binary
        )
    elif not path.exists(blueprint.binary):
        print_debug(debug, f"TAM aborted: {blueprint.binary} does not exist.")
        tam_report = Report(
            success=False, desc=wrappers.TAM_REPORT, benchmark=blueprint.binary
        )
    else:
        print_debug(debug, f"Apply TAM on {blueprint.binary}.")
        tam_report = wrappers.perf_tam_l1(
            executable_path=blueprint.binary,
            kernel=blueprint.kernel,
            tma_scope_dir=tma_scope_install_dir,
            report_path=blueprint.perf_report_path,
            reuse_perf_reports=reuse_perf_reports,
            use_huge_pages=use_huge_pages,
            lib_huge=lib_huge,
            core=core,
            debug=debug,
        )
    return tam_report


def find_suspicious_bottlenecks(
    all_blueprints: dict[str, Blueprint],
    reports: dict[str, Report],
) -> dict[str, list[str]]:
    odd_bottlenecks = {}
    for _, blueprint in all_blueprints.items():
        if not (
            reports[blueprint.binary].success
            and reports[blueprint.original_binary].success
        ):
            continue
        bt = suspicious_bottlenecks_of(
            blueprint=blueprint,
            reports=reports,
        )
        odd_bottlenecks[blueprint.binary] = bt
        if len(bt) == 0:
            continue
        # Create the directory intended to store data about the odd bottleneck
        bt_string = "+".join(bt)
        time_since_epoch = str(time.time())
        basename = path.basename(blueprint.binary)
        dir_name = f"{basename}-{bt_string}-{time_since_epoch}"
        dir_path = f"{args.reports_directory}/{dir_name}"
        os.mkdir(dir_path)
        # Copy data to the directory
        base_orig_source = path.basename(blueprint.source_original)
        base_source = path.basename(blueprint.source)
        base_orig_binary = path.basename(blueprint.original_binary)
        base_binary = path.basename(blueprint.binary)
        base_perf_report = path.basename(blueprint.perf_report_path)
        base_orig_perf_report = path.basename(blueprint.original_perf_report_path)
        new_orig_source = f"{dir_path}/{base_orig_source}"
        new_source = f"{dir_path}/{base_source}"
        new_orig_binary = f"{dir_path}/{base_orig_binary}"
        new_binary = f"{dir_path}/{base_binary}"
        new_perf_report = f"{dir_path}/{base_perf_report}"
        new_orig_perf_report = f"{dir_path}/{base_orig_perf_report}"
        shutil.copyfile(blueprint.source_original, new_orig_source)
        shutil.copyfile(blueprint.source, new_source)
        shutil.copyfile(blueprint.original_binary, new_orig_binary)
        shutil.copyfile(blueprint.binary, new_binary)
        shutil.copyfile(blueprint.perf_report_path, new_perf_report)
        shutil.copyfile(blueprint.original_perf_report_path, new_orig_perf_report)
        if args.enable_gus:
            base_gus_report = path.basename(blueprint.gus_report_path)
            base_sens_report = path.basename(blueprint.sens_report_path)
            new_gus_report = f"{dir_path}/{base_gus_report}"
            new_sens_report = f"{dir_path}/{base_sens_report}"
            shutil.copyfile(blueprint.gus_report_path, new_gus_report)
            shutil.copyfile(blueprint.sens_report_path, new_sens_report)
    return odd_bottlenecks


def suspicious_bottlenecks_of(
    blueprint: Blueprint,
    reports: dict[str, Report],
) -> list[str]:
    report_orig = reports[blueprint.original_binary]
    report_mut = reports[blueprint.binary]
    odd_bottlenecks = []
    assert report_orig.metrics
    assert report_mut.metrics
    original_time = report_orig.metrics[wrappers.CYCLES]
    version_time = report_mut.metrics[wrappers.CYCLES]
    assert original_time
    assert version_time
    # The mutant opimizes the original.
    # We take a security offset of 1/TAM_MARGIN_FRACTION in order to be sure
    # that the improvement is not just a sampling artifact.
    fraction_of_original_time = int(original_time / TAM_MARGIN_FRACTION)
    if version_time + fraction_of_original_time < original_time:
        for counter in cast(list[str], report_orig.bottlenecks):
            original_metric = report_orig.metrics[counter]
            version_metric = report_mut.metrics[counter]
            assert original_metric
            assert version_metric
            # The bottleneck is more saturated in the mutant.
            # No need for security offset here because the point is made
            # even if the bottleneck is just as saturated as the former
            # one.
            if version_metric > original_metric:
                odd_bottlenecks.append(counter)

    return odd_bottlenecks


def pack_data(
    all_blueprints: dict[str, Blueprint],
    sorted_blueprints: dict[str, dict[str, list[Blueprint]]],
    tam_reports: dict[str, Report],
    tam_buggy: dict[str, list[str]],
    gus_buggy: dict[str, list[str]],
    enable_gus: bool,
    enable_sensitivity: bool,
    gus_reports: dict[str, Report],
    disable_tam: bool,
    fool_tam: bool,
    fool_gus: bool,
):
    data = {NAME_KW: []}
    if not disable_tam:
        data[PERF_CYCLES_KW] = []
        data[TAM_BT_KW] = []
        if fool_tam:
            data[TAM_BT_BUGGY_KW] = []
    if enable_gus:
        data[GUS_CYCLES_KW] = []
    if enable_sensitivity:
        data[GUS_BT_KW] = []
        if fool_gus:
            data[GUS_BT_BUGGY_KW] = []
    if not disable_tam and enable_gus:
        data[GUS_RE_KW] = []

    for compiler, matrix in sorted_blueprints.items():
        for original, vector in matrix.items():
            # Skip the whole row if you are trying to fool the TAM and the
            # original benchmark is missing
            if fool_tam and not tam_reports[original].success:
                continue
            for blueprint in vector:
                name = blueprint.binary

                # Pre-conditions
                has_been_pruned = name not in all_blueprints
                tam_failed = not disable_tam and (
                    name not in tam_reports or not tam_reports[name].success
                )
                gus_failed = enable_gus and (
                    name not in gus_reports or not gus_reports[name].success
                )
                if has_been_pruned or tam_failed or gus_failed:
                    continue

                data[NAME_KW].append(blueprint.binary)

                if not disable_tam:
                    # TAM data
                    tam_metrics = cast(dict[str, int], tam_reports[name].metrics)
                    data[PERF_CYCLES_KW] += [tam_metrics[wrappers.CYCLES]]
                    data[TAM_BT_KW] += [tam_reports[name].bottlenecks]
                    # The buggy bottlenecks
                    if fool_tam:
                        if name in tam_buggy:
                            data[TAM_BT_BUGGY_KW] += [tam_buggy[name]]
                        else:
                            data[TAM_BT_BUGGY_KW] += [None]
                if enable_gus:
                    # Gus data
                    gus_metrics = cast(dict[str, int], gus_reports[name].metrics)
                    data[GUS_CYCLES_KW] += [gus_metrics[wrappers.CYCLES]]
                if enable_sensitivity:
                    # Sensitivity data
                    data[GUS_BT_KW] += [gus_reports[name].bottlenecks]
                    if fool_tam:
                        if name in gus_buggy:
                            data[GUS_BT_BUGGY_KW] += [gus_buggy[name]]
                        else:
                            data[GUS_BT_BUGGY_KW] += [None]
                if not disable_tam and enable_gus:
                    # The relative error of gus prediction
                    gus_metrics = cast(dict[str, int], gus_reports[name].metrics)
                    tam_metrics = cast(dict[str, int], tam_reports[name].metrics)
                    gus_attempt = gus_metrics[wrappers.CYCLES]
                    perf_truth = tam_metrics[wrappers.CYCLES]
                    assert gus_attempt
                    assert perf_truth
                    relative_error = round((gus_attempt - perf_truth) / perf_truth, 2)
                    data[GUS_RE_KW] += [relative_error]
    df = pandas.DataFrame(data)
    return df


def enumerate_blueprints(
    sources_conf: str,
    sources_cl: list[str],
    kernels_cl: list[str],
    versions_conf: str,
    fuzz_directory: str,
    compilers_conf: str,
    compiler_cl: str,
    build_directory: str,
    reports_directory: str,
) -> Tuple[dict[str, Blueprint], dict[str, dict[str, list[Blueprint]]]]:
    # Sources preprocessing
    original_sources = []
    kernels = []
    if sources_conf == None:
        original_sources = sources_cl
        kernels = kernels_cl
    else:
        assert path.exists(versions_conf)
        with open(sources_conf, "r") as f:
            for line in f:
                if not line.startswith("#"):
                    words = line.split()
                    original_sources.append(words[0])
                    kernels.append(words[1])
    assert len(original_sources)
    assert len(original_sources) == len(kernels)
    # Versions preprocessing
    fuzzers = {}
    fuzz_suffixes = []
    fuzz_commands = []
    if versions_conf != None:
        assert path.exists(versions_conf)
        with open(versions_conf, "r") as f:
            for line in f:
                if not line.startswith("#"):
                    words = line.split("=")
                    fuzz_suffixes.append(words[0])
                    fuzz_commands.append(words[1])
    # Compilers preprocessing
    compiling_commands = []
    compiling_suffixes = []
    if compilers_conf:
        assert path.exists(compilers_conf)
        with open(compilers_conf, "r") as f:
            for line in f:
                if not line.startswith("#"):
                    words = line.split("=")
                    compiling_commands.append("=".join(words[1:]))
                    compiling_suffixes.append(words[0])
    else:
        compiling_commands = [compiler_cl]
        compiling_suffixes = [compiler_cl.split()[0]]
    assert len(compiling_commands) == len(compiling_suffixes)
    # Crafting of the blueprints
    of_compilers = {}
    all_blueprints = {}
    # Iterate on compilers
    for csuffix, ccommand in zip(compiling_suffixes, compiling_commands):
        of_compilers[csuffix] = {}
        # Iterate on C benchmarks
        for original, kernel in zip(original_sources, kernels):
            basename = path.basename(original)
            dirname = path.dirname(original)
            radical, ext = path.splitext(basename)
            # The true non-mutant original
            binary_base = f"{radical}.{csuffix}"
            original_binary = f"{build_directory}/{binary_base}"
            original_gus_report = f"{reports_directory}/{binary_base}.gus"
            original_sens_report = f"{reports_directory}/{binary_base}.sens"
            original_perf_report = f"{reports_directory}/{binary_base}.perf"
            # Note: on the original, source_original = source,
            # binary_original = binary and perf_report = original_perf_report
            original_blueprint = Blueprint(
                source_original=original,
                original_binary=original_binary,
                fuzz_command_list=None,
                source=original,
                compile_command_string=ccommand,
                binary=original_binary,
                kernel=kernel,
                gus_report_path=original_gus_report,
                sens_report_path=original_sens_report,
                perf_report_path=original_perf_report,
                original_perf_report_path=original_perf_report,
            )
            of_compilers[csuffix][original_binary] = [original_blueprint]
            all_blueprints[original_binary] = original_blueprint
            # Iterate on mutations
            for fsuffix, fcommand in zip(fuzz_suffixes, fuzz_commands):
                fuzzed_path = f"{fuzz_directory}/{radical}.{fsuffix}{ext}"
                binary_base = f"{radical}.{fsuffix}.{csuffix}"
                binary = f"{build_directory}/{binary_base}"
                gus_report = f"{reports_directory}/{binary_base}.gus"
                sens_report = f"{reports_directory}/{binary_base}.sens"
                perf_report = f"{reports_directory}/{binary_base}.perf"
                blueprint = Blueprint(
                    source_original=original,
                    original_binary=original_binary,
                    fuzz_command_list=fcommand.split(),
                    source=fuzzed_path,
                    compile_command_string=ccommand,
                    binary=binary,
                    kernel=kernel,
                    gus_report_path=gus_report,
                    perf_report_path=perf_report,
                    sens_report_path=sens_report,
                    original_perf_report_path=original_perf_report,
                )
                of_compilers[csuffix][original_binary].append(blueprint)
                all_blueprints[blueprint.binary] = blueprint
    #
    return all_blueprints, of_compilers


def main(args):
    
    for s in args.sources:
        assert path.exists(s)
    assert not args.sources_conf or path.exists(args.sources_conf)
    assert not args.versions_conf or path.exists(args.versions_conf)
    assert not args.compilers_conf or path.exists(args.compilers_conf)
    assert path.exists(args.fuzz_directory)
    assert path.exists(args.build_directory)
    assert path.exists(args.reports_directory)
    
    # Enumerate
    all_blueprints, sorted_blueprints = enumerate_blueprints(
        sources_conf=args.sources_conf,
        sources_cl=args.sources,
        kernels_cl=args.kernels,
        versions_conf=args.versions_conf,
        compilers_conf=args.compilers_conf,
        compiler_cl=args.compiler,
        fuzz_directory=args.fuzz_directory,
        build_directory=args.build_directory,
        reports_directory=args.reports_directory,
    )
    # Safety check of the above
    for compiler, matrix in sorted_blueprints.items():
        for original, vector in matrix.items():
            for blueprint in vector:
                assert blueprint.binary in all_blueprints

    # Sample
    if args.sample:
        assert args.sample < len(all_blueprints)
        sampled_blueprints = dict(
            random.sample(list(all_blueprints.items()), args.sample)
        )
        original_blueprints = {}
        if args.fool_tam:
            for n, b in sampled_blueprints.items():
                if b.original_binary not in sampled_blueprints:
                    original_blueprints[b.original_binary] = all_blueprints[b.original_binary]
        all_blueprints = {**original_blueprints, **sampled_blueprints}

    # Fuzz.  Parallelism is not a good idea because Pluto is messy.
    fuzz_tot = len(all_blueprints)
    fuzz_num = 1
    for _, blueprint in all_blueprints.items():
        print_debug(args.debug, f"Fuzz {blueprint.source} ({fuzz_num}/{fuzz_tot}).")
        fuzz_it(blueprint=blueprint, use_cache=args.use_cache)
        fuzz_num += 1

    # Compile.
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(compile_it_parallel, blueprint, args)
            for _, blueprint in all_blueprints.items()
        }
        for future in concurrent.futures.as_completed(futures):
            future.result()

    # perf/TAM.
    tam_reports = {}
    blueprints_for_gus = {}
    for _, blueprint in all_blueprints.items():
        tam_report = tam_it(
            blueprint=blueprint,
            disable_tam=args.disable_tam,
            tma_scope_install_dir=args.tma_scope_install_dir,
            reuse_perf_reports=args.reuse_perf_reports,
            use_huge_pages=args.use_huge_pages,
            lib_huge=args.lib_huge,
            core=args.perf_core,
            debug=args.debug,
        )
        tam_reports[blueprint.binary] = tam_report
        tam_report.print(args.verbose_output)
        if tam_report.success:
            blueprints_for_gus[blueprint.binary] = blueprint
    if args.disable_tam:
        blueprints_for_gus = all_blueprints
    # Gus (fed only by benchmarks on which TAM works)
    # Detailed reports
    detailed_reports = {}
    if args.enable_gus:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(gus_it_parallel, blueprint, args)
                for _, blueprint in blueprints_for_gus.items()
            }
            for future in concurrent.futures.as_completed(futures):
                binary, gus_report = future.result()
                detailed_reports[binary] = gus_report
                detailed_reports[binary].print(args.verbose_output)
    sens_reports = {}
    # Sensitivity
    if args.enable_sensitivity:
        sens_tot = len(blueprints_for_gus)
        sens_num = 1
        for n,blueprint in blueprints_for_gus.items():
            print_debug(args.debug, f"Sens. {n} ({sens_num}/{sens_tot}).")
            sens_num += 1
            if not path.exists(blueprint.binary):
                print_debug(args.debug, f"Sens. aborted: {blueprint.binary} does not exist.")
                gus_report = Report(
                    success=False,
                    desc=wrappers.GUS_REPORT,
                    benchmark=blueprint.binary,
                )
            else:
                gus_report = wrappers.gus_sensitivity(
                    executable_path=blueprint.binary,
                    l1_size=args.l1_size,
                    l2_size=args.l2_size,
                    l3_size=args.l3_size,
                    kernel=blueprint.kernel,
                    sens_report_path=blueprint.sens_report_path,
                    use_cache=args.use_cache,
                    debug=args.debug,
                )
                sens_reports[blueprint.binary] = gus_report
                sens_reports[blueprint.binary].print(args.verbose_output)
    gus_reports = {}
    if args.enable_sensitivity and args.enable_gus:
        for n,b in sens_reports.items():
            if n in detailed_reports:
                gus_reports[n] = Report(
                    success = sens_reports[n].success and detailed_reports[n].success,
                    desc = f"{wrappers.GUS_REPORT} + {wrappers.SENS_REPORT}",
                    benchmark = n,
                    bottlenecks = sens_reports[n].bottlenecks,
                    metrics = {**sens_reports[n].metrics,**detailed_reports[n].metrics},
                    report = sens_reports[n].metrics + detailed_reports[n].report,
                )
    elif args.enable_sensitivity:
        gus_reports = sens_reports
    elif args.enable_gus:
        gus_reports = detailed_reports
    # Compute the mean relative error for gus
    sum_relative_errors = 0.0
    sum_relative_errors_lifted = 0.0
    count = 0
    count_lifted = 0
    if args.enable_gus and not args.disable_tam:
        for _, b in blueprints_for_gus.items():
            name = b.binary
            if not gus_reports[name].success:
                continue
            gus_metrics = cast(dict[str, int], gus_reports[name].metrics)
            tam_metrics = cast(dict[str, int], tam_reports[name].metrics)
            gus_attempt = gus_metrics[wrappers.CYCLES]
            perf_truth = tam_metrics[wrappers.CYCLES]
            relative_error = abs(gus_attempt - perf_truth) / perf_truth
            sum_relative_errors += relative_error
            count += 1
            if relative_error < LIFT_MRE_DISMISS_BEYOND:
                sum_relative_errors_lifted += relative_error
                count_lifted += 1
            mean_relative_error = round(sum_relative_errors / count, 2)
            mean_relative_error_lifted = round(
                sum_relative_errors_lifted / count_lifted, 2
            )
            if args.verbose_output:
                print(f"Gus MRE: {mean_relative_error}")
                print(f"Gus MRE lifted: {mean_relative_error_lifted}")

    # Find odd bottlenecks
    tam_buggy = {}
    if args.fool_tam:
        tam_buggy = find_suspicious_bottlenecks(
            all_blueprints=all_blueprints,
            reports=tam_reports,
        )
    gus_buggy = {}
    if args.fool_gus:
        gus_buggy = find_suspicious_bottlenecks(
            all_blueprints=blueprints_for_gus,
            reports=gus_reports,
        )

    # Produce the output
    if args.csv_output:
        df = pack_data(
            all_blueprints=all_blueprints,
            sorted_blueprints=sorted_blueprints,
            tam_reports=tam_reports,
            tam_buggy=tam_buggy,
            gus_buggy=gus_buggy,
            enable_gus=args.enable_gus,
            enable_sensitivity=args.enable_sensitivity,
            gus_reports=gus_reports,
            disable_tam=args.disable_tam,
            fool_tam=args.fool_tam,
            fool_gus = args.fool_gus,
        )
        df.to_csv(args.csv_output)


if __name__ == "__main__":
    args = ihm.get_args()
    main(args)
