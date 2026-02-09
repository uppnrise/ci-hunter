from ci_hunter.junit import (
    TEST_OUTCOME_FAILED,
    TEST_OUTCOME_PASSED,
    TEST_OUTCOME_SKIPPED,
    TestDuration,
    TestOutcome,
    parse_junit_durations,
    parse_junit_test_outcomes,
)


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


def test_parse_junit_test_outcomes_from_xml():
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="suite" tests="3" time="3.0">
  <testcase classname="pkg.test_a" name="test_pass" time="1.0" />
  <testcase classname="pkg.test_b" name="test_fail" time="1.0">
    <failure message="boom">trace</failure>
  </testcase>
  <testcase classname="pkg.test_c" name="test_skip" time="1.0">
    <skipped />
  </testcase>
</testsuite>
"""

    outcomes = parse_junit_test_outcomes(xml_text)

    assert outcomes == [
        TestOutcome(name="pkg.test_a::test_pass", outcome=TEST_OUTCOME_PASSED),
        TestOutcome(name="pkg.test_b::test_fail", outcome=TEST_OUTCOME_FAILED),
        TestOutcome(name="pkg.test_c::test_skip", outcome=TEST_OUTCOME_SKIPPED),
    ]
