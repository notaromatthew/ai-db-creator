from __future__ import annotations

import pytest

from analyze_available_records import cohen_d, holm_adjust, welch_test


def test_holm_adjust_is_monotone_in_sorted_p_values():
    raw = [0.04, 0.001, 0.03, 0.50]
    adjusted = holm_adjust(raw)
    assert adjusted == pytest.approx([0.09, 0.004, 0.09, 0.50])


def test_welch_test_detects_separated_groups():
    statistic, degrees_of_freedom, p_value = welch_test(
        [10.0, 11.0, 12.0, 13.0],
        [1.0, 2.0, 3.0, 4.0],
    )
    assert statistic > 9
    assert degrees_of_freedom == pytest.approx(6.0)
    assert p_value < 0.001


def test_cohen_d_preserves_contrast_direction():
    assert cohen_d([4.0, 5.0, 6.0], [1.0, 2.0, 3.0]) == pytest.approx(3.0)
