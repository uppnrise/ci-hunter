from ci_hunter.junit import TestDuration, parse_junit_durations


def test_parse_junit_durations_from_xml():
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="suite" tests="2" time="3.0">
  <testcase classname="pkg.test_a" name="test_one" time="1.5" />
  <testcase classname="pkg.test_b" name="test_two" time="0.5" />
</testsuite>
"""

    durations = parse_junit_durations(xml_text)

    assert durations == [
        TestDuration(name="pkg.test_a::test_one", duration_seconds=1.5),
        TestDuration(name="pkg.test_b::test_two", duration_seconds=0.5),
    ]
