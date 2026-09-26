from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKOUT_SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"
SETUP_PYTHON_SHA = "5fda3b95a4ea91299a34e894583c3862153e4b97"


def test_first_party_action_pins_match_action_identity() -> None:
    """Prevent valid action SHAs from being accidentally assigned to another action."""
    workflows = ROOT / ".github" / "workflows"
    for path in workflows.glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("- uses: actions/checkout@"):
                assert stripped == f"- uses: actions/checkout@{CHECKOUT_SHA}", path
            if stripped.startswith("- uses: actions/setup-python@"):
                assert stripped == f"- uses: actions/setup-python@{SETUP_PYTHON_SHA}", path
