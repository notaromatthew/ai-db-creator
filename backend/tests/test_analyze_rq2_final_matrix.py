from analyze_rq2_final_matrix import exact_permutation_p, hedges_g, holm_adjust


def test_exact_permutation_detects_complete_separation():
    assert exact_permutation_p([1, 1, 1, 1, 1], [0, 0, 0, 0, 0]) == 2 / 252


def test_hedges_g_preserves_full_minus_baseline_direction():
    assert hedges_g([0.8, 0.9, 1.0], [0.2, 0.3, 0.4]) < 0


def test_holm_adjustment_is_monotone_in_ranked_order():
    adjusted = holm_adjust([0.01, 0.04, 0.03])
    assert adjusted == [0.03, 0.06, 0.06]
