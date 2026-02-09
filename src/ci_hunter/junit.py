from __future__ import annotations

from dataclasses import dataclass
import xml.etree.ElementTree as ET
from typing import List


@dataclass(frozen=True)
class TestDuration:
    __test__ = False
    name: str
    duration_seconds: float


TEST_OUTCOME_PASSED = "passed"
TEST_OUTCOME_FAILED = "failed"
TEST_OUTCOME_SKIPPED = "skipped"


@dataclass(frozen=True)
class TestOutcome:
    __test__ = False
    name: str
    outcome: str


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


def parse_junit_test_outcomes(xml_text: str) -> List[TestOutcome]:
    root = ET.fromstring(xml_text)
    outcomes: list[TestOutcome] = []
    for testcase in root.iter("testcase"):
        classname = testcase.attrib.get("classname", "").strip()
        name = testcase.attrib.get("name", "").strip()
        if classname:
            full_name = f"{classname}::{name}"
        else:
            full_name = name
        outcome = _resolve_testcase_outcome(testcase)
        outcomes.append(TestOutcome(name=full_name, outcome=outcome))
    return outcomes


def _resolve_testcase_outcome(testcase: ET.Element) -> str:
    if testcase.find("failure") is not None or testcase.find("error") is not None:
        return TEST_OUTCOME_FAILED
    if testcase.find("skipped") is not None:
        return TEST_OUTCOME_SKIPPED
    return TEST_OUTCOME_PASSED
