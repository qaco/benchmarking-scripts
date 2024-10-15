import argparse
import os
import multiprocessing
import glob
import subprocess
from timeit import default_timer as timer

def run_gus(executable, gem5scripts_directory, output_directory, gus_directory):
    file_name = os.path.basename(executable)
    gus_path = os.path.join(gus_directory, 'gem5.fast')
    gem5_executable = os.path.join(gus_directory, 'gem5.fast')
    script = os.path.join(gem5scripts_directory, 'run.py')
    output_directory = os.path.join(output_directory, file_name.split('.GEM5')[0])
    start_time, end_time = 0, 0
    command = [gem5_executable, '--outdir', output_directory, script, '--processor_type', 'skx', '--bench', executable, '--args']
    try:
        start_time = timer()
        subprocess.run(command, check=True)
        end_time = timer()

        with open(os.path.join(output_directory, 'time'), 'w') as f:
            f.write('gus_runtime_seconds {}\n'.format(end_time - start_time))
    except subprocess.CalledProcessError as e:
        print('Error running gus on {}'.format(executable))
        print('Error: {}'.format(e))
        return 

def run_gem5_parallel(input_dir, gem5scripts_directory, output_directory, gem5_directory, threads):
    executables = glob.glob(os.path.join(input_dir, '*.GEM5'))
    with multiprocessing.Pool(int(threads)) as pool:
        pool.starmap(run_gus, [(executable, gem5scripts_directory, output_directory, gem5_directory) for executable in executables])
    
def main():
    parser = argparse.ArgumentParser(description='Generate GUS reports')
    parser.add_argument('input_dir', help='Input directory')
    parser.add_argument('gem5_scripts_directory', help='GUS directory')
    parser.add_argument('output_directory', help='GUS directory')
    parser.add_argument('gem5_directory', help='GEM5 directory')
    parser.add_argument('threads', help='Number of threads')
    args = parser.parse_args()

    # create output directory if it does not exist
    if not os.path.exists(args.output_directory):
        os.makedirs(args.output_directory)

    run_gem5_parallel(args.input_dir, args.output_directory, args.gem5_directory, args.threads)

if __name__ == '__main__':
    main()