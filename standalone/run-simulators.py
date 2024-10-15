import argparse
import os
import multiprocessing
import glob
import subprocess
import random
from timeit import default_timer as timer


def launch_subprocess_with_timeout(
    command, timeout, stdout=subprocess.PIPE, stderr=subprocess.PIPE
):
    start_time, end_time = None, None
    try:
        start_time = timer()
        subprocess.run(command, stdout=stdout, stderr=stderr, timeout=timeout)
        end_time = timer()
    except subprocess.TimeoutExpired:
        print(f"Timeout expired for command {command}")
        return None
    except Exception as e:
        print(f"Error running command {command}")
        print(f"Error: {e}")
        return None
    return end_time - start_time


def run_gus(
    executable: str,
    output_directory: str,
    gus_directory: str,
    timeout: int,
    use_cache: bool,
):
    print(f"[GUS] Running {executable}")
    
    file_name = os.path.basename(executable)

    def normalize_file_name(file_name: str) -> str:
        return file_name.split(".")[0].replace("-", "_")

    kernel_function = f"kernel_{normalize_file_name(file_name)}"

    symbols = [
        f"{kernel_function}.constprop.0",
        kernel_function,
    ]

    nm_output = subprocess.run(
        ["nm", executable], stdout=subprocess.PIPE
    ).stdout.decode()
    kernel_function = None
    for symbol in symbols:
        if symbol in nm_output:
            kernel_function = symbol
            break

    gus_path = os.path.join(gus_directory, "gus")

    path_gus_report = os.path.join(output_directory, f"{file_name}.gus_report")
    path_gus_time = os.path.join(output_directory, f"{file_name}.gus_time")
    if use_cache and (os.path.exists(path_gus_report) or os.path.exists(path_gus_time)):
        print(f"[GUS] Skipping {executable} as it already exists")
        return

    with open(path_gus_report, "w") as f:
        time = launch_subprocess_with_timeout(
            [gus_path, "--kernel", kernel_function, executable],
            timeout,
            stdout=f,
            stderr=f,
        )

    if time is None:
        with open(path_gus_time, "w") as f:
            f.write("timeout")
    else:
        with open(path_gus_time, "w") as f:
            f.write(f"{time}")


def run_gem5(
    executable: str,
    gem5scripts_directory: str,
    output_directory: str,
    gem5_directory: str,
    timeout: int,
    use_cache: bool,
):
    print(f"[GEM5] Running {executable}")

    file_name = os.path.basename(executable)
    benchmark_name = file_name.split(".GEM5")[0]
    output_directory = os.path.join(output_directory, benchmark_name)

    path_gem5_report = os.path.join(output_directory, f"{benchmark_name}.gem5_report")
    path_gem5_time = os.path.join(output_directory, f"{benchmark_name}.gem5_time")
    if use_cache and (
        os.path.exists(path_gem5_report) and os.path.exists(path_gem5_time)
    ):
        print(f"[GEM5] Skipping {executable} as it already exists")
        return

    # create output directory if it does not exist
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    with open(path_gem5_report, "w") as f:
        time = launch_subprocess_with_timeout(
            [
                os.path.join(gem5_directory, "build/X86/gem5.fast"),
                "--outdir",
                output_directory,
                os.path.join(gem5scripts_directory, "run.py"),
                "--processor_type",
                "skx",
                "--bench",
                executable,
                "--args",
            ],
            timeout,
            stdout=f,
            stderr=f,
        )

    if time is None:
        with open(path_gem5_time, "w") as f:
            f.write("timeout")
    else:
        with open(path_gem5_time, "w") as f:
            f.write(f"{time}")


def run_binary(
    executable: str, output_directory: str, timeout: int, retries: int, use_cache: bool
):
    print(f"[PAPI] Running {executable}")

    file_name = os.path.basename(executable)
    benchmark_name = file_name.split(".PAPI")[0]
    report_path = os.path.join(output_directory, f"{benchmark_name}.papi_report")
    time_path = os.path.join(output_directory, f"{benchmark_name}.papi_time")

    if use_cache and os.path.exists(report_path):
        print(f"[PAPI] Skipping {executable} as it already exists")
        return

    with open(report_path, "w") as reportf:
        with open(time_path, "w") as timef:
            for _ in range(retries):
                time = launch_subprocess_with_timeout(
                    [executable], timeout, stdout=reportf, stderr=reportf
                )
                assert time is not None
                timef.write(f"{time}\n")


def run_simulator_parallel(files: list[str], threads: int, fn: callable, *args):
    with multiprocessing.Pool(threads) as pool:
        pool.starmap(
            fn,
            [(executable, *args) for executable in files],
        )


def take_random_seed_list(items: list, size: int, seed: int) -> list:
    random.seed(seed)
    random.shuffle(items)
    return items[:size]


def main():
    parser = argparse.ArgumentParser(
        description="Run simulators in parallel to generate reports"
    )

    parser.add_argument("--input_dir", help="Input directory", type=str)
    parser.add_argument("--output_directory", help="Output directory", type=str)
    parser.add_argument("--gus_directory", help="GUS directory", type=str)
    parser.add_argument(
        "--gem5_scripts_directory",
        help="GEM5 scripts directory",
        type=str,
        default="gem5-exps",
    )
    parser.add_argument("--gem5_directory", help="GEM5 directory", type=str)
    parser.add_argument("--threads", help="Number of threads", type=int)
    parser.add_argument(
        "--timeout", help="Timeout for each simulator", type=int, default=7200
    )
    parser.add_argument(
        "--seed", help="Seed for random number generator", type=int, default=0
    )
    parser.add_argument(
        "--sample",
        help="Take a random sample of the input directory",
        type=int,
        default=0,
    )
    parser.add_argument(
        "--retries-per-executable",
        help="Number of retries per executable",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--skip-gus",
        help="Skip GUS simulator",
        action="store_true",
    )
    parser.add_argument(
        "--skip-gem5",
        help="Skip GEM5 simulator",
        action="store_true",
    )
    parser.add_argument(
        "--skip-papi",
        help="Skip PAPI simulator",
        action="store_true",
    )
    parser.add_argument(
        "--use-cache",
        help="Use cached results",
        action="store_true",
    )

    args = parser.parse_args()

    # create output directory if it does not exist
    if not os.path.exists(args.output_directory):
        os.makedirs(args.output_directory)

    # make subdirectories in output directory
    if not os.path.exists(os.path.join(args.output_directory, "gus")):
        os.makedirs(os.path.join(args.output_directory, "gus"))
    if not os.path.exists(os.path.join(args.output_directory, "gem5")):
        os.makedirs(os.path.join(args.output_directory, "gem5"))
    if not os.path.exists(os.path.join(args.output_directory, "papi")):
        os.makedirs(os.path.join(args.output_directory, "papi"))

    gus_output_directory = os.path.join(args.output_directory, "gus")
    gem5_output_directory = os.path.join(args.output_directory, "gem5")
    papi_output_directory = os.path.join(args.output_directory, "papi")

    # run simulators sequentially
    simulators = []

    if not args.skip_gus:
        simulators.append(
            (
                "GUS",
                run_gus,
                gus_output_directory,
                args.gus_directory,
                args.timeout,
                args.use_cache,
            )
        )

    if not args.skip_gem5:
        simulators.append(
            (
                "GEM5",
                run_gem5,
                args.gem5_scripts_directory,
                gem5_output_directory,
                args.gem5_directory,
                args.timeout,
                args.use_cache,
            )
        )

    executables = glob.glob(os.path.join(args.input_dir, "*.PAPI"))
    sorted(executables)
    if args.sample > 0:
        executables = take_random_seed_list(executables, args.sample, args.seed)

    for extension, fn, *fn_args in simulators:
        executables_current = list(
            map(
                lambda executable: executable.replace(".PAPI", f".{extension}"),
                executables,
            )
        )
        run_simulator_parallel(executables_current, args.threads, fn, *fn_args)

    if not args.skip_papi:
        for executable in executables:
            run_binary(
                executable,
                papi_output_directory,
                args.timeout,
                args.retries_per_executable,
                args.use_cache,
            )


if __name__ == "__main__":
    main()
