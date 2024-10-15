import argparse
import os
import glob
import subprocess

NUM_RETRIES = 5

def run_papi(executable, output_directory):
    file_name = os.path.basename(executable)
    try:
        before_gus = file_name.split('.PAPI')[0]
        with open(os.path.join(output_directory, before_gus + '.papi_report'), 'w') as f:
            for i in range(NUM_RETRIES):
                command = [executable]
                subprocess.run(command, stdout=f, stderr=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError as e:
        print('Error running gus on {}'.format(executable))
        print('Error: {}'.format(e))
        return 

def run_papi_parallel(input_dir, output_directory):
    executables = glob.glob(os.path.join(input_dir, '*.PAPI'))
    for executable in executables:
        run_papi(executable, output_directory)
    
def main():
    parser = argparse.ArgumentParser(description='Generate GUS reports')
    parser.add_argument('input_dir', help='Input directory')
    parser.add_argument('output_directory', help='Output directory')
    args = parser.parse_args()

    # create output directory if it does not exist
    if not os.path.exists(args.output_directory):
        os.makedirs(args.output_directory)

    run_papi_parallel(args.input_dir, args.output_directory)

if __name__ == '__main__':
    main()