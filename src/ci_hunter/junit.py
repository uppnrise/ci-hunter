from __future__ import annotations

from dataclasses import dataclass
import xml.etree.ElementTree as ET
from typing import List


@dataclass(frozen=True)
class TestDuration:
    __test__ = False
    name: str
    duration_seconds: float


def parse_junit_durations(xml_text: str) -> List[TestDuration]:
    root = ET.fromstring(xml_text)
    durations: list[TestDuration] = []
    for testcase in root.iter("testcase"):
        classname = testcase.attrib.get("classname", "").strip()
        name = testcase.attrib.get("name", "").strip()
        time_str = testcase.attrib.get("time", "0").strip()
        try:
            duration = float(time_str)
        except ValueError:
            duration = 0.0

        if classname:
            full_name = f"{classname}::{name}"
        else:
            full_name = name
        durations.append(TestDuration(name=full_name, duration_seconds=duration))
    return durations
