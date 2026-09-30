from criba.scoring import mutual_information


def test_mutual_information_uses_x_and_y_marginals() -> None:
    """Perfectly correlated fair bits carry exactly one bit of information."""
    joint = [[0.5, 0.0], [0.0, 0.5]]
    marginal_x = [0.5, 0.5]
    marginal_y = [0.5, 0.5]

    assert mutual_information(joint, marginal_x, marginal_y) == 1.0
