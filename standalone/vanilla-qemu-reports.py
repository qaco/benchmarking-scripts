import argparse
import os
import multiprocessing
import glob
import subprocess
import time
def run_gus(executable, output_directory, gus_directory):
    file_name = os.path.basename(executable)
    gus_path = os.path.join(gus_directory, 'qemu-x86_64')
    command = [gus_path, executable]
    try:
        before_gus = file_name.split('.GUS')[0]
        start_time, end_time = 0, 0
        with open(os.path.join(output_directory, before_gus + '.qemu_report'), 'w') as f:
            start_time = time.time()
            subprocess.run(command, stdout=f, stderr=subprocess.PIPE, check=True)
            end_time = time.time()

        with open(os.path.join(output_directory, before_gus + '.qemu_report'), 'a') as f:
            f.write('gus_runtime_seconds {}\n'.format(end_time - start_time))
    except subprocess.CalledProcessError as e:
        print('Error running gus on {}'.format(executable))
        print('Error: {}'.format(e))
        return 

def run_gus_parallel(input_dir, output_directory, gus_directory, threads):
    executables = glob.glob(os.path.join(input_dir, '*.GUS'))
    with multiprocessing.Pool(int(threads)) as pool:
        pool.starmap(run_gus, [(executable, output_directory, gus_directory) for executable in executables])
    
def main():
    parser = argparse.ArgumentParser(description='Generate GUS reports')
    parser.add_argument('input_dir', help='Input directory')
    parser.add_argument('output_directory', help='GUS directory')
    parser.add_argument('gus_directory', help='GUS directory')
    parser.add_argument('threads', help='Number of threads')
    args = parser.parse_args()

    # create output directory if it does not exist
    if not os.path.exists(args.output_directory):
        os.makedirs(args.output_directory)

    run_gus_parallel(args.input_dir, args.output_directory, args.gus_directory, args.threads)

if __name__ == '__main__':
    main()