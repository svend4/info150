import pytest

from triage4.scoring import (
    ConsistencyIssue,
    ConsistencyReport,
    batch_consistency_check,
    check_all_present,
    check_canvas_bounds,
    check_gap_uniformity,
    check_score_threshold,
    check_unique_ids,
    run_consistency_check,
)


def test_consistency_issue_validates_severity():
    with pytest.raises(ValueError):
        ConsistencyIssue(code="X", description="y", severity="bogus")


def test_consistency_issue_rejects_empty_code():
    with pytest.raises(ValueError):
        ConsistencyIssue(code="", description="y")


def test_check_unique_ids_flags_duplicates():
    issues = check_unique_ids([1, 2, 2, 3, 3])
    assert len(issues) == 1
    assert issues[0].code == "DUPLICATE_ID"
    assert issues[0].fragment_ids == [2, 3]


def test_check_unique_ids_no_issue_when_unique():
    assert check_unique_ids([1, 2, 3]) == []


def test_check_all_present_reports_missing_and_extra():
    issues = check_all_present([1, 2, 4], [1, 2, 3])
    codes = {i.code for i in issues}
    assert codes == {"MISSING_FRAGMENT", "EXTRA_FRAGMENT"}


def test_check_canvas_bounds_detects_out_of_bounds():
    issues = check_canvas_bounds(
        positions=[(0, 0), (90, 90)],
        sizes=[(10, 10), (20, 20)],
        canvas_w=100,
        canvas_h=100,
    )
    assert len(issues) == 1
    assert issues[0].code == "OUT_OF_BOUNDS"


def test_check_canvas_bounds_validates_inputs():
    with pytest.raises(ValueError):
        check_canvas_bounds([], [], canvas_w=0, canvas_h=100)
    with pytest.raises(ValueError):
        check_canvas_bounds([(0, 0)], [], canvas_w=100, canvas_h=100)


def test_check_score_threshold_warns_low_pairs():
    issues = check_score_threshold({(0, 1): 0.3, (1, 2): 0.8}, min_score=0.5)
    assert len(issues) == 1
    assert issues[0].code == "LOW_SCORE"


def test_check_score_threshold_validates_min_score():
    with pytest.raises(ValueError):
        check_score_threshold({(0, 1): 0.5}, min_score=-0.1)


def test_check_gap_uniformity_warns_when_variance_high():
    issues = check_gap_uniformity([1.0, 1.0, 20.0, 1.0], max_std=2.0)
    assert len(issues) == 1
    assert issues[0].code == "NONUNIFORM_GAP"


def test_check_gap_uniformity_returns_nothing_for_single_gap():
    assert check_gap_uniformity([3.0]) == []


def test_run_consistency_check_returns_report():
    report = run_consistency_check(
        fragment_ids=[1, 2, 3],
        expected_ids=[1, 2, 3],
        positions=[(0, 0), (10, 0), (20, 0)],
        sizes=[(10, 10), (10, 10), (10, 10)],
        canvas_w=100,
        canvas_h=100,
        pair_scores={(0, 1): 0.8, (1, 2): 0.9},
        min_score=0.5,
    )
    assert isinstance(report, ConsistencyReport)
    assert report.is_consistent is True
    assert report.checked_pairs == 2


def test_batch_consistency_check_returns_list():
    assemblies = [
        dict(
            fragment_ids=[1, 2],
            expected_ids=[1, 2],
            positions=[(0, 0), (10, 0)],
            sizes=[(10, 10), (10, 10)],
            canvas_w=100,
            canvas_h=100,
        ),
    ]
    reports = batch_consistency_check(assemblies)
    assert len(reports) == 1
    assert reports[0].is_consistent is True
