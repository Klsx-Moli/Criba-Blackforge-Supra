"""ASTRA-007/010/029: conservative mechanism comparison and abstention."""

from criba.diversity_selector import compare_mechanisms


def test_astra_010_low_lexical_overlap_abstains_instead_of_distinct():
    assert (
        compare_mechanisms(
            "rotate ephemeral credentials after each authorized operation",
            "aggregate local temperature measurements before transmission",
        )
        == "UNKNOWN"
    )


def test_astra_010_quantity_change_is_preserved_when_context_matches():
    assert (
        compare_mechanisms(
            "the gateway permits 1 request per credential every minute",
            "the gateway permits 10 requests per credential every minute",
        )
        == "DISTINCT"
    )


def test_astra_010_scoped_negation_is_distinct_but_unrelated_negation_abstains():
    assert (
        compare_mechanisms(
            "the gateway permits remote execution for approved agents",
            "the gateway does not permit remote execution for approved agents",
        )
        == "DISTINCT"
    )
    assert (
        compare_mechanisms(
            "the gateway does not permit remote execution for approved agents",
            "local sensors aggregate thermal readings before transmission",
        )
        == "UNKNOWN"
    )


def test_astra_007_verbosity_does_not_create_scientific_distinction():
    base = "rotate credentials after each authorized operation"
    verbose = "for improved security and robust operation, rotate credentials after each authorized operation"
    assert compare_mechanisms(base, verbose) != "DISTINCT"
