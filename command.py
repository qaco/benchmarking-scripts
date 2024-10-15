import subprocess
import sys, os
from typing import Union
import re
from ihm import print_debug


class Result:
    success: bool
    message: str

    def __init__(self, success, message):
        self.success = success
        self.message = message


class Fail(Result):
    def __init__(self, message):
        super().__init__(success=False, message=message)


class Success(Result):
    def __init__(self, message):
        super().__init__(success=True, message=message)


def fail(command_list):
    print("! " + " ".join(command_list) + " fails", file=sys.stderr)
    command = " ".join(command_list)
    return Fail(command)


def remove_color_codes(text):
    ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
    return ansi_escape.sub("", text)


def execute(
    command_list: list[str],
    message_if_success: str = "",
    timeout: int | None = None,
    target_file: str | None = None,
    env_vars: dict[str, str] = {},
    capture_output=True,
    debug: bool = False,
):
    env_str = ""
    for k in env_vars:
        env_str += f"{k}={env_vars[k]} "

    command = env_str + " ".join(command_list)
    print_debug(debug, command)

    try:
        output = subprocess.run(
            command,
            shell=True,
            text=True,
            capture_output=capture_output,
            timeout = timeout
        )
    except subprocess.CalledProcessError as e:
        return fail(command_list)
    except subprocess.TimeoutExpired as e:
        return fail(["Timeout:"] + command_list)
    if capture_output:
        tmp_result = output.stdout + output.stderr
        result = remove_color_codes(tmp_result)
        res = Success(result)
    else:
        res = Success(message_if_success)
    if target_file:
        f = open(target_file, "w")
        f.write(res.message)
        f.close()
    return res
