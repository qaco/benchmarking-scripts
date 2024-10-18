import subprocess
import sys

def print_warning(debug: bool, warning: str):
    if debug:
        print(warning,file=sys.stderr)

def run_command_output_free(
        command: str,
        timeout: int,
):
    subprocess.run(
        command,
        shell=True,
        text=True,
        capture_output=False,
        timeout = timeout
    )

def run_command(
        command: str,
        timeout: int,
) -> (str,str) :
     #   
    output = subprocess.run(
        command,
        shell=True,
        text=True,
        capture_output=True,
        timeout = timeout
    )
    return output.stdout,output.stderr
