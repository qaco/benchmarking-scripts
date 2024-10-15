import re
from typing import Union
import sys
from dataclasses import dataclass


class Report:

    def __init__(
        self,
        success: bool,
        desc: str,
        benchmark: str,
        bottlenecks: list[str] | None = None,
        metrics: dict[str, int | None] | None = None,
        report: str | None = None,
    ):
        self.success = success
        self.desc = desc
        self.benchmark = benchmark
        self.bottlenecks = bottlenecks
        self.metrics = metrics
        self.report = report

    def print(self, flag):
        if flag and self.success:
            print(f"> {self.desc} ({self.benchmark})")
            print(f"  Bottlenecks: {self.bottlenecks}")
            print(f"  Metrics: {self.metrics}")

    def __str__(self):
        if not self.success:
            return ""
        s = ""
        for name, value in self.metrics.items():
            s += f"{name}: {value}"
            s += "\n"
        s += f"bottlenecks: {self.bottlenecks}"
        return s


def parse_float(regexp, text):
    match = re.search(regexp, text)
    if match == None:
        return None
    else:
        return float(match.group(1).replace(",", "."))


def parse_int(regexp, text):
    text = text.replace('.','')
    match = re.search(regexp, text)
    if match == None or match.group(1) == None:
        return None
    myint = re.sub("[^0-9]", "", match.group(1))
    if myint.isdigit():
        return int(myint)
    else:
        return None
